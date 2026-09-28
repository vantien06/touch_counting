import argparse
import csv
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import yaml
import portalocker
from ultralytics import YOLO


WAITING = "WAITING"
COUNTING = "COUNTING"
CAMERA_WIDTH = 3840
CAMERA_HEIGHT = 2160
CSV_FIELDS = [
    "camera",
    "camera_resolution",
    "recorded_at_utc",
    "person_id",
    "zone",
    "entry_frame",
    "exit_frame",
    "entry_time_seconds",
    "exit_time_seconds",
    "time_in_zone_seconds",
]


class EventLogger:
    def __init__(self, path, camera, resolution):
        self.path = Path(path)
        self.camera = camera
        self.resolution = resolution

    def writerow(self, event):
        row = {
            "camera": self.camera,
            "camera_resolution": self.resolution,
            **event,
        }
        with portalocker.Lock(str(self.path), mode="a+", timeout=30, newline="", encoding="utf-8") as csv_file:
            csv_file.seek(0, 2)
            writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
            if csv_file.tell() == 0:
                writer.writeheader()
            writer.writerow(row)
            csv_file.flush()


def parse_video_source(source):
    source = str(source)
    if source.isdigit():
        return int(source)
    return source


def list_cameras(max_index=10):
    cameras = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if capture.isOpened():
                ok, frame = capture.read()
                if ok and frame is not None:
                    cameras.append((index, frame.shape[1], frame.shape[0]))
        finally:
            capture.release()
    return cameras


@dataclass
class VisitState:
    region: str
    track_id: int
    first_seen_frame: int
    first_seen_seconds: float
    last_seen_frame: int
    last_seen_seconds: float
    last_center: tuple
    status: str = WAITING
    entry_frame: int | None = None
    entry_seconds: float | None = None


@dataclass
class Detection:
    track_id: int | None
    confidence: float
    center: tuple
    box: tuple


def read_config(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream) or {}
    if not config.get("regions"):
        raise ValueError("config.yaml must contain at least one region")
    return config


def resolve_imgsz(value, width, height):
    if isinstance(value, str) and value.lower() in {"native", "max", "maximum"}:
        return max(width, height)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid imgsz: {value}") from exc


def point_in_region(center, points):
    polygon = np.asarray(points, dtype=np.float32)
    return cv2.pointPolygonTest(polygon, (float(center[0]), float(center[1])), False) >= 0


def parse_regions(config):
    regions = []
    for item in config["regions"]:
        points = item.get("points", [])
        if len(points) < 3:
            raise ValueError(f"Region {item.get('name')} needs at least 3 points")
        regions.append((str(item["name"]), points))
    return regions


def close_visit(state, exit_frame, exit_seconds, writer):
    if state.status != COUNTING:
        return
    duration = max(0.0, exit_seconds - float(state.first_seen_seconds))
    writer.writerow({
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "person_id": state.track_id,
        "zone": state.region.replace("_", " ").title(),
        "entry_frame": state.first_seen_frame,
        "exit_frame": exit_frame,
        "entry_time_seconds": f"{state.first_seen_seconds:.3f}",
        "exit_time_seconds": f"{exit_seconds:.3f}",
        "time_in_zone_seconds": f"{duration:.3f}",
    })


def get_detections(result):
    boxes = result.boxes
    detections = []
    if boxes is None:
        return detections
    xyxy = boxes.xyxy.cpu().numpy()
    confidence = boxes.conf.cpu().numpy()
    classes = boxes.cls.cpu().numpy().astype(int)
    ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(xyxy)
    for box, score, cls, track_id in zip(xyxy, confidence, classes, ids):
        if cls != 0:
            continue
        x1, y1, x2, y2 = [int(value) for value in box]
        center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
        detections.append(Detection(None if track_id is None else int(track_id), float(score), center, (x1, y1, x2, y2)))
    return detections


