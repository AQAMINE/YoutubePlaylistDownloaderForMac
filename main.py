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
from icons import ACCENT, DANGER, INK, MUTED, OK, photo
from widgets import ModernButton, ModernEntry, ModernSelect

APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "settings.json"
DEFAULT_SAVE = Path.home() / "Downloads" / "YouTubeDownloads"

# Studio-tool palette (cool slate + teal — not purple / not cream-serif)
BG = "#F2F5F8"
SURFACE = "#FFFFFF"
BORDER = "#D8DEE6"
TEXT = "#1A2332"

QUALITY_LABELS = ["Best", "4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"]
QUALITY_TO_VALUE = {
    "Best": "best",
    "4320p": "4320",
    "2160p": "2160",
    "1440p": "1440",
    "1080p": "1080",
    "720p": "720",
    "480p": "480",
    "360p": "360",
    "240p": "240",
    "144p": "144",
}
VALUE_TO_QUALITY = {v: k for k, v in QUALITY_TO_VALUE.items()}
VIDEO_LABELS = [f.upper() for f in VIDEO_FORMATS]
AUDIO_LABELS = [f.upper() for f in AUDIO_FORMATS]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube Playlist Downloader")
        self.geometry("900x760")
        self.minsize(780, 680)
        self.configure(bg=BG)

        self.settings = self._load_settings()
        self._info: dict | None = None
        self._downloader: Downloader | None = None
        self._busy = False
        self._icons: dict[str, tk.PhotoImage] = {}

        self._load_icons()
        self._build_style()
        self._build_ui()
        self._refresh_ffmpeg_status()

        try:
            self.iconphoto(True, self._icons["play"])
        except tk.TclError:
            pass

    def _load_icons(self) -> None:
        """Keep PhotoImage refs on self so Tk does not garbage-collect them."""
        self._icons = {
            "play": photo("play", 28, master=self),
            "search": photo("search", 16, INK, master=self),
            "download": photo("download", 18, "#FFFFFF", master=self),
            "cancel": photo("cancel", 16, DANGER, master=self),
            "folder": photo("folder", 16, INK, master=self),
            "folder_open": photo("folder_open", 16, INK, master=self),
            "link": photo("link", 16, MUTED, master=self),
            "sliders": photo("sliders", 16, MUTED, master=self),
            "activity": photo("activity", 16, MUTED, master=self),
            "check": photo("check", 14, master=self),
            "warning": photo("warning", 14, master=self),
            "monitor": photo("monitor", 15, MUTED, master=self),
            "film": photo("film", 15, MUTED, master=self),
            "music": photo("music", 15, MUTED, master=self),
        }

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
                "audio_format": self._audio_format_value(),
                "video_format": self._video_format_value(),
                "quality": self._quality_value(),
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
        # clam gives reliable custom colors on macOS
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", background=BG, foreground=TEXT, font=("Helvetica Neue", 12))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE, relief="flat")
        style.configure(
            "TLabelframe",
            background=SURFACE,
            foreground=MUTED,
            bordercolor=BORDER,
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "TLabelframe.Label",
            background=SURFACE,
            foreground=MUTED,
            font=("Helvetica Neue", 11, "bold"),
        )
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Card.TLabel", background=SURFACE, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Helvetica Neue", 12))
        style.configure(
            "CardMuted.TLabel",
            background=SURFACE,
            foreground=MUTED,
            font=("Helvetica Neue", 11),
        )
        style.configure(
            "Title.TLabel",
            background=BG,
            foreground=TEXT,
            font=("Helvetica Neue", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=BG,
            foreground=MUTED,
            font=("Helvetica Neue", 12),
        )
        style.configure(
            "Status.TLabel",
            background=SURFACE,
            foreground=TEXT,
            font=("Helvetica Neue", 12),
        )
        style.configure(
            "TEntry",
            fieldbackground=SURFACE,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=10,
            insertcolor=TEXT,
        )
        style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, focuscolor=BG)
        style.map("TCheckbutton", background=[("active", SURFACE)])
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=10,
        )

    def _section_header(self, parent: tk.Misc, icon: str, title: str) -> ttk.Frame:
        row = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(row, image=self._icons[icon], style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(
            row,
            text=title,
            style="Card.TLabel",
            font=("Helvetica Neue", 11, "bold"),
            foreground=MUTED,
        ).pack(side=tk.LEFT)
        return row

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=(18, 14))
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, image=self._icons["play"]).pack(side=tk.LEFT, padx=(0, 12))
        titles = ttk.Frame(header)
        titles.pack(side=tk.LEFT, fill=tk.X)
        ttk.Label(titles, text="Playlist Downloader", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            titles,
            text="Paste a YouTube video, playlist, or channel URL",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        url_card = ttk.LabelFrame(outer, text="", padding=12)
        url_card.pack(fill=tk.X, pady=(0, 8))
        self._section_header(url_card, "link", "SOURCE").pack(anchor=tk.W, pady=(0, 8))

        url_row = ttk.Frame(url_card, style="Card.TFrame")
        url_row.pack(fill=tk.X)
        self.url_var = tk.StringVar()
        self.url_entry = ModernEntry(
            url_row, textvariable=self.url_var, font=("Helvetica Neue", 13), bg=SURFACE
        )
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self.fetch_metadata())
        self.fetch_btn = ModernButton(
            url_row,
            text="Fetch",
            icon=self._icons["search"],
            command=self.fetch_metadata,
            variant="ghost",
            bg=SURFACE,
        )
        self.fetch_btn.pack(side=tk.LEFT)

        self.info_title = ttk.Label(
            url_card, text="Waiting for a URL…", style="Status.TLabel", wraplength=740
        )
        self.info_title.pack(anchor=tk.W, pady=(8, 0))
        self.info_meta = ttk.Label(url_card, text="", style="CardMuted.TLabel")
        self.info_meta.pack(anchor=tk.W, pady=(2, 0))

        settings = ttk.LabelFrame(outer, text="", padding=12)
        settings.pack(fill=tk.X, pady=(0, 8))
        self._section_header(settings, "sliders", "DOWNLOAD SETTINGS").pack(
            anchor=tk.W, pady=(0, 8)
        )

        path_row = ttk.Frame(settings, style="Card.TFrame")
        path_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(path_row, text="Save to", style="CardMuted.TLabel").pack(side=tk.LEFT)
        self.save_var = tk.StringVar(value=self.settings["save_path"])
        self.save_entry = ModernEntry(
            path_row, textvariable=self.save_var, font=("Helvetica Neue", 12), bg=SURFACE
        )
        self.save_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.browse_btn = ModernButton(
            path_row,
            text="Browse",
            icon=self._icons["folder"],
            command=self._browse,
            variant="ghost",
            bg=SURFACE,
        )
        self.browse_btn.pack(side=tk.LEFT)

        opts = ttk.Frame(settings, style="Card.TFrame")
        opts.pack(fill=tk.X, pady=4)

        self.audio_only_var = tk.BooleanVar(value=self.settings["audio_only"])
        ttk.Checkbutton(
            opts,
            text="Audio only",
            variable=self.audio_only_var,
            command=self._toggle_mode,
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 16))

        self.skip_var = tk.BooleanVar(value=self.settings["skip_existing"])
        ttk.Checkbutton(opts, text="Skip existing", variable=self.skip_var).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 16)
        )

        self.subdir_var = tk.BooleanVar(value=self.settings["playlist_subdir"])
        ttk.Checkbutton(opts, text="Playlist folder", variable=self.subdir_var).grid(
            row=0, column=2, sticky=tk.W
        )

        fmt_row = ttk.Frame(settings, style="Card.TFrame")
        fmt_row.pack(fill=tk.X, pady=6)

        def _field(parent, label: str) -> ttk.Frame:
            col = ttk.Frame(parent, style="Card.TFrame")
            col.pack(side=tk.LEFT, padx=(0, 16))
            ttk.Label(col, text=label, style="CardMuted.TLabel").pack(anchor=tk.W, pady=(0, 4))
            return col

        q_col = _field(fmt_row, "Quality")
        self.quality_var = tk.StringVar(
            value=VALUE_TO_QUALITY.get(str(self.settings["quality"]), "1080p")
        )
        self.quality_combo = ModernSelect(
            q_col,
            values=QUALITY_LABELS,
            variable=self.quality_var,
            width=8,
            icon=self._icons["monitor"],
            bg=SURFACE,
        )
        self.quality_combo.pack(anchor=tk.W)

        v_col = _field(fmt_row, "Video format")
        self.video_fmt_var = tk.StringVar(value=str(self.settings["video_format"]).upper())
        self.video_combo = ModernSelect(
            v_col,
            values=VIDEO_LABELS,
            variable=self.video_fmt_var,
            width=6,
            icon=self._icons["film"],
            bg=SURFACE,
        )
        self.video_combo.pack(anchor=tk.W)

        a_col = _field(fmt_row, "Audio format")
        self.audio_fmt_var = tk.StringVar(value=str(self.settings["audio_format"]).upper())
        self.audio_combo = ModernSelect(
            a_col,
            values=AUDIO_LABELS,
            variable=self.audio_fmt_var,
            width=6,
            icon=self._icons["music"],
            bg=SURFACE,
        )
        self.audio_combo.pack(anchor=tk.W)

        subset = ttk.Frame(settings, style="Card.TFrame")
        subset.pack(fill=tk.X, pady=(6, 0))
        self.subset_var = tk.BooleanVar(value=self.settings["subset_enabled"])
        ttk.Checkbutton(
            subset,
            text="Download subset (indexes)",
            variable=self.subset_var,
        ).pack(anchor=tk.W)

        range_row = ttk.Frame(settings, style="Card.TFrame")
        range_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(range_row, text="Start", style="CardMuted.TLabel").pack(side=tk.LEFT)
        self.start_var = tk.StringVar(value=str(self.settings["subset_start"]))
        self.start_entry = ModernEntry(
            range_row,
            textvariable=self.start_var,
            width=4,
            fixed_width=84,
            font=("Helvetica Neue", 12),
            bg=SURFACE,
        )
        self.start_entry.pack(side=tk.LEFT, padx=(8, 16))
        ttk.Label(range_row, text="End (0 = all)", style="CardMuted.TLabel").pack(side=tk.LEFT)
        self.end_var = tk.StringVar(value=str(self.settings["subset_end"]))
        self.end_entry = ModernEntry(
            range_row,
            textvariable=self.end_var,
            width=4,
            fixed_width=84,
            font=("Helvetica Neue", 12),
            bg=SURFACE,
        )
        self.end_entry.pack(side=tk.LEFT, padx=(8, 0))

        self._toggle_mode()

        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X, pady=(6, 8))

        self.download_btn = ModernButton(
            actions,
            text="Download",
            icon=self._icons["download"],
            command=self.start_download,
            variant="primary",
            padx=16,
            pady=8,
            bg=BG,
        )
        self.download_btn.pack(side=tk.LEFT)

        self.cancel_btn = ModernButton(
            actions,
            text="Cancel",
            icon=self._icons["cancel"],
            command=self.cancel_download,
            variant="danger",
            bg=BG,
        )
        self.cancel_btn.configure(state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=10)

        self.open_btn = ModernButton(
            actions,
            text="Open folder",
            icon=self._icons["folder_open"],
            command=self._open_folder,
            variant="ghost",
            bg=BG,
        )
        self.open_btn.pack(side=tk.LEFT)

        ff_row = ttk.Frame(actions)
        ff_row.pack(side=tk.RIGHT)
        self.ffmpeg_icon = ttk.Label(ff_row, image=self._icons["check"])
        self.ffmpeg_icon.pack(side=tk.LEFT, padx=(0, 6))
        self.ffmpeg_label = ttk.Label(ff_row, text="", style="Muted.TLabel")
        self.ffmpeg_label.pack(side=tk.LEFT)

        prog = ttk.LabelFrame(outer, text="", padding=12)
        prog.pack(fill=tk.BOTH, expand=True)
        self._section_header(prog, "activity", "PROGRESS").pack(anchor=tk.W, pady=(0, 6))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(prog, textvariable=self.status_var, style="Status.TLabel").pack(anchor=tk.W)
        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=6)
        self.speed_var = tk.StringVar(value="")
        ttk.Label(prog, textvariable=self.speed_var, style="CardMuted.TLabel").pack(anchor=tk.W)

        log_wrap = tk.Frame(prog, bg=BORDER, padx=1, pady=1)
        log_wrap.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.log = tk.Text(
            log_wrap,
            height=5,
            wrap=tk.WORD,
            font=("Menlo", 11),
            bg="#0F172A",
            fg="#E2E8F0",
            insertbackground="#E2E8F0",
            relief=tk.FLAT,
            padx=10,
            pady=8,
            highlightthickness=0,
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.configure(state=tk.DISABLED)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _toggle_mode(self) -> None:
        audio = self.audio_only_var.get()
        self.quality_combo.configure(state=tk.DISABLED if audio else tk.NORMAL)
        self.video_combo.configure(state=tk.DISABLED if audio else tk.NORMAL)
        self.audio_combo.configure(state=tk.NORMAL if audio else tk.DISABLED)

    def _quality_value(self) -> str:
        return QUALITY_TO_VALUE.get(self.quality_var.get(), "1080")

    def _video_format_value(self) -> str:
        return self.video_fmt_var.get().lower()

    def _audio_format_value(self) -> str:
        return self.audio_fmt_var.get().lower()

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
            self.ffmpeg_icon.configure(image=self._icons["check"])
            self.ffmpeg_label.configure(text="FFmpeg ready", foreground=OK)
        else:
            self.ffmpeg_icon.configure(image=self._icons["warning"])
            self.ffmpeg_label.configure(text="FFmpeg missing", foreground=DANGER)

    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.download_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.cancel_btn.configure(state=tk.NORMAL if busy else tk.DISABLED)
        self.fetch_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)

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
                    audio_format=self._audio_format_value(),
                    video_format=self._video_format_value(),
                    quality=self._quality_value(),
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
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Missing dependency. Run:")
        print(f"  pip3 install -r \"{APP_DIR / 'requirements.txt'}\"")
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
