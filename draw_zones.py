import argparse
from pathlib import Path

import cv2
import yaml


WINDOW = "Draw zones - drag, s=save, u=undo, q=quit"


def load_config(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as stream:
            return yaml.safe_load(stream) or {}
    return {}


def main():
    parser = argparse.ArgumentParser(description="Draw rectangular monitoring zones")
    parser.add_argument("--video", required=True, help="Video path or camera URL")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    capture = cv2.VideoCapture(args.video)
    if not capture.isOpened():
        raise SystemExit(f"Cannot open video/camera: {args.video}")
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        raise SystemExit("Cannot read the first frame")

    config_path = Path(args.config)
    config = load_config(config_path)
    zones = []
    drawing = False
    start = None
    current = None

    def mouse(event, x, y, _flags, _param):
        nonlocal drawing, start, current
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start = (x, y)
            current = None
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            current = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and drawing:
            drawing = False
            current = (x, y)
            x1, y1 = start
            x2, y2 = current
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            if right - left >= 2 and bottom - top >= 2:
                index = len(zones) + 1
                zones.append({
                    "name": f"region_{chr(64 + index) if index <= 26 else index}",
                    "points": [[left, top], [right, top], [right, bottom], [left, bottom]],
                })
            start = None
            current = None

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, mouse)
    while True:
        display = frame.copy()
        for zone in zones:
            points = zone["points"]
            polygon = [(int(point[0]), int(point[1])) for point in points]
            cv2.polylines(display, [__import__("numpy").array(polygon, dtype="int32")], True, (0, 215, 255), 2)
            cv2.putText(display, zone["name"], polygon[0], cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 215, 255), 2)
        if drawing and start and current:
            cv2.rectangle(display, start, current, (0, 215, 255), 2)
        cv2.imshow(WINDOW, display)
        key = cv2.waitKey(20) & 0xFF
        if key == ord("u") and zones:
            zones.pop()
        elif key == ord("s"):
            config["regions"] = zones
            with config_path.open("w", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            print(f"Saved {len(zones)} zones to {config_path}")
            break
        elif key == ord("q") or key == 27:
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