def update_states(states, detections, regions, frame_index, seconds, dwell, grace, handoff_distance, writer, touch_counts):
    matched = set()
    assignments = {}
    by_id = {d.track_id: d for d in detections if d.track_id is not None}

    for region_name, _points in regions:
        region_states = states.setdefault(region_name, [])
        for state in region_states:
            detection = by_id.get(state.track_id)
            if detection is not None:
                assignments[id(state)] = detection
                matched.add(id(detection))

        # Keep a pending/active visit alive across a short ID switch.
        for state in region_states:
            if id(state) in assignments:
                continue
            candidates = [
                detection for detection in detections
                if detection.track_id is not None
                and id(detection) not in matched
                and math.dist(state.last_center, detection.center) <= handoff_distance
                and seconds - state.last_seen_seconds <= grace
            ]
            if candidates:
                detection = min(candidates, key=lambda item: math.dist(state.last_center, item.center))
                state.track_id = detection.track_id
                assignments[id(state)] = detection
                matched.add(id(detection))

        region_states[:] = [state for state in region_states if state.status == COUNTING or seconds - state.last_seen_seconds <= grace]
        for state in list(region_states):
            detection = assignments.get(id(state))
            if detection is None:
                if state.status == COUNTING and seconds - state.last_seen_seconds > grace:
                    close_visit(state, state.last_seen_frame, state.last_seen_seconds, writer)
                    region_states.remove(state)
                continue
            state.last_seen_frame = frame_index
            state.last_seen_seconds = seconds
            state.last_center = detection.center
            if state.status == WAITING and seconds - state.first_seen_seconds >= dwell:
                state.status = COUNTING
                state.entry_frame = frame_index
                state.entry_seconds = seconds
                touch_counts[region_name] = touch_counts.get(region_name, 0) + 1

        for detection in detections:
            if detection.track_id is None or id(detection) in matched:
                continue
            if point_in_region(detection.center, dict(regions)[region_name]):
                region_states.append(VisitState(region_name, detection.track_id, frame_index, seconds, frame_index, seconds, detection.center))
                matched.add(id(detection))

        # A tracked person whose center left the zone closes that visit immediately.
        for state in list(region_states):
            detection = assignments.get(id(state))
            if detection is not None and not point_in_region(detection.center, dict(regions)[region_name]):
                close_visit(state, frame_index, seconds, writer)
                region_states.remove(state)


