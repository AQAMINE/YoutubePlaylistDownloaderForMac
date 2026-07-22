"""Runtime line icons (Lucide-style) for the Tk UI — crisp anti-aliased vector drawings."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
import tkinter as tk
from PIL import Image, ImageDraw

ACCENT = "#0D9488"
INK = "#0F172A"
MUTED = "#64748B"
DANGER = "#E11D48"
OK = "#059669"
BORDER = "#E2E8F0"


def _canvas(size: int, scale: int = 4) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    px = size * scale
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), scale


def _finish(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _hex_rgb(color: str) -> tuple[int, int, int, int]:
    c = color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (r, g, b, 255)


def icon_search(size: int = 18, color: str = INK) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.ellipse((4 * s, 4 * s, 13 * s, 13 * s), outline=col, width=2 * s)
    d.line((12 * s, 12 * s, 17 * s, 17 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_download(size: int = 18, color: str = ACCENT) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((10 * s, 3 * s, 10 * s, 12 * s), fill=col, width=2 * s, joint="round")
    d.line((6 * s, 8 * s, 10 * s, 12 * s), fill=col, width=2 * s, joint="round")
    d.line((14 * s, 8 * s, 10 * s, 12 * s), fill=col, width=2 * s, joint="round")
    d.line((4 * s, 16 * s, 16 * s, 16 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_cancel(size: int = 18, color: str = DANGER) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((5 * s, 5 * s, 15 * s, 15 * s), fill=col, width=2 * s, joint="round")
    d.line((15 * s, 5 * s, 5 * s, 15 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_folder(size: int = 18, color: str = INK) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.polygon(
        [
            (3 * s, 6 * s),
            (8 * s, 6 * s),
            (10 * s, 8 * s),
            (17 * s, 8 * s),
            (17 * s, 16 * s),
            (3 * s, 16 * s),
        ],
        outline=col,
        width=2 * s,
    )
    return _finish(img, size)


def icon_folder_open(size: int = 18, color: str = INK) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((3 * s, 7 * s, 8 * s, 7 * s), fill=col, width=2 * s, joint="round")
    d.line((8 * s, 7 * s, 10 * s, 5 * s), fill=col, width=2 * s, joint="round")
    d.line((10 * s, 5 * s, 17 * s, 5 * s), fill=col, width=2 * s, joint="round")
    d.polygon(
        [
            (3 * s, 9 * s),
            (15 * s, 9 * s),
            (17 * s, 16 * s),
            (5 * s, 16 * s),
        ],
        outline=col,
        width=2 * s,
    )
    return _finish(img, size)


def icon_link(size: int = 18, color: str = MUTED) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.arc((3 * s, 6 * s, 11 * s, 14 * s), 40, 320, fill=col, width=2 * s)
    d.arc((9 * s, 6 * s, 17 * s, 14 * s), 220, 140, fill=col, width=2 * s)
    d.line((8 * s, 10 * s, 12 * s, 10 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_play(size: int = 22, color: str = ACCENT) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.ellipse((1 * s, 1 * s, 19 * s, 19 * s), outline=col, width=2 * s)
    d.polygon(
        [(8 * s, 5 * s), (8 * s, 15 * s), (15 * s, 10 * s)],
        fill=col,
    )
    return _finish(img, size)


def icon_sliders(size: int = 18, color: str = MUTED) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    for y, x in ((5, 12), (10, 8), (15, 14)):
        d.line((3 * s, y * s, 17 * s, y * s), fill=col, width=2 * s, joint="round")
        d.ellipse((x * s - 2 * s, y * s - 2 * s, x * s + 2 * s, y * s + 2 * s), fill=col)
    return _finish(img, size)


def icon_activity(size: int = 18, color: str = MUTED) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line(
        [
            (2 * s, 10 * s),
            (6 * s, 10 * s),
            (8 * s, 4 * s),
            (11 * s, 16 * s),
            (13 * s, 8 * s),
            (18 * s, 8 * s),
        ],
        fill=col,
        width=2 * s,
        joint="round",
    )
    return _finish(img, size)


def icon_check(size: int = 16, color: str = OK) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((3 * s, 9 * s, 7 * s, 13 * s), fill=col, width=2 * s, joint="round")
    d.line((7 * s, 13 * s, 15 * s, 4 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_warning(size: int = 16, color: str = DANGER) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.polygon([(10 * s, 2 * s), (18 * s, 17 * s), (2 * s, 17 * s)], outline=col, width=2 * s)
    d.line((10 * s, 7 * s, 10 * s, 11 * s), fill=col, width=2 * s, joint="round")
    d.ellipse((9 * s, 13 * s, 11 * s, 15 * s), fill=col)
    return _finish(img, size)


def icon_chevron(size: int = 14, color: str = MUTED) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((3 * s, 5 * s, 7 * s, 9 * s), fill=col, width=2 * s, joint="round")
    d.line((7 * s, 9 * s, 11 * s, 5 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_monitor(size: int = 16, color: str = MUTED) -> Image.Image:
    """Quality / resolution."""
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.rounded_rectangle((2 * s, 3 * s, 14 * s, 11 * s), radius=2 * s, outline=col, width=2 * s)
    d.line((5 * s, 14 * s, 11 * s, 14 * s), fill=col, width=2 * s, joint="round")
    d.line((8 * s, 11 * s, 8 * s, 14 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def icon_film(size: int = 16, color: str = MUTED) -> Image.Image:
    """Video format."""
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.rounded_rectangle((3 * s, 2 * s, 13 * s, 14 * s), radius=2 * s, outline=col, width=2 * s)
    d.line((3 * s, 6 * s, 13 * s, 6 * s), fill=col, width=s, joint="round")
    d.line((3 * s, 10 * s, 13 * s, 10 * s), fill=col, width=s, joint="round")
    d.rectangle((3 * s, 2 * s, 5 * s, 4 * s), fill=col)
    d.rectangle((11 * s, 2 * s, 13 * s, 4 * s), fill=col)
    return _finish(img, size)


def icon_music(size: int = 16, color: str = MUTED) -> Image.Image:
    """Audio format."""
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((7 * s, 3 * s, 7 * s, 11 * s), fill=col, width=2 * s, joint="round")
    d.line((7 * s, 3 * s, 13 * s, 5 * s), fill=col, width=2 * s, joint="round")
    d.ellipse((3 * s, 10 * s, 8 * s, 14 * s), outline=col, width=2 * s)
    d.ellipse((9 * s, 8 * s, 14 * s, 12 * s), outline=col, width=2 * s)
    return _finish(img, size)


def icon_clear(size: int = 14, color: str = MUTED) -> Image.Image:
    img, d, s = _canvas(size)
    col = _hex_rgb(color)
    d.line((3 * s, 3 * s, 11 * s, 11 * s), fill=col, width=2 * s, joint="round")
    d.line((11 * s, 3 * s, 3 * s, 11 * s), fill=col, width=2 * s, joint="round")
    return _finish(img, size)


def _pil_for(name: str, size: int, color: str) -> Image.Image:
    makers = {
        "search": icon_search,
        "download": icon_download,
        "cancel": icon_cancel,
        "folder": icon_folder,
        "folder_open": icon_folder_open,
        "link": icon_link,
        "play": icon_play,
        "sliders": icon_sliders,
        "activity": icon_activity,
        "check": icon_check,
        "warning": icon_warning,
        "chevron": icon_chevron,
        "monitor": icon_monitor,
        "film": icon_film,
        "music": icon_music,
        "clear": icon_clear,
    }
    fn = makers[name]
    if color == INK and name in ("download", "cancel", "check", "warning", "play", "chevron"):
        return fn(size)
    return fn(size, color)


@lru_cache(maxsize=128)
def _icon_png(name: str, size: int, color: str) -> bytes:
    buf = BytesIO()
    _pil_for(name, size, color).save(buf, format="PNG")
    return buf.getvalue()


def photo(name: str, size: int = 18, color: str = INK, *, master=None) -> tk.PhotoImage:
    """Return a Tk-compatible PhotoImage for the named icon."""
    kw: dict = {"data": _icon_png(name, size, color)}
    if master is not None:
        kw["master"] = master
    return tk.PhotoImage(**kw)
