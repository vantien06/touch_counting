import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2


PROJECT_DIR = Path(__file__).resolve().parent
CAMERA_WIDTH = 3840
CAMERA_HEIGHT = 2160


def find_cameras(max_index=10):
    cameras = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if capture.isOpened():
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                ok, frame = capture.read()
                if ok and frame is not None:
                    cameras.append((index, frame.shape[1], frame.shape[0]))
        finally:
            capture.release()
    return cameras


class TouchCountingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Touch Counting")
        self.root.geometry("560x300")
        self.root.resizable(False, False)
        self.cameras = []
        self.process = None

        main = ttk.Frame(root, padding=18)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Touch Counting", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="Chọn camera và thao tác với chương trình").pack(anchor="w", pady=(2, 18))

        camera_row = ttk.Frame(main)
        camera_row.pack(fill="x", pady=5)
        ttk.Label(camera_row, text="Camera", width=16).pack(side="left")
        self.camera_var = tk.StringVar()
        self.camera_box = ttk.Combobox(camera_row, textvariable=self.camera_var, state="readonly", width=38)
        self.camera_box.pack(side="left", fill="x", expand=True)
        ttk.Button(camera_row, text="Lam moi", command=self.refresh_cameras).pack(side="left", padx=(8, 0))

        config_row = ttk.Frame(main)
        config_row.pack(fill="x", pady=5)
        ttk.Label(config_row, text="Config", width=16).pack(side="left")
        self.config_var = tk.StringVar(value=str(PROJECT_DIR / "config.yaml"))
        ttk.Entry(config_row, textvariable=self.config_var).pack(side="left", fill="x", expand=True)
        ttk.Button(config_row, text="Chon", command=self.choose_config).pack(side="left", padx=(8, 0))

        output_row = ttk.Frame(main)
        output_row.pack(fill="x", pady=5)
        ttk.Label(output_row, text="CSV ket qua", width=16).pack(side="left")
        self.output_var = tk.StringVar(value=str(PROJECT_DIR / "events.csv"))
        ttk.Entry(output_row, textvariable=self.output_var).pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="Chon", command=self.choose_output).pack(side="left", padx=(8, 0))

        self.preview_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Mo cua so preview", variable=self.preview_var).pack(anchor="w", pady=(10, 4))

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(12, 0))
        self.start_button = ttk.Button(buttons, text="Bat dau tracking", command=self.start_tracking)
        self.start_button.pack(side="left")
        ttk.Button(buttons, text="Ve / sua zone", command=self.draw_zones).pack(side="left", padx=8)
        self.stop_button = ttk.Button(buttons, text="Dung", command=self.stop_tracking, state="disabled")
        self.stop_button.pack(side="left")

        self.status_var = tk.StringVar(value="Dang tim camera...")
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(18, 0))
        self.refresh_cameras()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def refresh_cameras(self):
        self.status_var.set("Dang tim camera...")
        self.root.update_idletasks()
        self.cameras = find_cameras()
        labels = [f"Camera {index} - {width}x{height}" for index, width, height in self.cameras]
        self.camera_box["values"] = labels
        if labels:
            self.camera_box.current(0)
            self.status_var.set(f"Tim thay {len(labels)} camera")
        else:
            self.camera_var.set("")
            self.status_var.set("Khong tim thay camera")

    def selected_camera(self):
        selection = self.camera_box.current()
        if selection < 0 or selection >= len(self.cameras):
            messagebox.showwarning("Chua chon camera", "Hay chon mot camera truoc.")
            return None
        return self.cameras[selection][0]

    def choose_config(self):
        path = filedialog.askopenfilename(initialdir=PROJECT_DIR, filetypes=[("YAML", "*.yaml"), ("All files", "*.*")])
        if path:
            self.config_var.set(path)

    def choose_output(self):
        path = filedialog.asksaveasfilename(initialdir=PROJECT_DIR, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.output_var.set(path)

    def command_for(self, script):
        camera = self.selected_camera()
        if camera is None:
            return None
        command = [sys.executable, str(PROJECT_DIR / script), "--camera", str(camera), "--config", self.config_var.get()]
        if script == "main.py":
            command.extend(["--output", self.output_var.get()])
            if self.preview_var.get():
                command.append("--preview")
        return command

    def start_tracking(self):
        if self.process and self.process.poll() is None:
            return
        command = self.command_for("main.py")
        if command is None:
            return
        self.process = subprocess.Popen(command, cwd=PROJECT_DIR)
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("Dang tracking... Nhan Dung de ket thuc")
        self.root.after(500, self.check_process)

    def draw_zones(self):
        command = self.command_for("draw_zones.py")
        if command is not None:
            subprocess.Popen(command, cwd=PROJECT_DIR)
            self.status_var.set("Cua so ve zone da duoc mo")

    def stop_tracking(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Da dung tracking")

    def check_process(self):
        if self.process and self.process.poll() is None:
            self.root.after(500, self.check_process)
        else:
            self.process = None
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.status_var.set("Tracking da ket thuc")

    def close(self):
        self.stop_tracking()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    TouchCountingApp(root)
    root.mainloop()
