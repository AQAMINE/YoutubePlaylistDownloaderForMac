#!/usr/bin/env python3
"""YouTube Playlist Downloader — Python / macOS version with modern UI/UX design."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# macOS python.org builds often lack CA certs — fix SSL before any network use.
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    certifi = None  # type: ignore[assignment]

from PIL import Image, ImageDraw, ImageTk

from downloader import (
    AUDIO_FORMATS,
    VIDEO_FORMATS,
    DownloadCancelled,
    Downloader,
    fetch_info,
    ffmpeg_available,
    summarize_info,
)
from icons import ACCENT, DANGER, INK, MUTED, OK, photo
from widgets import ModernButton, ModernCheckbutton, ModernEntry, ModernSelect

APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "settings.json"
DEFAULT_SAVE = Path.home() / "Downloads" / "YouTubeDownloads"

# Modern Palette Tokens (Slate & Vibrant Teal)
BG = "#F8FAFC"
SURFACE = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT = "#0F172A"
TEXT_MUTED = "#64748B"

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
        self.geometry("920x800")
        self.minsize(820, 720)
        self.configure(bg=BG)

        self.settings = self._load_settings()
        self._info: dict | None = None
        self._downloader: Downloader | None = None
        self._busy = False
        self._icons: dict[str, tk.PhotoImage] = {}
        self._thumb_photo: ImageTk.PhotoImage | None = None
        self._thumb_token = 0

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
            "link": photo("link", 16, ACCENT, master=self),
            "sliders": photo("sliders", 16, ACCENT, master=self),
            "activity": photo("activity", 16, ACCENT, master=self),
            "check": photo("check", 14, OK, master=self),
            "warning": photo("warning", 14, DANGER, master=self),
            "monitor": photo("monitor", 16, MUTED, master=self),
            "film": photo("film", 16, MUTED, master=self),
            "music": photo("music", 16, MUTED, master=self),
            "clear": photo("clear", 12, MUTED, master=self),
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
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", background=BG, foreground=TEXT, font=("Helvetica Neue", 12))
        style.configure("TFrame", background=BG)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Helvetica Neue", 22, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=TEXT_MUTED, font=("Helvetica Neue", 12))
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=12,
        )

    def _card(self, parent: tk.Misc, *, pady: tuple[int, int] = (0, 10)) -> tk.Frame:
        """Sleek white card container with rounded aesthetics and continuous border."""
        shell = tk.Frame(parent, bg=BORDER, highlightthickness=0, bd=0)
        shell.pack(fill=tk.BOTH, expand=False, pady=pady)

        inner = tk.Frame(shell, bg=SURFACE, highlightthickness=0, bd=0)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        content = tk.Frame(inner, bg=SURFACE, highlightthickness=0, bd=0)
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)
        return content

    def _section_header(self, parent: tk.Misc, icon: str, title: str) -> tk.Frame:
        row = tk.Frame(parent, bg=SURFACE)
        badge = tk.Frame(row, bg="#F0FDFA", padx=6, pady=4)
        badge.pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(badge, image=self._icons[icon], bg="#F0FDFA", bd=0).pack(side=tk.LEFT)

        tk.Label(
            row,
            text=title,
            bg=SURFACE,
            fg=TEXT,
            font=("Helvetica Neue", 12, "bold"),
            bd=0,
        ).pack(side=tk.LEFT)
        return row

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=(20, 16))
        outer.pack(fill=tk.BOTH, expand=True)

        # ── Header ─────────────────────────────────────────────
        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 12))

        logo_frame = tk.Frame(header, bg="#F0FDFA", padx=8, pady=8)
        logo_frame.pack(side=tk.LEFT, padx=(0, 14))
        tk.Label(logo_frame, image=self._icons["play"], bg="#F0FDFA", bd=0).pack()

        titles = ttk.Frame(header)
        titles.pack(side=tk.LEFT, fill=tk.X)
        ttk.Label(titles, text="YouTube Playlist Downloader", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            titles,
            text="Download videos, audio, playlists, or entire channels in high quality",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        # FFmpeg status badge on top-right
        ff_badge = tk.Frame(header, bg=BG)
        ff_badge.pack(side=tk.RIGHT, anchor=tk.NE)
        self.ffmpeg_icon = tk.Label(ff_badge, image=self._icons["check"], bg=BG, bd=0)
        self.ffmpeg_icon.pack(side=tk.LEFT, padx=(0, 6))
        self.ffmpeg_label = tk.Label(
            ff_badge, text="", bg=BG, fg=OK, font=("Helvetica Neue", 11, "bold")
        )
        self.ffmpeg_label.pack(side=tk.LEFT)

        # ── Source Card ────────────────────────────────────────
        url_card = self._card(outer)
        self._section_header(url_card, "link", "SOURCE MEDIA URL").pack(anchor=tk.W, pady=(0, 10))

        url_row = tk.Frame(url_card, bg=SURFACE)
        url_row.pack(fill=tk.X)
        self.url_var = tk.StringVar()
        self.url_entry = ModernEntry(
            url_row,
            textvariable=self.url_var,
            font=("Helvetica Neue", 13),
            bg=SURFACE,
            show_clear=True,
        )
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self.fetch_metadata())

        self.fetch_btn = ModernButton(
            url_row,
            text="Fetch Info",
            icon=self._icons["search"],
            command=self.fetch_metadata,
            variant="ghost",
            bg=SURFACE,
        )
        self.fetch_btn.pack(side=tk.LEFT)

        # Metadata preview: ~75% info text · ~25% first-video thumbnail
        self.preview_box = tk.Frame(
            url_card, bg="#F8FAFC", highlightthickness=1, highlightbackground=BORDER
        )
        self.preview_box.pack(fill=tk.X, pady=(10, 0))

        preview_inner = tk.Frame(self.preview_box, bg="#F8FAFC", padx=12, pady=10)
        preview_inner.pack(fill=tk.X)
        preview_inner.columnconfigure(0, weight=3, uniform="preview")
        preview_inner.columnconfigure(1, weight=1, uniform="preview")

        text_col = tk.Frame(preview_inner, bg="#F8FAFC")
        text_col.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.info_title = tk.Label(
            text_col,
            text="Paste a YouTube URL above and click Fetch Info to start",
            bg="#F8FAFC",
            fg=TEXT_MUTED,
            font=("Helvetica Neue", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.info_title.pack(anchor=tk.W, fill=tk.X)

        self.info_meta = tk.Label(
            text_col,
            text="",
            bg="#F8FAFC",
            fg=TEXT_MUTED,
            font=("Helvetica Neue", 11),
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.info_meta.pack(anchor=tk.W, fill=tk.X, pady=(4, 0))

        thumb_col = tk.Frame(preview_inner, bg="#F8FAFC")
        thumb_col.grid(row=0, column=1, sticky="nse")

        self.thumb_frame = tk.Frame(
            thumb_col,
            bg="#E2E8F0",
            width=168,
            height=94,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.thumb_frame.pack(anchor=tk.E)
        self.thumb_frame.pack_propagate(False)

        self.thumb_label = tk.Label(
            self.thumb_frame,
            text="No preview",
            image=self._icons["play"],
            compound=tk.TOP,
            bg="#E2E8F0",
            fg=TEXT_MUTED,
            font=("Helvetica Neue", 9),
            bd=0,
        )
        self.thumb_label.pack(expand=True, fill=tk.BOTH)

        preview_inner.bind("<Configure>", self._on_preview_resize)

        # ── Settings Card ──────────────────────────────────────
        settings = self._card(outer)
        self._section_header(settings, "sliders", "DOWNLOAD CONFIGURATION").pack(anchor=tk.W, pady=(0, 10))

        # Save directory
        path_row = tk.Frame(settings, bg=SURFACE)
        path_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            path_row, text="Save to", bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica Neue", 11, "bold")
        ).pack(side=tk.LEFT)
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

        # Options switches / checkboxes
        opts = tk.Frame(settings, bg=SURFACE)
        opts.pack(fill=tk.X, pady=(4, 10))

        self.audio_only_var = tk.BooleanVar(value=self.settings["audio_only"])
        self.audio_chk = ModernCheckbutton(
            opts,
            text="Audio only",
            variable=self.audio_only_var,
            command=self._toggle_mode,
            bg=SURFACE,
        )
        self.audio_chk.pack(side=tk.LEFT, padx=(0, 20))

        self.skip_var = tk.BooleanVar(value=self.settings["skip_existing"])
        self.skip_chk = ModernCheckbutton(
            opts,
            text="Skip existing files",
            variable=self.skip_var,
            bg=SURFACE,
        )
        self.skip_chk.pack(side=tk.LEFT, padx=(0, 20))

        self.subdir_var = tk.BooleanVar(value=self.settings["playlist_subdir"])
        self.subdir_chk = ModernCheckbutton(
            opts,
            text="Create playlist subfolder",
            variable=self.subdir_var,
            bg=SURFACE,
        )
        self.subdir_chk.pack(side=tk.LEFT)

        # Format & Quality Selects Row
        fmt_row = tk.Frame(settings, bg=SURFACE)
        fmt_row.pack(fill=tk.X, pady=(0, 10))

        def _field(parent, label: str) -> tk.Frame:
            col = tk.Frame(parent, bg=SURFACE)
            col.pack(side=tk.LEFT, padx=(0, 24))
            tk.Label(col, text=label, bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica Neue", 11, "bold")).pack(
                anchor=tk.W, pady=(0, 4)
            )
            return col

        q_col = _field(fmt_row, "Video Quality")
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

        v_col = _field(fmt_row, "Video Format")
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

        a_col = _field(fmt_row, "Audio Format")
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

        # Subset / Index range
        subset_row = tk.Frame(settings, bg=SURFACE)
        subset_row.pack(fill=tk.X, pady=(4, 0))

        self.subset_var = tk.BooleanVar(value=self.settings["subset_enabled"])
        self.subset_chk = ModernCheckbutton(
            subset_row,
            text="Download item subset (index range)",
            variable=self.subset_var,
            bg=SURFACE,
        )
        self.subset_chk.pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(subset_row, text="Start", bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica Neue", 11)).pack(
            side=tk.LEFT, padx=(8, 4)
        )
        self.start_var = tk.StringVar(value=str(self.settings["subset_start"]))
        self.start_entry = ModernEntry(
            subset_row,
            textvariable=self.start_var,
            width=4,
            fixed_width=64,
            font=("Helvetica Neue", 12),
            bg=SURFACE,
        )
        self.start_entry.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(
            subset_row, text="End (0 = all)", bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica Neue", 11)
        ).pack(side=tk.LEFT, padx=(0, 4))
        self.end_var = tk.StringVar(value=str(self.settings["subset_end"]))
        self.end_entry = ModernEntry(
            subset_row,
            textvariable=self.end_var,
            width=4,
            fixed_width=64,
            font=("Helvetica Neue", 12),
            bg=SURFACE,
        )
        self.end_entry.pack(side=tk.LEFT)

        self._toggle_mode()

        # ── Action Buttons ─────────────────────────────────────
        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X, pady=(4, 10))

        self.download_btn = ModernButton(
            actions,
            text="Start Download",
            icon=self._icons["download"],
            command=self.start_download,
            variant="primary",
            padx=20,
            pady=10,
            bg=BG,
        )
        self.download_btn.pack(side=tk.LEFT)

        self.cancel_btn = ModernButton(
            actions,
            text="Cancel",
            icon=self._icons["cancel"],
            command=self.cancel_download,
            variant="danger",
            padx=16,
            pady=10,
            bg=BG,
        )
        self.cancel_btn.configure(state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=12)

        self.open_btn = ModernButton(
            actions,
            text="Open Download Folder",
            icon=self._icons["folder_open"],
            command=self._open_folder,
            variant="ghost",
            padx=16,
            pady=10,
            bg=BG,
        )
        self.open_btn.pack(side=tk.LEFT)

        # ── Progress & Output Card ─────────────────────────────
        prog_shell = tk.Frame(outer, bg=BORDER, highlightthickness=0, bd=0)
        prog_shell.pack(fill=tk.BOTH, expand=True)

        prog_inner = tk.Frame(prog_shell, bg=SURFACE, highlightthickness=0, bd=0)
        prog_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        prog = tk.Frame(prog_inner, bg=SURFACE, highlightthickness=0, bd=0)
        prog.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        prog_head = tk.Frame(prog, bg=SURFACE)
        prog_head.pack(fill=tk.X, pady=(0, 8))
        self._section_header(prog_head, "activity", "PROGRESS & LOGS").pack(side=tk.LEFT)

        clear_log_btn = ModernButton(
            prog_head,
            text="Clear Logs",
            icon=self._icons["clear"],
            command=self._clear_log,
            variant="ghost",
            padx=10,
            pady=4,
            bg=SURFACE,
        )
        clear_log_btn.pack(side=tk.RIGHT)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            prog,
            textvariable=self.status_var,
            bg=SURFACE,
            fg=TEXT,
            font=("Helvetica Neue", 12, "bold"),
            anchor="w",
        ).pack(anchor=tk.W)

        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=(6, 4))

        self.speed_var = tk.StringVar(value="")
        tk.Label(
            prog,
            textvariable=self.speed_var,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=("Helvetica Neue", 11),
            anchor="w",
        ).pack(anchor=tk.W)

        log_wrap = tk.Frame(prog, bg="#0F172A", padx=1, pady=1)
        log_wrap.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.log = tk.Text(
            log_wrap,
            height=6,
            wrap=tk.WORD,
            font=("Menlo", 11),
            bg="#0F172A",
            fg="#E2E8F0",
            insertbackground="#E2E8F0",
            relief=tk.FLAT,
            padx=12,
            pady=10,
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
            self.ffmpeg_label.configure(text="FFmpeg ready", fg=OK)
        else:
            self.ffmpeg_icon.configure(image=self._icons["warning"])
            self.ffmpeg_label.configure(text="FFmpeg missing", fg=DANGER)

    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.download_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.cancel_btn.configure(state=tk.NORMAL if busy else tk.DISABLED)
        self.fetch_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)

    # ── preview / thumbnail ───────────────────────────────────
    def _on_preview_resize(self, event=None) -> None:
        width = event.width if event is not None else self.preview_box.winfo_width()
        # Text column is ~75%; leave a little margin for padding.
        wrap = max(180, int(width * 0.72) - 24)
        self.info_title.configure(wraplength=wrap)
        self.info_meta.configure(wraplength=wrap)
        thumb_w = max(120, int(width * 0.25) - 8)
        thumb_h = max(68, int(thumb_w * 9 / 16))
        self.thumb_frame.configure(width=thumb_w, height=thumb_h)

    def _clear_thumbnail(self, placeholder: str = "No preview") -> None:
        self._thumb_token += 1
        self._thumb_photo = None
        self.thumb_label.configure(
            image=self._icons["play"],
            text=placeholder,
            compound=tk.TOP,
            fg=TEXT_MUTED,
            bg="#E2E8F0",
        )

    def _set_thumbnail_photo(self, photo: ImageTk.PhotoImage | None, token: int) -> None:
        if token != self._thumb_token:
            return
        if photo is None:
            self._clear_thumbnail("Unavailable")
            return
        self._thumb_photo = photo
        self.thumb_label.configure(image=photo, text="", compound=tk.CENTER, bg="#F8FAFC")

    @staticmethod
    def _download_thumbnail_image(url: str, max_w: int, max_h: int) -> Image.Image | None:
        if not url:
            return None
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; YTPlaylistDownloader/1.0)"},
        )
        context = None
        if certifi is not None:
            import ssl

            context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=12, context=context) as resp:
            data = resp.read()
        img = Image.open(BytesIO(data)).convert("RGBA")
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        # Soft rounded corners to match the rest of the UI.
        radius = 8
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, img.size[0] - 1, img.size[1] - 1), radius=radius, fill=255)
        img.putalpha(mask)
        return img

    def _load_thumbnail_async(self, url: str) -> None:
        self._thumb_token += 1
        token = self._thumb_token
        if not url:
            self._clear_thumbnail("No preview")
            return

        self.thumb_label.configure(
            image=self._icons["play"],
            text="Loading…",
            compound=tk.TOP,
            fg=TEXT_MUTED,
            bg="#E2E8F0",
        )

        def work() -> None:
            try:
                # Size for the 25% column (~168×94 default; scales with window).
                w = max(120, self.thumb_frame.winfo_width() or 168)
                h = max(68, self.thumb_frame.winfo_height() or 94)
                pil = self._download_thumbnail_image(url, w * 2, h * 2)
                if pil is None:
                    self.after(0, lambda: self._set_thumbnail_photo(None, token))
                    return
                photo = ImageTk.PhotoImage(pil, master=self)
                self.after(0, lambda p=photo: self._set_thumbnail_photo(p, token))
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
                self.after(0, lambda: self._set_thumbnail_photo(None, token))

        threading.Thread(target=work, daemon=True).start()

    # ── fetch ─────────────────────────────────────────────────
    def fetch_metadata(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Paste a YouTube URL first.")
            return
        if self._busy:
            return

        self.status_var.set("Fetching info…")
        self.info_title.configure(text="Loading metadata from YouTube…", fg=TEXT)
        self.info_meta.configure(text="")
        self._clear_thumbnail("Loading…")
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
        self.info_title.configure(text=summary["title"], fg=TEXT)
        kind = "Playlist / Channel" if summary["kind"] == "playlist" else "Video"
        extra = f"Type: {kind}  •  {summary['count']} item(s)"
        if summary.get("uploader"):
            extra += f"  •  Channel: {summary['uploader']}"
        if summary.get("view_count"):
            extra += f"  •  {summary['view_count']:,} views"
        self.info_meta.configure(text=extra)
        self._load_thumbnail_async(summary.get("thumbnail") or "")
        self.status_var.set("Ready to download")
        self._append_log(f"Found: {summary['title']} ({summary['count']} items)")

    def _on_info_error(self, err: str) -> None:
        self._info = None
        self.info_title.configure(text="Could not load URL metadata", fg=DANGER)
        self.info_meta.configure(text=err)
        self._clear_thumbnail("No preview")
        self.status_var.set("Error fetching metadata")
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
            messagebox.showerror("Invalid subset", "Start/End must be valid numbers.")
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
            self.status_var.set("Processing video/audio streams…")

    def _on_download_done(self) -> None:
        self._set_busy(False)
        self.progress["value"] = 100
        self.status_var.set("Download complete!")
        self.speed_var.set("")
        self._append_log("All downloads finished successfully.")
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
            self.status_var.set("Cancelling download…")

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
        print(f'  pip3 install -r "{APP_DIR / "requirements.txt"}"')
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
