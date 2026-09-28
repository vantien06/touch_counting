import subprocess
import sys
import hashlib
from io import BytesIO
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
import yaml
from cv2_enumerate_cameras import enumerate_cameras
from PIL import Image, ImageTk


PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIR / "config.yaml"
CAMERA_CONFIG_DIR = PROJECT_DIR / "camera_configs"
LOGO_PATH = PROJECT_DIR / "logo" / "logo.svg"
MODEL_FILES = {"Nano": "yolo26n.pt", "Small": "yolo26s.pt", "Medium": "yolo26m.pt"}
MODEL_NAMES = {value: key for key, value in MODEL_FILES.items()}
CAMERA_WIDTH = 3840
CAMERA_HEIGHT = 2160


def find_cameras(max_index=10):
    cameras = []
    try:
        devices = enumerate_cameras(cv2.CAP_DSHOW)
    except (OSError, RuntimeError):
        devices = []
    if not devices:
        devices = [type("CameraDevice", (), {"index": index, "name": f"Camera {index}", "path": f"index:{index}", "vid": 0, "pid": 0}) for index in range(max_index)]
    for device in devices:
        index = device.index
        if index >= max_index:
            continue
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if capture.isOpened():
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                ok, frame = capture.read()
                if ok and frame is not None:
                    identity = getattr(device, "path", None) or f"{device.name}:{device.vid}:{device.pid}"
                    camera_id = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12]
                    cameras.append({
                        "index": index,
                        "name": device.name.strip() or f"Camera {index}",
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                        "id": camera_id,
                    })
        finally:
            capture.release()
    return cameras


class TouchCountingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Touch Counting")
        self.logo_image = None
        self.header_logo_image = None
        if LOGO_PATH.exists():
            try:
                import cairosvg
                png_data = cairosvg.svg2png(url=str(LOGO_PATH), output_width=64, output_height=64)
                logo = Image.open(BytesIO(png_data)).convert("RGBA")
                self.logo_image = ImageTk.PhotoImage(logo)
                self.root.iconphoto(True, self.logo_image)
                header_png = cairosvg.svg2png(url=str(LOGO_PATH), output_width=52, output_height=52)
                header_logo = Image.open(BytesIO(header_png)).convert("RGBA")
                self.header_logo_image = ImageTk.PhotoImage(header_logo)
            except (ImportError, OSError, ValueError):
                self.logo_image = None
        self.root.geometry("900x700")
        self.root.minsize(620, 560)
        self.root.resizable(True, True)
        self.cameras = []
        self.processes = []
        self.preview_capture = None
        self.preview_after_id = None
        self.load_settings()

        main = ttk.Frame(root, padding=18)
        main.pack(fill="both", expand=True)
        title_row = ttk.Frame(main)
        title_row.pack(anchor="w")
        if self.header_logo_image is not None:
            ttk.Label(title_row, image=self.header_logo_image).pack(side="left", padx=(0, 10))
        ttk.Label(title_row, text="Touch Counting", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(main, text="Select a camera and configure tracking").pack(anchor="w", pady=(2, 14))

        camera_section = ttk.Frame(main)
        camera_section.pack(fill="x", pady=5)
        camera_controls = ttk.Frame(camera_section)
        camera_controls.pack(side="left", fill="x", expand=True)
        camera_row = ttk.Frame(camera_controls)
        camera_row.pack(fill="x")
        ttk.Label(camera_row, text="Camera", width=16).pack(side="left")
        self.camera_var = tk.StringVar()
        self.camera_box = ttk.Combobox(camera_row, textvariable=self.camera_var, state="readonly", width=38)
        self.camera_box.pack(side="left", fill="x", expand=True)
        ttk.Button(camera_row, text="Refresh", command=self.refresh_cameras).pack(side="left", padx=(8, 0))
        self.camera_box.bind("<<ComboboxSelected>>", self.update_camera_preview)

        name_row = ttk.Frame(camera_controls)
        name_row.pack(fill="x", pady=(6, 0))
        ttk.Label(name_row, text="Camera name", width=16).pack(side="left")
        self.camera_name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.camera_name_var).pack(side="left", fill="x", expand=True)
        ttk.Button(name_row, text="Save name", command=self.save_camera_name).pack(side="left", padx=(8, 0))

        preview_frame = ttk.LabelFrame(camera_section, text="Camera preview", padding=4, width=172, height=110)
        preview_frame.pack(side="left", padx=(12, 0))
        preview_frame.pack_propagate(False)
        self.preview_label = ttk.Label(preview_frame, text="Select a camera", anchor="center")
        self.preview_label.pack()

        settings = ttk.LabelFrame(main, text="Tracking settings", padding=10)
        settings.pack(fill="x", pady=(10, 5))
        settings.columnconfigure(1, weight=1)
        self.add_setting_row(settings, 0, "Model", self.model_var, tuple(MODEL_FILES), "Nano is fastest, Small is balanced, and Medium is more accurate but slower.")
        self.add_setting_row(settings, 1, "Confidence", self.confidence_var, help_text="Minimum confidence for detecting a person. Lower values detect more people but may add false detections.")
        self.add_setting_row(settings, 2, "Resolution", self.imgsz_var, ("native", "1920", "1280", "640"), "Image size sent to the AI model. Lower values are faster; higher values can detect smaller people.")
        self.add_setting_row(settings, 3, "Zone time (sec)", self.dwell_var, help_text="How long a person must remain in a zone before one visit is counted.")
        self.add_setting_row(settings, 4, "Lost ID grace (sec)", self.grace_var, help_text="How long to keep a visit when the camera temporarily loses the person.")
        self.add_setting_row(settings, 5, "ID recovery (px)", self.handoff_var, help_text="Maximum distance for matching a newly detected person to the previous position after an ID change.")

        output_row = ttk.Frame(main)
        output_row.pack(fill="x", pady=(8, 5))
        ttk.Label(output_row, text="Output CSV", width=16).pack(side="left")
        self.output_var = tk.StringVar(value=str(PROJECT_DIR / "events.csv"))
        ttk.Entry(output_row, textvariable=self.output_var).pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="Browse", command=self.choose_output).pack(side="left", padx=(8, 0))

        self.preview_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Open preview window", variable=self.preview_var).pack(anchor="w", pady=(10, 4))

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(12, 0))
        self.start_button = ttk.Button(buttons, text="Start tracking", command=self.start_tracking)
        self.start_button.pack(side="left")
        self.start_all_button = ttk.Button(buttons, text="Start all cameras", command=self.start_all_tracking)
        self.start_all_button.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Draw / edit zones", command=self.draw_zones).pack(side="left", padx=8)
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop_tracking, state="disabled")
        self.stop_button.pack(side="left")

        self.status_var = tk.StringVar(value="Searching for cameras...")
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(18, 0))
        self.refresh_cameras()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(0, self.root.state, "zoomed")

    def refresh_cameras(self):
        self.stop_camera_preview()
        self.status_var.set("Searching for cameras...")
        self.root.update_idletasks()
        self.cameras = find_cameras()
        for camera in self.cameras:
            self.ensure_camera_config(camera)
        for camera in self.cameras:
            camera["custom_name"] = self.read_camera_name(camera)
        labels = [f"{camera['custom_name']} - {camera['width']}x{camera['height']} (index {camera['index']})" for camera in self.cameras]
        self.camera_box["values"] = labels
        if labels:
            self.camera_box.current(0)
            self.load_camera_settings(self.cameras[0])
            self.update_camera_preview()
            self.status_var.set(f"Found {len(labels)} camera(s)")
        else:
            self.camera_var.set("")
            self.preview_label.configure(text="No preview available", image="")
            self.status_var.set("No camera found")

    def update_camera_preview(self, _event=None):
        self.stop_camera_preview()
        selection = self.camera_box.current()
        if selection < 0 or selection >= len(self.cameras):
            self.preview_label.configure(text="Select a camera", image="")
            return
        camera = self.cameras[selection]
        camera_index = camera["index"]
        self.load_camera_settings(camera)
        self.preview_capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.preview_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.preview_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.preview_capture.isOpened():
            self.stop_camera_preview()
            self.preview_label.configure(text="Preview unavailable", image="")
            return
        self.refresh_preview_frame()

    def refresh_preview_frame(self):
        if self.preview_capture is None:
            return
        ok, frame = self.preview_capture.read()
        if ok and frame is not None:
            frame = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
            ok, encoded = cv2.imencode(".png", frame)
            if ok:
                self.preview_image = tk.PhotoImage(data=encoded.tobytes(), format="png")
                self.preview_label.configure(image=self.preview_image, text="")
        self.preview_after_id = self.root.after(100, self.refresh_preview_frame)

    def stop_camera_preview(self):
        if self.preview_after_id is not None:
            self.root.after_cancel(self.preview_after_id)
            self.preview_after_id = None
        if self.preview_capture is not None:
            self.preview_capture.release()
            self.preview_capture = None

    def load_settings(self):
        config = {}
        if CONFIG_PATH.exists():
            try:
                with CONFIG_PATH.open("r", encoding="utf-8") as stream:
                    config = yaml.safe_load(stream) or {}
            except (OSError, yaml.YAMLError):
                config = {}
        model = str(config.get("model", "yolo26n.pt"))
        self.model_var = tk.StringVar(value=MODEL_NAMES.get(model, model))
        self.confidence_var = tk.StringVar(value=str(config.get("confidence", 0.25)))
        self.imgsz_var = tk.StringVar(value=str(config.get("imgsz", "native")))
        self.dwell_var = tk.StringVar(value=str(config.get("dwell_seconds", 5.0)))
        self.grace_var = tk.StringVar(value=str(config.get("id_switch_grace_seconds", 1.0)))
        self.handoff_var = tk.StringVar(value=str(config.get("id_switch_distance_pixels", 120.0)))

    def camera_config_path(self, camera):
        return CAMERA_CONFIG_DIR / f"camera_{camera['id']}.yaml"

    def load_camera_settings(self, camera):
        config_path = self.camera_config_path(camera)
        legacy_path = CAMERA_CONFIG_DIR / f"camera_{camera['index']}.yaml"
        if not config_path.exists() and legacy_path.exists():
            config_path = legacy_path
        if not config_path.exists():
            return
        try:
            with config_path.open("r", encoding="utf-8") as stream:
                config = yaml.safe_load(stream) or {}
            camera["custom_name"] = str(config.get("camera_name", camera["name"]))
            self.camera_name_var.set(camera["custom_name"])
            model = str(config.get("model", MODEL_FILES.get(self.model_var.get(), "yolo26n.pt")))
            self.model_var.set(MODEL_NAMES.get(model, model))
            self.confidence_var.set(str(config.get("confidence", self.confidence_var.get())))
            self.imgsz_var.set(str(config.get("imgsz", self.imgsz_var.get())))
            self.dwell_var.set(str(config.get("dwell_seconds", self.dwell_var.get())))
            self.grace_var.set(str(config.get("id_switch_grace_seconds", self.grace_var.get())))
            self.handoff_var.set(str(config.get("id_switch_distance_pixels", self.handoff_var.get())))
        except (OSError, yaml.YAMLError):
            return

    def read_camera_name(self, camera):
        config_path = self.camera_config_path(camera)
        try:
            with config_path.open("r", encoding="utf-8") as stream:
                config = yaml.safe_load(stream) or {}
            return str(config.get("camera_name", camera["name"]))
        except (OSError, yaml.YAMLError):
            return camera["name"]

    def ensure_camera_config(self, camera):
        CAMERA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_path = self.camera_config_path(camera)
        if config_path.exists():
            return config_path
        legacy_path = CAMERA_CONFIG_DIR / f"camera_{camera['index']}.yaml"
        source_path = legacy_path if legacy_path.exists() else CONFIG_PATH
        with source_path.open("r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
        if not legacy_path.exists() and camera["index"] != 0:
            config["regions"] = []
        with config_path.open("w", encoding="utf-8") as stream:
            yaml.safe_dump(config, stream, sort_keys=False)
        return config_path

    def save_camera_name(self):
        camera = self.selected_camera_info()
        if camera is None:
            return
        camera_name = self.camera_name_var.get().strip()
        if not camera_name:
            messagebox.showwarning("Invalid camera name", "Please enter a camera name.")
            return
        try:
            config_path = self.ensure_camera_config(camera)
            with config_path.open("r", encoding="utf-8") as stream:
                config = yaml.safe_load(stream) or {}
            config["camera_name"] = camera_name
            with config_path.open("w", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            camera["custom_name"] = camera_name
            selection = self.camera_box.current()
            labels = [f"{item.get('custom_name', item['name'])} - {item['width']}x{item['height']} (index {item['index']})" for item in self.cameras]
            self.camera_box["values"] = labels
            self.camera_box.current(selection)
            self.status_var.set(f"Camera renamed to {camera_name}")
        except (OSError, yaml.YAMLError):
            messagebox.showerror("Could not save camera name", "The camera name could not be saved.")

    def add_setting_row(self, parent, row, label, variable, values=None, help_text=""):
        ttk.Label(parent, text=label, width=28).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=3)
        if values:
            control = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        else:
            control = ttk.Entry(parent, textvariable=variable)
        control.grid(row=row, column=1, sticky="ew", pady=3)
        ttk.Button(parent, text="ⓘ", width=2, command=lambda: self.show_setting_help(label, help_text)).grid(row=row, column=2, padx=(8, 0), pady=3)

    def show_setting_help(self, label, help_text):
        messagebox.showinfo(label, help_text)

    def save_settings(self):
        try:
            confidence = float(self.confidence_var.get())
            dwell = float(self.dwell_var.get())
            grace = float(self.grace_var.get())
            handoff = float(self.handoff_var.get())
            if not 0 <= confidence <= 1 or dwell < 0 or grace < 0 or handoff < 0:
                raise ValueError
            imgsz = self.imgsz_var.get().strip()
            if imgsz.lower() not in {"native", "max", "maximum"}:
                imgsz = int(imgsz)
                if imgsz <= 0:
                    raise ValueError
            camera = self.selected_camera_info()
            if camera is None:
                return False
            config_path = self.ensure_camera_config(camera)
            with config_path.open("r", encoding="utf-8") as stream:
                config = yaml.safe_load(stream) or {}
            config.update({
                "model": MODEL_FILES.get(self.model_var.get(), self.model_var.get()),
                "confidence": confidence,
                "imgsz": imgsz,
                "dwell_seconds": dwell,
                "id_switch_grace_seconds": grace,
                "id_switch_distance_pixels": handoff,
            })
            with config_path.open("w", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
        except (OSError, ValueError, TypeError, yaml.YAMLError):
            messagebox.showerror("Invalid settings", "Please enter valid tracking settings.")
            return False
        return True

    def selected_camera(self):
        camera = self.selected_camera_info()
        return camera["index"] if camera is not None else None

    def selected_camera_info(self):
        selection = self.camera_box.current()
        if selection < 0 or selection >= len(self.cameras):
            messagebox.showwarning("No camera selected", "Please select a camera first.")
            return None
        return self.cameras[selection]

    def choose_output(self):
        path = filedialog.asksaveasfilename(initialdir=PROJECT_DIR, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.output_var.set(path)

    def command_for(self, script, camera=None, include_preview=True):
        if camera is None:
            camera = self.selected_camera_info()
        if camera is None:
            return None
        config_path = self.ensure_camera_config(camera)
        command = [sys.executable, str(PROJECT_DIR / script), "--camera", str(camera["index"]), "--config", str(config_path)]
        if script == "main.py":
            command.extend(["--output", self.output_var.get()])
            if include_preview and self.preview_var.get():
                command.append("--preview")
        return command

    def start_tracking(self):
        if any(process.poll() is None for process in self.processes):
            return
        if not self.save_settings():
            return
        self.stop_camera_preview()
        command = self.command_for("main.py")
        if command is None:
            return
        self.processes = [subprocess.Popen(command, cwd=PROJECT_DIR)]
        self.start_button.config(state="disabled")
        self.start_all_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("Tracking... Click Stop to finish")
        self.root.after(500, self.check_process)

    def start_all_tracking(self):
        if any(process.poll() is None for process in self.processes):
            return
        if not self.cameras:
            messagebox.showwarning("No cameras", "No cameras are available for tracking.")
            return
        if not self.save_settings():
            return
        self.stop_camera_preview()
        commands = [
            self.command_for("main.py", camera=camera, include_preview=False)
            for camera in self.cameras
        ]
        self.processes = [subprocess.Popen(command, cwd=PROJECT_DIR) for command in commands]
        self.start_button.config(state="disabled")
        self.start_all_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set(f"Tracking {len(self.processes)} camera(s)... Click Stop to finish")
        self.root.after(500, self.check_process)

    def draw_zones(self):
        if not self.save_settings():
            return
        self.stop_camera_preview()
        command = self.command_for("draw_zones.py")
        if command is not None:
            subprocess.Popen(command, cwd=PROJECT_DIR)
            self.status_var.set("Zone drawing window opened")

    def stop_tracking(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
        self.processes = []
        self.start_button.config(state="normal")
        self.start_all_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Tracking stopped")

    def check_process(self):
        if any(process.poll() is None for process in self.processes):
            self.root.after(500, self.check_process)
        else:
            self.processes = []
            self.start_button.config(state="normal")
            self.start_all_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.status_var.set("Tracking finished")

    def close(self):
        self.stop_tracking()
        self.stop_camera_preview()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    TouchCountingApp(root)
    root.mainloop()