def draw_frame(frame, detections, regions, states, touch_counts):
    zone_colors = {}
    for name, points in regions:
        region_states = states.get(name, [])
        if any(state.status == COUNTING for state in region_states):
            zone_colors[name] = (0, 0, 255)
        elif any(state.status == WAITING for state in region_states):
            zone_colors[name] = (0, 215, 255)
        else:
            zone_colors[name] = (0, 180, 0)
        polygon = np.asarray(points, dtype=np.int32)
        cv2.polylines(frame, [polygon], True, zone_colors[name], 2)
        x, y = polygon[0]
        label_y = max(20, int(y) - 8)
        region_label = name.replace("_", " ").title()
        cv2.putText(frame, region_label, (int(x), label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, zone_colors[name], 2)
        cv2.putText(frame, f"Count: {touch_counts.get(name, 0)}", (int(x), label_y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, zone_colors[name], 2)

    for detection in detections:
        x1, y1, x2, y2 = detection.box
        color = (0, 165, 255) if detection.track_id is not None else (0, 0, 255)
        label = f"Person {detection.confidence:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, detection.center, 8, (255, 0, 180), -1)
        cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def main():
    parser = argparse.ArgumentParser(description="Track people and log zone dwell visits")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--video", help="Video path or RTSP/HTTP camera URL")
    source_group.add_argument("--camera", type=int, help="Camera index; use --list-cameras to see available cameras")
    source_group.add_argument("--list-cameras", action="store_true", help="List connected cameras and exit")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", default="events.csv")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--save-video")
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()
    if args.list_cameras:
        cameras = list_cameras()
        if cameras:
            for index, width, height in cameras:
                print(f"Camera {index}: {width}x{height}")
        else:
            print("No camera found")
        return
    if args.video is None and args.camera is None:
        parser.error("one of --video or --camera is required (or use --list-cameras)")
    config = read_config(args.config)

    source = args.camera if args.camera is not None else parse_video_source(args.video)
    if isinstance(source, int):
        capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    else:
        capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise SystemExit(f"Cannot open video/camera: {source}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not math.isfinite(fps) or fps <= 0:
        fps = 30.0
    if width <= 0 or height <= 0:
        capture.release()
        raise SystemExit("Invalid video dimensions")
    ok, first_frame = capture.read()
    if not ok or first_frame is None:
        capture.release()
        raise SystemExit("Video opened but the first frame could not be read")
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    if args.preview:
        loading_frame = first_frame.copy()
        cv2.namedWindow("Touch counting", cv2.WINDOW_NORMAL)
        cv2.putText(loading_frame, "Loading model...", (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 215, 255), 2)
        cv2.imshow("Touch counting", loading_frame)
        cv2.waitKey(1)

    print(f"Input: {width}x{height} at {fps:.2f} FPS; imgsz={resolve_imgsz(config.get('imgsz', 'native'), width, height)}; preview={args.preview}")
    target_frames = total_frames
    if args.max_frames > 0:
        target_frames = min(args.max_frames, total_frames) if total_frames > 0 else args.max_frames
    print(f"Processing {target_frames or 'unknown number of'} frame(s)...", flush=True)

    regions = parse_regions(config)
    model = YOLO(config.get("model", "yolo26s.pt"))
    imgsz = resolve_imgsz(config.get("imgsz", "native"), width, height)
    dwell = float(config.get("dwell_seconds", 5.0))
    grace = float(config.get("id_switch_grace_seconds", 1.0))
    handoff_distance = float(config.get("id_switch_distance_pixels", 120.0))
    confidence = float(config.get("confidence", 0.25))
    tracker = config.get("tracker", "bytetrack.yaml")
    writer = None
    camera_name = f"Camera {args.camera}" if args.camera is not None else str(args.video)
    resolution = f"{width}x{height}"
    writer = EventLogger(args.output, camera_name, resolution)
    try:
        video_writer = None
        states = {}
        touch_counts = {name: 0 for name, _points in regions}
        frame_index = -1
        processing_started = time.perf_counter()
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            frame_index += 1
            if args.max_frames and frame_index >= args.max_frames:
                break
            seconds = time.perf_counter() - processing_started
            result = model.track(frame, persist=True, classes=[0], conf=confidence, imgsz=imgsz, tracker=tracker, verbose=False)[0]
            detections = get_detections(result)
            update_states(states, detections, regions, frame_index, seconds, dwell, grace, handoff_distance, writer, touch_counts)
            draw_frame(frame, detections, regions, states, touch_counts)
            if args.save_video and video_writer is None:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                video_writer = cv2.VideoWriter(args.save_video, fourcc, fps, (width, height))
                if not video_writer.isOpened():
                    raise SystemExit(f"Cannot open output video: {args.save_video}")
            if video_writer is not None:
                video_writer.write(frame)
            processed_frames = frame_index + 1
            if processed_frames == 1 or processed_frames % 10 == 0 or (target_frames and processed_frames == target_frames):
                elapsed = time.perf_counter() - processing_started
                speed = processed_frames / elapsed if elapsed > 0 else 0.0
                remaining = (target_frames - processed_frames) / speed if target_frames and speed > 0 else None
                eta = f", ETA {remaining:.1f}s" if remaining is not None else ""
                print(f"Processed {processed_frames}/{target_frames or '?'} frames ({speed:.2f} FPS{eta})", flush=True)
            if args.preview:
                cv2.imshow("Touch counting", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
        final_frame = max(frame_index, 0)
        final_seconds = time.perf_counter() - processing_started
        for region_states in states.values():
            for state in region_states:
                if state.status == COUNTING:
                    close_visit(state, final_frame, final_seconds, writer)
        if video_writer is not None:
            video_writer.release()
    finally:
        capture.release()
        if args.preview:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
