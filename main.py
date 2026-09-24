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
from ultralytics import YOLO


EMPTY = "EMPTY"
WAITING = "WAITING"
COUNTING = "COUNTING"


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
    duration = max(0.0, exit_seconds - float(state.entry_seconds))
    writer.writerow({
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        "track_id": state.track_id,
        "region": state.region,
        "entry_frame": state.entry_frame,
        "exit_frame": exit_frame,
        "entry_seconds": f"{state.entry_seconds:.3f}",
        "exit_seconds": f"{exit_seconds:.3f}",
        "duration_seconds": f"{duration:.3f}",
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


def update_states(states, detections, regions, frame_index, seconds, dwell, grace, handoff_distance, writer):
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


def draw_frame(frame, detections, regions, states):
    zone_colors = {}
    for name, points in regions:
        region_states = states.get(name, [])
        if any(state.status == COUNTING for state in region_states):
            zone_colors[name] = ((0, 180, 0), COUNTING)
        elif any(state.status == WAITING for state in region_states):
            zone_colors[name] = ((0, 215, 255), WAITING)
        else:
            zone_colors[name] = ((80, 0, 140), EMPTY)
        polygon = np.asarray(points, dtype=np.int32)
        cv2.polylines(frame, [polygon], True, zone_colors[name][0], 2)
        x, y = polygon[0]
        cv2.putText(frame, f"{name}: {zone_colors[name][1]}", (int(x), max(20, int(y) - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, zone_colors[name][0], 2)

    for detection in detections:
        x1, y1, x2, y2 = detection.box
        color = (0, 165, 255) if detection.track_id is not None else (0, 0, 255)
        label = f"ID {detection.track_id} {detection.confidence:.2f}" if detection.track_id is not None else f"no-id {detection.confidence:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, detection.center, 5, (255, 0, 180), -1)
        cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def main():
    parser = argparse.ArgumentParser(description="Track people and log zone dwell visits")
    parser.add_argument("--video", required=True, help="Video path or RTSP/HTTP camera URL")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", default="events.csv")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--save-video")
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()
    config = read_config(args.config)

    capture = cv2.VideoCapture(args.video)
    if not capture.isOpened():
        raise SystemExit(f"Cannot open video/camera: {args.video}")
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
    csv_file = None
    fieldnames = ["logged_at_utc", "track_id", "region", "entry_frame", "exit_frame", "entry_seconds", "exit_seconds", "duration_seconds"]
    try:
        csv_file = Path(args.output).open("w", newline="", encoding="utf-8")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        video_writer = None
        states = {}
        frame_index = -1
        last_frame = None
        processing_started = time.perf_counter()
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            frame_index += 1
            if args.max_frames and frame_index >= args.max_frames:
                break
            seconds = frame_index / fps
            result = model.track(frame, persist=True, classes=[0], conf=confidence, imgsz=imgsz, tracker=tracker, verbose=False)[0]
            detections = get_detections(result)
            update_states(states, detections, regions, frame_index, seconds, dwell, grace, handoff_distance, writer)
            draw_frame(frame, detections, regions, states)
            if args.save_video and video_writer is None:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                video_writer = cv2.VideoWriter(args.save_video, fourcc, fps, (width, height))
                if not video_writer.isOpened():
                    raise SystemExit(f"Cannot open output video: {args.save_video}")
            if video_writer is not None:
                video_writer.write(frame)
            last_frame = frame
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
        final_seconds = final_frame / fps
        for region_states in states.values():
            for state in region_states:
                if state.status == COUNTING:
                    close_visit(state, final_frame, final_seconds, writer)
        if video_writer is not None:
            video_writer.release()
    finally:
        capture.release()
        if csv_file is not None:
            csv_file.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
