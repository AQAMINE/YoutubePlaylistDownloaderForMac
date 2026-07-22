"""Modern custom rounded controls (Buttons, Selects, Entries, Checkboxes) for Tkinter UI."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Callable, Sequence

import tkinter as tk
from PIL import Image, ImageDraw

from icons import ACCENT, BORDER, DANGER, INK, MUTED, OK, photo

SURFACE = "#FFFFFF"
HOVER = "#F8FAFC"
TEXT = "#0F172A"
PRIMARY_HOVER = "#0F766E"
PRIMARY_ACTIVE = "#115E59"
PRIMARY_DISABLED = "#99D5CF"
DANGER_BG = "#FFF1F2"
DANGER_BORDER = "#FECDD3"
DANGER_HOVER = "#FFE4E6"
DANGER_ACTIVE = "#FCA5A5"
CARD_BG = "#FFFFFF"


def _rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


@lru_cache(maxsize=256)
def _round_png(
    width: int,
    height: int,
    radius: int,
    fill: str,
    outline: str,
    outline_width: int = 1,
) -> bytes:
    scale = 3
    w, h, r = max(1, width * scale), max(1, height * scale), radius * scale
    ow = max(1, outline_width * scale)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer border rounded rect
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=_rgb(outline) + (255,))
    inset = ow
    if w - 1 - inset > inset and h - 1 - inset > inset:
        draw.rounded_rectangle(
            (inset, inset, w - 1 - inset, h - 1 - inset),
            radius=max(0, r - inset),
            fill=_rgb(fill) + (255,),
        )

    out = img.resize((width, height), Image.Resampling.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def round_photo(
    master,
    width: int,
    height: int,
    radius: int,
    fill: str,
    outline: str,
    outline_width: int = 1,
) -> tk.PhotoImage:
    return tk.PhotoImage(
        master=master,
        data=_round_png(max(8, width), max(8, height), radius, fill, outline, outline_width),
    )


def _parent_bg(master) -> str:
    try:
        bg = master.cget("background")
        if bg:
            return str(bg)
    except tk.TclError:
        pass
    try:
        bg = master.cget("bg")
        if bg:
            return str(bg)
    except tk.TclError:
        pass
    return CARD_BG


# ── Modern Button ────────────────────────────────────────────────────────────
class ModernButton(tk.Canvas):
    """Soft rounded button with icon, text, hover, active tactile press, and hand cursor."""

    def __init__(
        self,
        master,
        *,
        text: str,
        command: Callable | None = None,
        icon: tk.PhotoImage | None = None,
        variant: str = "ghost",
        padx: int = 16,
        pady: int = 8,
        radius: int = 10,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(
            master, highlightthickness=0, bd=0, bg=parent_bg, cursor="hand2", **kwargs
        )
        self.command = command
        self.variant = variant
        self._enabled = True
        self._icon = icon
        self._text = text
        self._padx = padx
        self._pady = pady
        self._radius = radius
        self._parent_bg = parent_bg
        self._hover = False
        self._pressed = False
        self._bg_image: tk.PhotoImage | None = None

        self.content = tk.Frame(self, bg=self._palette()["bg"], cursor="hand2")
        if icon is not None:
            self.icon_lbl = tk.Label(
                self.content, image=icon, bg=self._palette()["bg"], bd=0, cursor="hand2"
            )
            self.icon_lbl.pack(side=tk.LEFT, padx=(0, 6))
        else:
            self.icon_lbl = None

        self.text_lbl = tk.Label(
            self.content,
            text=text,
            bg=self._palette()["bg"],
            fg=self._palette()["fg"],
            font=("Helvetica Neue", 12, "bold" if variant == "primary" else "bold"),
            bd=0,
            cursor="hand2",
        )
        self.text_lbl.pack(side=tk.LEFT)

        self._window = self.create_window(0, 0, window=self.content, anchor="center")
        self.bind("<Configure>", self._redraw)
        for w in (self, self.content, self.text_lbl):
            self._bind_events(w)
        if self.icon_lbl is not None:
            self._bind_events(self.icon_lbl)

        self.after_idle(self._fit)

    def _bind_events(self, widget: tk.Misc) -> None:
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress-1>", self._on_press)
        widget.bind("<ButtonRelease-1>", self._on_release)

    def _palette(self) -> dict[str, str]:
        disabled = not self._enabled
        hover = self._hover and self._enabled
        pressed = self._pressed and self._enabled

        if self.variant == "primary":
            if disabled:
                return {"bg": PRIMARY_DISABLED, "fg": "#ECFEFF", "border": PRIMARY_DISABLED}
            if pressed:
                return {"bg": PRIMARY_ACTIVE, "fg": "#FFFFFF", "border": PRIMARY_ACTIVE}
            if hover:
                return {"bg": PRIMARY_HOVER, "fg": "#FFFFFF", "border": PRIMARY_HOVER}
            return {"bg": ACCENT, "fg": "#FFFFFF", "border": ACCENT}

        if self.variant == "danger":
            if disabled:
                return {"bg": SURFACE, "fg": "#FCA5A5", "border": "#FECACA"}
            if pressed:
                return {"bg": DANGER_ACTIVE, "fg": "#FFFFFF", "border": DANGER_ACTIVE}
            if hover:
                return {"bg": DANGER_HOVER, "fg": DANGER, "border": DANGER_BORDER}
            return {"bg": DANGER_BG, "fg": DANGER, "border": DANGER_BORDER}

        # Ghost / Secondary Variant
        if disabled:
            return {"bg": "#F8FAFC", "fg": "#94A3B8", "border": BORDER}
        if pressed:
            return {"bg": "#E2E8F0", "fg": TEXT, "border": "#94A3B8"}
        if hover:
            return {"bg": "#F1F5F9", "fg": TEXT, "border": "#CBD5E1"}
        return {"bg": SURFACE, "fg": "#1E293B", "border": BORDER}

    def _fit(self) -> None:
        self.content.update_idletasks()
        w = self.content.winfo_reqwidth() + self._padx * 2
        h = max(36, self.content.winfo_reqheight() + self._pady * 2)
        self.configure(width=w, height=h)
        self._redraw()

    def _redraw(self, _e=None) -> None:
        self.update_idletasks()
        w = max(self.winfo_width(), 40)
        h = max(self.winfo_height(), 32)
        colors = self._palette()
        self._bg_image = round_photo(
            self, w, h, self._radius, colors["bg"], colors["border"], outline_width=1
        )
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")

        # Slight tactile shift down on press
        offset = 1 if self._pressed else 0
        self.coords(self._window, w / 2, h / 2 + offset)
        self.itemconfigure(self._window, width=w - 4, height=h - 4)

        for widget in (self.content, self.text_lbl):
            widget.configure(bg=colors["bg"])
        self.text_lbl.configure(fg=colors["fg"])
        if self.icon_lbl is not None:
            self.icon_lbl.configure(bg=colors["bg"])

    def _on_enter(self, _e=None) -> None:
        if not self._enabled:
            return
        self._hover = True
        self._redraw()

    def _on_leave(self, _e=None) -> None:
        x, y = self.winfo_pointerxy()
        widget = self.winfo_containing(x, y)
        if widget is not None and str(widget).startswith(str(self)):
            return
        self._hover = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _e=None) -> None:
        if self._enabled:
            self._pressed = True
            self._redraw()

    def _on_release(self, _e=None) -> None:
        if self._enabled and self._pressed:
            self._pressed = False
            self._redraw()
            if self.command:
                self.command()

    def configure(self, cnf=None, **kwargs):  # noqa: A003
        if cnf:
            kwargs = {**cnf, **kwargs}
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._enabled = state not in (tk.DISABLED, "disabled")
            self._hover = False
            self._pressed = False
            cursor = "hand2" if self._enabled else "arrow"
            self.configure(cursor=cursor)
            self.content.configure(cursor=cursor)
            self.text_lbl.configure(cursor=cursor)
            if self.icon_lbl is not None:
                self.icon_lbl.configure(cursor=cursor)
            self._redraw()
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            self.text_lbl.configure(text=self._text)
            self.after_idle(self._fit)
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if kwargs:
            return super().configure(**kwargs)
        return None

    config = configure


# ── Modern Select / Dropdown ──────────────────────────────────────────────────
class ModernSelect(tk.Canvas):
    """Rounded dropdown select trigger box with icon and popup menu."""

    _open_menu: ModernSelect | None = None

    def __init__(
        self,
        master,
        *,
        values: Sequence[str],
        variable: tk.StringVar | None = None,
        width: int = 10,
        command: Callable | None = None,
        icon: tk.PhotoImage | None = None,
        radius: int = 10,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(
            master, highlightthickness=0, bd=0, bg=parent_bg, cursor="hand2", **kwargs
        )
        self.values = list(values)
        self.variable = variable or tk.StringVar(value=self.values[0] if self.values else "")
        self.command = command
        self._enabled = True
        self._popup: tk.Toplevel | None = None
        self._radius = radius
        self._parent_bg = parent_bg
        self._hover = False
        self._min_char_width = width
        self._bg_image: tk.PhotoImage | None = None
        self._popup_bg: tk.PhotoImage | None = None
        self._leading_icon = icon

        root = self.winfo_toplevel()
        self._chevron = photo("chevron", 12, MUTED, master=root)
        self._check = photo("check", 14, ACCENT, master=root)

        self.inner = tk.Frame(self, bg=SURFACE, cursor="hand2")

        if icon is not None:
            self.leading_lbl = tk.Label(self.inner, image=icon, bg=SURFACE, bd=0, cursor="hand2")
            self.leading_lbl.pack(side=tk.LEFT, padx=(10, 6), pady=6)
        else:
            self.leading_lbl = None

        self.value_lbl = tk.Label(
            self.inner,
            textvariable=self.variable,
            bg=SURFACE,
            fg=TEXT,
            font=("Helvetica Neue", 12, "bold"),
            anchor="w",
            bd=0,
            cursor="hand2",
        )
        self.value_lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 6), pady=6)

        self.chevron_lbl = tk.Label(self.inner, image=self._chevron, bg=SURFACE, bd=0, cursor="hand2")
        self.chevron_lbl.pack(side=tk.RIGHT, padx=(4, 10), pady=6)

        self._window = self.create_window(0, 0, window=self.inner, anchor="center")
        self.bind("<Configure>", self._redraw)

        targets = [self, self.inner, self.value_lbl, self.chevron_lbl]
        if self.leading_lbl is not None:
            targets.append(self.leading_lbl)
        for w in targets:
            w.bind("<Button-1>", self._toggle)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        self.after_idle(self._fit)

    def _fit(self) -> None:
        self.inner.update_idletasks()
        req_w = self.inner.winfo_reqwidth() + 16
        min_w = self._min_char_width * 11 + (32 if self._leading_icon else 0) + 36
        w = max(req_w, min_w)
        h = max(38, self.inner.winfo_reqheight() + 8)
        self.configure(width=w, height=h)
        self._redraw()

    def _colors(self) -> dict[str, str]:
        if not self._enabled:
            return {"bg": "#F8FAFC", "fg": "#94A3B8", "border": BORDER}
        if self._popup or self._hover:
            return {"bg": SURFACE, "fg": TEXT, "border": ACCENT}
        return {"bg": SURFACE, "fg": TEXT, "border": BORDER}

    def _redraw(self, _e=None) -> None:
        self.update_idletasks()
        w = max(self.winfo_width(), 90)
        h = max(self.winfo_height(), 38)
        colors = self._colors()

        self._bg_image = round_photo(
            self, w, h, self._radius, colors["bg"], colors["border"], outline_width=1
        )
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")

        self.coords(self._window, w / 2, h / 2)
        self.itemconfigure(self._window, width=w - 4, height=h - 4)

        widgets = [self.inner, self.value_lbl, self.chevron_lbl]
        if self.leading_lbl is not None:
            widgets.append(self.leading_lbl)
        for widget in widgets:
            widget.configure(bg=colors["bg"])
        self.value_lbl.configure(fg=colors["fg"])

    def _on_enter(self, _e=None) -> None:
        if not self._enabled:
            return
        self._hover = True
        self._redraw()

    def _on_leave(self, _e=None) -> None:
        x, y = self.winfo_pointerxy()
        widget = self.winfo_containing(x, y)
        if widget is not None and str(widget).startswith(str(self)):
            return
        if self._popup:
            return
        self._hover = False
        self._redraw()

    def _toggle(self, _e=None) -> None:
        if not self._enabled:
            return
        if self._popup:
            self._close()
        else:
            self._open()

    def _close(self) -> None:
        if self._popup is not None:
            try:
                self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None
        if ModernSelect._open_menu is self:
            ModernSelect._open_menu = None
        self._hover = False
        self._redraw()

    def _open(self) -> None:
        if ModernSelect._open_menu and ModernSelect._open_menu is not self:
            ModernSelect._open_menu._close()

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        width = max(self.winfo_width(), 160)
        row_h = 36
        pad = 8
        height = min(len(self.values) * row_h + pad * 2, 280)

        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=self._parent_bg)

        canvas = tk.Canvas(
            popup, width=width, height=height, highlightthickness=0, bd=0, bg=self._parent_bg
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        self._popup_bg = round_photo(popup, width, height, 12, SURFACE, BORDER, outline_width=1)
        canvas.create_image(0, 0, image=self._popup_bg, anchor="nw")

        menu = tk.Frame(canvas, bg=SURFACE)
        canvas.create_window(
            pad, pad, window=menu, anchor="nw", width=width - pad * 2, height=height - pad * 2
        )

        current = self.variable.get()
        for value in self.values:
            selected = value == current
            row = tk.Frame(menu, bg="#F0FDFA" if selected else SURFACE, cursor="hand2")
            row.pack(fill=tk.X, pady=1, padx=2)

            if self._leading_icon is not None:
                ic = tk.Label(row, image=self._leading_icon, bg=row["bg"], bd=0, cursor="hand2")
                ic.pack(side=tk.LEFT, padx=(10, 8), pady=6)
            else:
                ic = None

            lbl = tk.Label(
                row,
                text=value,
                bg=row["bg"],
                fg=ACCENT if selected else TEXT,
                font=("Helvetica Neue", 12, "bold" if selected else "normal"),
                anchor="w",
                bd=0,
                cursor="hand2",
            )
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4 if self._leading_icon else 10, 4), pady=6)

            mark = tk.Label(
                row,
                image=self._check if selected else "",
                bg=row["bg"],
                bd=0,
                cursor="hand2",
            )
            mark.pack(side=tk.RIGHT, padx=(6, 10), pady=6)

            def _enter(e, r=row, l=lbl, m=mark, i=ic, sel=selected):
                bg = "#CCFBF1" if sel else "#F1F5F9"
                r.configure(bg=bg)
                l.configure(bg=bg)
                m.configure(bg=bg)
                if i is not None:
                    i.configure(bg=bg)

            def _leave(e, r=row, l=lbl, m=mark, i=ic, sel=selected):
                bg = "#F0FDFA" if sel else SURFACE
                r.configure(bg=bg)
                l.configure(bg=bg)
                m.configure(bg=bg)
                if i is not None:
                    i.configure(bg=bg)

            def _pick(_e=None, v=value):
                self.variable.set(v)
                self._close()
                if self.command:
                    self.command(v)

            targets = [row, lbl, mark]
            if ic is not None:
                targets.append(ic)
            for w in targets:
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)
                w.bind("<Button-1>", _pick)

        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.deiconify()
        popup.focus_force()
        popup.bind("<Escape>", lambda _e: self._close())
        popup.bind("<FocusOut>", lambda _e: self.after(120, self._maybe_close))

        self._popup = popup
        ModernSelect._open_menu = self
        self._hover = True
        self._redraw()

    def _maybe_close(self) -> None:
        if self._popup is None:
            return
        try:
            focused = self._popup.focus_get()
        except tk.TclError:
            focused = None
        if focused is None:
            self._close()

    def configure(self, cnf=None, **kwargs):  # noqa: A003
        if cnf:
            kwargs = {**cnf, **kwargs}
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._enabled = state not in (tk.DISABLED, "disabled")
            if not self._enabled:
                self._close()
            cursor = "hand2" if self._enabled else "arrow"
            self.configure(cursor=cursor)
            self.inner.configure(cursor=cursor)
            self.value_lbl.configure(cursor=cursor)
            self.chevron_lbl.configure(cursor=cursor)
            if self.leading_lbl is not None:
                self.leading_lbl.configure(cursor=cursor)
            self._redraw()
        if "values" in kwargs:
            self.values = list(kwargs.pop("values"))
        if kwargs:
            return super().configure(**kwargs)
        return None

    config = configure

    def get(self) -> str:
        return self.variable.get()

    def set(self, value: str) -> None:
        self.variable.set(value)


# ── Modern Entry ─────────────────────────────────────────────────────────────
class ModernEntry(tk.Canvas):
    """Rounded input field with focus glow and optional clear button."""

    def __init__(
        self,
        master,
        *,
        textvariable: tk.StringVar | None = None,
        font=("Helvetica Neue", 13),
        radius: int = 10,
        show: str | None = None,
        width: int | None = None,
        fixed_width: int | None = None,
        show_clear: bool = False,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(master, highlightthickness=0, bd=0, bg=parent_bg, **kwargs)
        self._radius = radius
        self._parent_bg = parent_bg
        self._focused = False
        self._hover = False
        self._fixed_width = fixed_width
        self._show_clear = show_clear
        self._bg_image: tk.PhotoImage | None = None
        self.textvariable = textvariable or tk.StringVar()

        root = self.winfo_toplevel()
        self._clear_icon = photo("clear", 12, MUTED, master=root)

        self.inner = tk.Frame(self, bg=SURFACE)
        entry_kw: dict = {
            "textvariable": self.textvariable,
            "font": font,
            "bg": SURFACE,
            "fg": TEXT,
            "relief": tk.FLAT,
            "bd": 0,
            "highlightthickness": 0,
            "insertbackground": TEXT,
        }
        if show is not None:
            entry_kw["show"] = show
        if width is not None:
            entry_kw["width"] = width

        self.entry = tk.Entry(self.inner, **entry_kw)
        pad_x = 10 if fixed_width else 12
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(pad_x, 4), pady=7)

        if show_clear:
            self.clear_btn = tk.Label(self.inner, image=self._clear_icon, bg=SURFACE, bd=0, cursor="hand2")
            self.clear_btn.bind("<Button-1>", lambda _e: self.textvariable.set(""))
            self.clear_btn.pack(side=tk.RIGHT, padx=(0, 10))
            self.textvariable.trace_add("write", self._on_text_change)
            self._on_text_change()
        else:
            self.clear_btn = None

        self._window = self.create_window(0, 0, window=self.inner, anchor="center")
        self.bind("<Configure>", self._redraw)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        for w in (self, self.inner, self.entry):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if fixed_width:
            self.configure(width=fixed_width, height=38)
        self.after_idle(self._fit)

    def _on_text_change(self, *_args) -> None:
        if self.clear_btn is None:
            return
        if self.textvariable.get():
            self.clear_btn.pack(side=tk.RIGHT, padx=(0, 10))
        else:
            self.clear_btn.pack_forget()

    def _fit(self) -> None:
        self.inner.update_idletasks()
        h = 38
        if self._fixed_width:
            self.configure(width=self._fixed_width, height=h)
        else:
            self.configure(height=h)
        self._redraw()

    def _colors(self) -> dict[str, str]:
        if self._focused:
            return {"bg": SURFACE, "border": ACCENT}
        if self._hover:
            return {"bg": SURFACE, "border": "#94A3B8"}
        return {"bg": SURFACE, "border": BORDER}

    def _redraw(self, _e=None) -> None:
        self.update_idletasks()
        w = self._fixed_width or max(self.winfo_width(), 120)
        h = max(self.winfo_height(), 38)
        colors = self._colors()
        self._bg_image = round_photo(
            self, w, h, self._radius, colors["bg"], colors["border"], outline_width=1
        )
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")

        self.coords(self._window, w / 2, h / 2)
        self.itemconfigure(self._window, width=w - 4, height=h - 4)
        self.inner.configure(bg=colors["bg"])
        self.entry.configure(bg=colors["bg"])
        if self.clear_btn is not None:
            self.clear_btn.configure(bg=colors["bg"])

    def _on_enter(self, _e=None) -> None:
        self._hover = True
        self._redraw()

    def _on_leave(self, _e=None) -> None:
        x, y = self.winfo_pointerxy()
        widget = self.winfo_containing(x, y)
        if widget is not None and str(widget).startswith(str(self)):
            return
        self._hover = False
        self._redraw()

    def _on_focus_in(self, _e=None) -> None:
        self._focused = True
        self._redraw()

    def _on_focus_out(self, _e=None) -> None:
        self._focused = False
        self._redraw()

    def bind(self, sequence=None, func=None, add=None):  # noqa: A003
        if sequence in ("<Return>", "<Key>", "<KeyRelease>"):
            return self.entry.bind(sequence, func, add)
        return super().bind(sequence, func, add)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str) -> None:
        self.textvariable.set(value)


# ── Modern Checkbox / Switch ──────────────────────────────────────────────────
class ModernCheckbutton(tk.Canvas):
    """Pill-styled hover checkbox component with rounded box & sharp checkmark."""

    def __init__(
        self,
        master,
        *,
        text: str,
        variable: tk.BooleanVar | None = None,
        command: Callable | None = None,
        radius: int = 6,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(
            master, highlightthickness=0, bd=0, bg=parent_bg, cursor="hand2", **kwargs
        )
        self.text = text
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command
        self.radius = radius
        self.parent_bg = parent_bg
        self._hover = False
        self._box_image: tk.PhotoImage | None = None

        root = self.winfo_toplevel()
        self._check_icon = photo("check", 12, "#FFFFFF", master=root)

        self.inner = tk.Frame(self, bg=parent_bg, cursor="hand2", padx=6, pady=4)
        self.box = tk.Canvas(
            self.inner, width=20, height=20, highlightthickness=0, bd=0, bg=parent_bg, cursor="hand2"
        )
        self.box.pack(side=tk.LEFT, padx=(0, 8))

        self.label = tk.Label(
            self.inner,
            text=text,
            bg=parent_bg,
            fg="#1E293B",
            font=("Helvetica Neue", 12),
            bd=0,
            cursor="hand2",
        )
        self.label.pack(side=tk.LEFT)

        self._window = self.create_window(0, 0, window=self.inner, anchor="w")
        self.bind("<Configure>", self._redraw)

        for w in (self, self.inner, self.box, self.label):
            w.bind("<Button-1>", self._toggle)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        self.variable.trace_add("write", lambda *_args: self._redraw())
        self.after_idle(self._fit)

    def _fit(self) -> None:
        self.inner.update_idletasks()
        w = self.inner.winfo_reqwidth() + 12
        h = max(32, self.inner.winfo_reqheight() + 4)
        self.configure(width=w, height=h)
        self._redraw()

    def _redraw(self, _e=None) -> None:
        self.update_idletasks()
        checked = self.variable.get()
        bg_color = "#F1F5F9" if self._hover else self.parent_bg

        self.inner.configure(bg=bg_color)
        self.box.configure(bg=bg_color)
        self.label.configure(bg=bg_color)

        fill = ACCENT if checked else SURFACE
        border = ACCENT if checked else ("#0D9488" if self._hover else "#CBD5E1")

        self._box_image = round_photo(self.box, 20, 20, self.radius, fill, border, outline_width=1)
        self.box.delete("all")
        self.box.create_image(0, 0, image=self._box_image, anchor="nw")
        if checked:
            self.box.create_image(10, 10, image=self._check_icon, anchor="center")

        h = max(self.winfo_height(), 32)
        self.coords(self._window, 2, h / 2)

    def _toggle(self, _e=None) -> None:
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()

    def _on_enter(self, _e=None) -> None:
        self._hover = True
        self._redraw()

    def _on_leave(self, _e=None) -> None:
        x, y = self.winfo_pointerxy()
        widget = self.winfo_containing(x, y)
        if widget is not None and str(widget).startswith(str(self)):
            return
        self._hover = False
        self._redraw()
