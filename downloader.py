"""Download logic powered by yt-dlp (playlist / channel / video)."""

from __future__ import annotations

import re
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import yt_dlp

ProgressCallback = Callable[[dict[str, Any]], None]
LogCallback = Callable[[str], None]

VIDEO_QUALITIES = [
    "best",
    "4320",
    "2160",
    "1440",
    "1080",
    "720",
    "480",
    "360",
    "240",
    "144",
]

AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav", "aac", "ogg", "webm"]
VIDEO_FORMATS = ["mp4", "mkv", "webm"]


@lru_cache(maxsize=1)
def ffmpeg_path() -> str | None:
    """System FFmpeg, or the binary bundled via imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def ffmpeg_available() -> bool:
    return ffmpeg_path() is not None


def clean_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip(" .") or "download"


def build_ydl_opts(
    *,
    save_path: Path,
    audio_only: bool,
    audio_format: str,
    video_format: str,
    quality: str,
    playlist_start: int | None = None,
    playlist_end: int | None = None,
    skip_existing: bool = True,
    open_folder_when_done: bool = False,
    progress_hooks: list[Callable] | None = None,
) -> dict[str, Any]:
    save_path.mkdir(parents=True, exist_ok=True)
    outtmpl = str(save_path / "%(playlist_index|)s%(playlist_index& - |)s%(title)s [%(id)s].%(ext)s")

    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "ignoreerrors": True,
        "noplaylist": False,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": progress_hooks or [],
        "retries": 3,
        "fragment_retries": 3,
    }

    ff = ffmpeg_path()
    if ff:
        opts["ffmpeg_location"] = ff

    if skip_existing:
        opts["overwrites"] = False
        opts["nooverwrites"] = True

    if playlist_start and playlist_start > 0:
        opts["playliststart"] = playlist_start
    if playlist_end and playlist_end > 0:
        opts["playlistend"] = playlist_end

    has_ffmpeg = bool(ff)

    if audio_only:
        opts["format"] = "bestaudio/best"
        if has_ffmpeg:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                },
                {"key": "FFmpegMetadata"},
            ]
    else:
        height_filter = "" if quality == "best" else f"[height<={quality}]"
        if has_ffmpeg:
            # Separate video+audio streams merged by FFmpeg (has sound + best quality).
            opts["format"] = (
                f"bestvideo{height_filter}+bestaudio/best{height_filter}/best"
            )
            opts["merge_output_format"] = video_format
            if video_format in ("mp4", "mkv"):
                opts["postprocessors"] = [{"key": "FFmpegMetadata"}]
        else:
            # No FFmpeg: must pick a single progressive file that already includes audio.
            opts["format"] = (
                f"best{height_filter}[acodec!=none][vcodec!=none]/"
                f"best{height_filter}[acodec!=none]/best[acodec!=none]/best"
            )

    return opts


def fetch_info(url: str) -> dict[str, Any]:
    """Return yt-dlp metadata for a URL (flat playlist when possible)."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise ValueError("Could not fetch information for this URL.")
    return info


def summarize_info(info: dict[str, Any]) -> dict[str, Any]:
    entries = info.get("entries")
    if entries is not None:
        videos = [e for e in entries if e]
        title = info.get("title") or info.get("uploader") or "Playlist / Channel"
        uploader = info.get("uploader") or info.get("channel") or ""
        thumb = ""
        if videos:
            vid = videos[0].get("id") or ""
            if vid:
                thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
        return {
            "kind": "playlist",
            "title": title,
            "uploader": uploader,
            "count": len(videos),
            "thumbnail": thumb,
            "entries": videos,
        }

    video_id = info.get("id", "")
    return {
        "kind": "video",
        "title": info.get("title") or "Video",
        "uploader": info.get("uploader") or info.get("channel") or "",
        "count": 1,
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else "",
        "entries": [info],
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
    }


class DownloadCancelled(Exception):
    pass


class Downloader:
    def __init__(
        self,
        on_progress: ProgressCallback | None = None,
        on_log: LogCallback | None = None,
    ):
        self.on_progress = on_progress
        self.on_log = on_log
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _hook(self, status: dict[str, Any]) -> None:
        if self._cancel:
            raise DownloadCancelled("Download cancelled by user.")
        if self.on_progress:
            self.on_progress(status)

    def download(
        self,
        url: str,
        *,
        save_path: Path,
        audio_only: bool = False,
        audio_format: str = "mp3",
        video_format: str = "mp4",
        quality: str = "1080",
        playlist_start: int | None = None,
        playlist_end: int | None = None,
        skip_existing: bool = True,
        playlist_subdir: bool = False,
        playlist_title: str | None = None,
    ) -> None:
        self._cancel = False

        target = save_path
        if playlist_subdir and playlist_title:
            target = save_path / clean_filename(playlist_title)

        if not ffmpeg_available():
            raise RuntimeError(
                "FFmpeg is required so videos include sound.\n\n"
                "Install with: pip install imageio-ffmpeg\n"
                "Or: brew install ffmpeg\n\n"
                "Then restart the app and download again."
            )

        opts = build_ydl_opts(
            save_path=target,
            audio_only=audio_only,
            audio_format=audio_format,
            video_format=video_format,
            quality=quality,
            playlist_start=playlist_start,
            playlist_end=playlist_end,
            skip_existing=skip_existing,
            progress_hooks=[self._hook],
        )

        if self.on_log:
            self.on_log(f"Starting download → {target}")

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        if self.on_log:
            self.on_log("Done.")
