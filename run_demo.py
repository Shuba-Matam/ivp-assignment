"""Optional native Windows viewer: execute the real script and inspect saved figures."""
import os
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parent


class Demo:
    def __init__(self, root):
        self.root = root
        root.title("IVP Assignment | Shuba Bhuvi Matam | RA2311031010068")
        root.geometry("1260x860")
        self.events = queue.Queue()
        self.process = None
        self.photo = None
        header = ttk.Frame(root, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="IMAGE AND VIDEO PROCESSING", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(header, text="Shuba Bhuvi Matam   |   RA2311031010068   |   21CSE480T", font=("Segoe UI", 12)).pack(anchor="w", pady=(3, 10))
        self.run_button = ttk.Button(header, text="Run all ten experiments", command=self.run)
        self.run_button.pack(side="left")
        ttk.Button(header, text="Open outputs folder", command=lambda: os.startfile(ROOT / "outputs")).pack(side="left", padx=8)
        self.status = ttk.Label(header, text="Ready", font=("Segoe UI", 11, "bold"))
        self.status.pack(side="right")
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        log_frame = ttk.Frame(self.tabs)
        self.tabs.add(log_frame, text="Execution log")
        self.log = tk.Text(log_frame, wrap="word", font=("Consolas", 11), padx=14, pady=12, bg="#f9fafb", fg="#172033")
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        self.figures = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(self.figures, text="Output figures")
        self.figure_select = ttk.Combobox(self.figures, state="readonly", width=95)
        self.figure_select.pack(fill="x")
        self.figure_select.bind("<<ComboboxSelected>>", self.show_figure)
        self.image_label = ttk.Label(self.figures, anchor="center")
        self.image_label.pack(fill="both", expand=True, pady=8)
        self.refresh_figures()
        self.root.after(100, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        if "--autorun" in sys.argv:
            root.after(500, self.run)
        elif "--show-figure" in sys.argv:
            position = sys.argv.index("--show-figure")
            if len(sys.argv) > position + 1:
                self.figure_select.set(sys.argv[position + 1])
                self.tabs.select(1)
                root.after(200, self.show_figure)

    def run(self):
        if self.process and self.process.poll() is None:
            return
        self.log.delete("1.0", "end")
        self.log.insert("end", f"Working directory: {ROOT}\nCommand: python -u assignment.py --all\n\n")
        self.status.configure(text="Running experiments")
        self.run_button.configure(state="disabled")
        self.tabs.select(0)
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "assignment.py"), "--all"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in self.process.stdout:
            self.events.put(("line", line))
        self.events.put(("done", self.process.wait()))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "line":
                    self.log.insert("end", value)
                    self.log.see("end")
                else:
                    self.log.insert("end", f"\nProcess exit code: {value}\n")
                    self.log.see("end")
                    self.status.configure(text="Completed successfully" if value == 0 else "Run failed - inspect log")
                    self.run_button.configure(state="normal")
                    self.refresh_figures()
                    status_dir = ROOT / ".work"
                    status_dir.mkdir(exist_ok=True)
                    (status_dir / "demo_status.json").write_text(json.dumps({"exit_code": value, "command": "python -u assignment.py --all"}), encoding="utf-8")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def refresh_figures(self):
        figures = sorted(p for p in (ROOT / "outputs").rglob("*.png") if "frame_" not in p.name and "screenshots" not in p.parts)
        self.figure_select["values"] = [str(p.relative_to(ROOT)) for p in figures]
        if figures:
            self.figure_select.current(0)
            self.show_figure()

    def show_figure(self, event=None):
        from PIL import Image, ImageTk
        path = ROOT / self.figure_select.get()
        if not path.is_file():
            return
        img = Image.open(path)
        img.thumbnail((1180, 670), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.image_label.configure(image=self.photo)

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.root.destroy()


if __name__ == "__main__":
    Demo(tk.Tk()).root.mainloop()
