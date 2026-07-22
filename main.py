#!/usr/bin/env python3
"""YouTube Playlist Downloader — Python / macOS version."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# macOS python.org builds often lack CA certs — fix SSL before any network use.
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

from downloader import (
    AUDIO_FORMATS,
    VIDEO_FORMATS,
    VIDEO_QUALITIES,
    DownloadCancelled,
    Downloader,
    fetch_info,
    ffmpeg_available,
    summarize_info,
)

APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "settings.json"
DEFAULT_SAVE = Path.home() / "Downloads" / "YouTubeDownloads"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube Playlist Downloader")
        self.geometry("780x640")
        self.minsize(680, 560)
        self.configure(bg="#1e1e1e")

        self.settings = self._load_settings()
        self._info: dict | None = None
        self._downloader: Downloader | None = None
        self._busy = False

        self._build_style()
        self._build_ui()
        self._refresh_ffmpeg_status()

    # ── settings ──────────────────────────────────────────────
    def _load_settings(self) -> dict:
        defaults = {
            "save_path": str(DEFAULT_SAVE),
            "audio_only": False,
            "audio_format": "mp3",
            "video_format": "mp4",
            "quality": "1080",
            "skip_existing": True,
            "playlist_subdir": True,
            "subset_enabled": False,
            "subset_start": 1,
            "subset_end": 0,
        }
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                defaults.update(data)
            except (json.JSONDecodeError, OSError):
                pass
        return defaults

    def _save_settings(self) -> None:
        self.settings.update(
            {
                "save_path": self.save_var.get(),
                "audio_only": self.audio_only_var.get(),
                "audio_format": self.audio_fmt_var.get(),
                "video_format": self.video_fmt_var.get(),
                "quality": self.quality_var.get(),
                "skip_existing": self.skip_var.get(),
                "playlist_subdir": self.subdir_var.get(),
                "subset_enabled": self.subset_var.get(),
                "subset_start": int(self.start_var.get() or 1),
                "subset_end": int(self.end_var.get() or 0),
            }
        )
        SETTINGS_PATH.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")

    # ── UI ────────────────────────────────────────────────────
    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"))
        style.configure("Status.TLabel", font=("Helvetica", 11))
        style.configure("Muted.TLabel", foreground="#666666")
        style.configure("Accent.TButton", font=("Helvetica", 12, "bold"))

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 6}
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="YouTube Playlist Downloader", style="Title.TLabel").pack(
            anchor=tk.W, pady=(0, 4)
        )
        ttk.Label(
            root,
            text="Paste a video, playlist, or channel URL",
            style="Muted.TLabel",
        ).pack(anchor=tk.W)

        # URL
        url_row = ttk.Frame(root)
        url_row.pack(fill=tk.X, **pad)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var, font=("Helvetica", 13))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda _e: self.fetch_metadata())
        ttk.Button(url_row, text="Fetch", command=self.fetch_metadata).pack(side=tk.LEFT)

        # Info panel
        info = ttk.LabelFrame(root, text="Info", padding=10)
        info.pack(fill=tk.X, **pad)
        self.info_title = ttk.Label(info, text="—", style="Status.TLabel", wraplength=700)
        self.info_title.pack(anchor=tk.W)
        self.info_meta = ttk.Label(info, text="", style="Muted.TLabel")
        self.info_meta.pack(anchor=tk.W, pady=(4, 0))

        # Settings
        settings = ttk.LabelFrame(root, text="Download settings", padding=10)
        settings.pack(fill=tk.X, **pad)

        path_row = ttk.Frame(settings)
        path_row.pack(fill=tk.X, pady=2)
        ttk.Label(path_row, text="Save to:").pack(side=tk.LEFT)
        self.save_var = tk.StringVar(value=self.settings["save_path"])
        ttk.Entry(path_row, textvariable=self.save_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=8
        )
        ttk.Button(path_row, text="Browse…", command=self._browse).pack(side=tk.LEFT)

        opts = ttk.Frame(settings)
        opts.pack(fill=tk.X, pady=8)

        self.audio_only_var = tk.BooleanVar(value=self.settings["audio_only"])
        ttk.Checkbutton(
            opts, text="Audio only", variable=self.audio_only_var, command=self._toggle_mode
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 12))

        self.skip_var = tk.BooleanVar(value=self.settings["skip_existing"])
        ttk.Checkbutton(opts, text="Skip existing", variable=self.skip_var).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 12)
        )

        self.subdir_var = tk.BooleanVar(value=self.settings["playlist_subdir"])
        ttk.Checkbutton(
            opts, text="Playlist folder", variable=self.subdir_var
        ).grid(row=0, column=2, sticky=tk.W)

        fmt_row = ttk.Frame(settings)
        fmt_row.pack(fill=tk.X, pady=2)

        ttk.Label(fmt_row, text="Quality:").pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value=str(self.settings["quality"]))
        self.quality_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.quality_var,
            values=VIDEO_QUALITIES,
            width=8,
            state="readonly",
        )
        self.quality_combo.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(fmt_row, text="Video format:").pack(side=tk.LEFT)
        self.video_fmt_var = tk.StringVar(value=self.settings["video_format"])
        self.video_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.video_fmt_var,
            values=VIDEO_FORMATS,
            width=6,
            state="readonly",
        )
        self.video_combo.pack(side=tk.LEFT, padx=(4, 16))

        ttk.Label(fmt_row, text="Audio format:").pack(side=tk.LEFT)
        self.audio_fmt_var = tk.StringVar(value=self.settings["audio_format"])
        self.audio_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.audio_fmt_var,
            values=AUDIO_FORMATS,
            width=6,
            state="readonly",
        )
        self.audio_combo.pack(side=tk.LEFT, padx=4)

        subset = ttk.Frame(settings)
        subset.pack(fill=tk.X, pady=6)
        self.subset_var = tk.BooleanVar(value=self.settings["subset_enabled"])
        ttk.Checkbutton(subset, text="Download subset (indexes)", variable=self.subset_var).pack(
            side=tk.LEFT
        )
        ttk.Label(subset, text="Start:").pack(side=tk.LEFT, padx=(12, 2))
        self.start_var = tk.StringVar(value=str(self.settings["subset_start"]))
        ttk.Entry(subset, textvariable=self.start_var, width=5).pack(side=tk.LEFT)
        ttk.Label(subset, text="End (0 = all):").pack(side=tk.LEFT, padx=(8, 2))
        self.end_var = tk.StringVar(value=str(self.settings["subset_end"]))
        ttk.Entry(subset, textvariable=self.end_var, width=5).pack(side=tk.LEFT)

        self._toggle_mode()

        # Actions
        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, **pad)
        self.download_btn = ttk.Button(
            actions, text="Download", style="Accent.TButton", command=self.start_download
        )
        self.download_btn.pack(side=tk.LEFT)
        self.cancel_btn = ttk.Button(actions, text="Cancel", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="Open folder", command=self._open_folder).pack(side=tk.LEFT)

        self.ffmpeg_label = ttk.Label(actions, text="", style="Muted.TLabel")
        self.ffmpeg_label.pack(side=tk.RIGHT)

        # Progress
        prog = ttk.LabelFrame(root, text="Progress", padding=10)
        prog.pack(fill=tk.BOTH, expand=True, **pad)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(prog, textvariable=self.status_var, style="Status.TLabel").pack(anchor=tk.W)
        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=8)
        self.speed_var = tk.StringVar(value="")
        ttk.Label(prog, textvariable=self.speed_var, style="Muted.TLabel").pack(anchor=tk.W)

        self.log = tk.Text(prog, height=10, wrap=tk.WORD, font=("Menlo", 11))
        self.log.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.log.configure(state=tk.DISABLED)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _toggle_mode(self) -> None:
        audio = self.audio_only_var.get()
        self.quality_combo.configure(state=tk.DISABLED if audio else "readonly")
        self.video_combo.configure(state=tk.DISABLED if audio else "readonly")
        self.audio_combo.configure(state="readonly" if audio else tk.DISABLED)

    def _browse(self) -> None:
        path = filedialog.askdirectory(initialdir=self.save_var.get() or str(Path.home()))
        if path:
            self.save_var.set(path)

    def _open_folder(self) -> None:
        path = Path(self.save_var.get())
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(path)], check=False)

    def _refresh_ffmpeg_status(self) -> None:
        if ffmpeg_available():
            self.ffmpeg_label.configure(text="FFmpeg: found")
        else:
            self.ffmpeg_label.configure(text="FFmpeg: missing")

    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.download_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.cancel_btn.configure(state=tk.NORMAL if busy else tk.DISABLED)

    # ── fetch ─────────────────────────────────────────────────
    def fetch_metadata(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste a YouTube URL first.")
            return
        if self._busy:
            return

        self.status_var.set("Fetching info…")
        self.info_title.configure(text="Loading…")
        self.info_meta.configure(text="")
        self._append_log(f"Fetching: {url}")

        def work() -> None:
            try:
                raw = fetch_info(url)
                summary = summarize_info(raw)
                self.after(0, lambda s=summary: self._on_info(s))
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
                self.after(0, lambda e=err: self._on_info_error(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_info(self, summary: dict) -> None:
        self._info = summary
        self.info_title.configure(text=summary["title"])
        kind = "Playlist / channel" if summary["kind"] == "playlist" else "Video"
        extra = f"{kind}  ·  {summary['count']} item(s)"
        if summary.get("uploader"):
            extra += f"  ·  {summary['uploader']}"
        if summary.get("view_count"):
            extra += f"  ·  {summary['view_count']:,} views"
        self.info_meta.configure(text=extra)
        self.status_var.set("Ready to download")
        self._append_log(f"Found: {summary['title']} ({summary['count']} items)")

    def _on_info_error(self, err: str) -> None:
        self._info = None
        self.info_title.configure(text="Could not load URL")
        self.info_meta.configure(text=err)
        self.status_var.set("Error")
        self._append_log(f"Error: {err}")
        messagebox.showerror("Fetch failed", err)

    # ── download ──────────────────────────────────────────────
    def start_download(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste a YouTube URL first.")
            return
        if self._busy:
            return

        if not ffmpeg_available():
            messagebox.showerror(
                "FFmpeg required",
                "Videos have no sound without FFmpeg (it merges audio + video).\n\n"
                "Install with:\n  brew install ffmpeg\n\n"
                "Then restart this app and download again.",
            )
            return

        try:
            start = int(self.start_var.get() or 1) if self.subset_var.get() else None
            end = int(self.end_var.get() or 0) if self.subset_var.get() else None
            if end == 0:
                end = None
        except ValueError:
            messagebox.showerror("Invalid subset", "Start/End must be numbers.")
            return

        self._save_settings()
        self._set_busy(True)
        self.progress["value"] = 0
        self.speed_var.set("")
        self.status_var.set("Downloading…")
        playlist_title = (self._info or {}).get("title")

        def on_progress(status: dict) -> None:
            self.after(0, lambda: self._handle_progress(status))

        def on_log(msg: str) -> None:
            self.after(0, lambda: self._append_log(msg))

        def work() -> None:
            self._downloader = Downloader(on_progress=on_progress, on_log=on_log)
            try:
                self._downloader.download(
                    url,
                    save_path=Path(self.save_var.get()),
                    audio_only=self.audio_only_var.get(),
                    audio_format=self.audio_fmt_var.get(),
                    video_format=self.video_fmt_var.get(),
                    quality=self.quality_var.get(),
                    playlist_start=start,
                    playlist_end=end,
                    skip_existing=self.skip_var.get(),
                    playlist_subdir=self.subdir_var.get(),
                    playlist_title=playlist_title,
                )
                self.after(0, self._on_download_done)
            except DownloadCancelled:
                self.after(0, lambda: self._on_download_fail("Cancelled"))
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
                self.after(0, lambda e=err: self._on_download_fail(e))

        threading.Thread(target=work, daemon=True).start()

    def _handle_progress(self, status: dict) -> None:
        st = status.get("status")
        if st == "downloading":
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            done = status.get("downloaded_bytes") or 0
            if total:
                pct = done / total * 100
                self.progress["value"] = pct
            speed = status.get("_speed_str") or status.get("speed")
            eta = status.get("_eta_str") or ""
            filename = Path(status.get("filename") or "").name
            if isinstance(speed, (int, float)) and speed:
                speed_txt = f"{speed / (1024 * 1024):.2f} MiB/s"
            else:
                speed_txt = str(speed or "")
            self.speed_var.set(f"{speed_txt}  {eta}".strip())
            if filename:
                self.status_var.set(f"Downloading: {filename}")
        elif st == "finished":
            self.progress["value"] = 100
            filename = Path(status.get("filename") or "").name
            self._append_log(f"Finished: {filename}")
            self.status_var.set("Processing…")

    def _on_download_done(self) -> None:
        self._set_busy(False)
        self.progress["value"] = 100
        self.status_var.set("Download complete")
        self.speed_var.set("")
        self._append_log("All downloads finished.")
        messagebox.showinfo("Done", "Download complete.")

    def _on_download_fail(self, err: str) -> None:
        self._set_busy(False)
        self.status_var.set(err)
        self._append_log(f"Stopped: {err}")
        if err != "Cancelled":
            messagebox.showerror("Download failed", err)

    def cancel_download(self) -> None:
        if self._downloader:
            self._downloader.cancel()
            self.status_var.set("Cancelling…")

    def _on_close(self) -> None:
        try:
            self._save_settings()
        except OSError:
            pass
        if self._downloader:
            self._downloader.cancel()
        self.destroy()


def main() -> None:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print("Missing dependency. Run:")
        print(f"  pip3 install -r \"{APP_DIR / 'requirements.txt'}\"")
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
