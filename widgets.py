"""Modern rounded buttons, selects, and inputs for the Tk UI."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Callable, Sequence

import tkinter as tk
from PIL import Image, ImageDraw

from icons import ACCENT, DANGER, INK, MUTED, photo

SURFACE = "#FFFFFF"
BORDER = "#D8DEE6"
HOVER = "#F1F5F9"
TEXT = "#1A2332"
PRIMARY_HOVER = "#0F766E"
PRIMARY_DISABLED = "#99D5CF"
DANGER_BG = "#FFF1F2"
DANGER_BORDER = "#FECDD3"
DANGER_HOVER = "#FFE4E6"
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
    outline_width: int = 2,
) -> bytes:
    scale = 3
    w, h, r, ow = width * scale, height * scale, radius * scale, max(1, outline_width * scale)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=_rgb(outline) + (255,))
    inset = ow
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
    outline_width: int = 2,
) -> tk.PhotoImage:
    return tk.PhotoImage(
        master=master,
        data=_round_png(max(8, width), max(8, height), radius, fill, outline, outline_width),
    )


class ModernButton(tk.Canvas):
    """Soft rounded button with icon and hover (OS default cursor)."""

    def __init__(
        self,
        master,
        *,
        text: str,
        command: Callable | None = None,
        icon: tk.PhotoImage | None = None,
        variant: str = "ghost",
        padx: int = 18,
        pady: int = 8,
        radius: int = 12,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(master, highlightthickness=0, bd=0, bg=parent_bg, **kwargs)
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
        self._bg_image: tk.PhotoImage | None = None

        self.content = tk.Frame(self, bg=self._palette()["bg"])
        if icon is not None:
            self.icon_lbl = tk.Label(self.content, image=icon, bg=self._palette()["bg"], bd=0)
            self.icon_lbl.pack(side=tk.LEFT, padx=(0, 8))
        else:
            self.icon_lbl = None
        self.text_lbl = tk.Label(
            self.content,
            text=text,
            bg=self._palette()["bg"],
            fg=self._palette()["fg"],
            font=("Helvetica Neue", 12, "bold" if variant == "primary" else "normal"),
            bd=0,
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
        widget.bind("<Button-1>", self._on_click)

    def _palette(self) -> dict[str, str]:
        disabled = not self._enabled
        hover = self._hover and self._enabled
        if self.variant == "primary":
            if disabled:
                return {"bg": PRIMARY_DISABLED, "fg": "#ECFEFF", "border": PRIMARY_DISABLED}
            if hover:
                return {"bg": PRIMARY_HOVER, "fg": "#FFFFFF", "border": PRIMARY_HOVER}
            return {"bg": ACCENT, "fg": "#FFFFFF", "border": ACCENT}
        if self.variant == "danger":
            if disabled:
                return {"bg": SURFACE, "fg": "#FCA5A5", "border": "#FECACA"}
            if hover:
                return {"bg": DANGER_HOVER, "fg": DANGER, "border": DANGER_BORDER}
            return {"bg": DANGER_BG, "fg": DANGER, "border": DANGER_BORDER}
        if disabled:
            return {"bg": "#F8FAFC", "fg": "#94A3B8", "border": BORDER}
        if hover:
            return {"bg": HOVER, "fg": TEXT, "border": "#CBD5E1"}
        return {"bg": SURFACE, "fg": TEXT, "border": BORDER}

    def _fit(self) -> None:
        self.content.update_idletasks()
        w = self.content.winfo_reqwidth() + self._padx * 2
        h = self.content.winfo_reqheight() + self._pady * 2
        self.configure(width=w, height=h)
        self._redraw()

    def _redraw(self, _e=None) -> None:
        self.update_idletasks()
        w = max(self.winfo_width(), 40)
        h = max(self.winfo_height(), 32)
        colors = self._palette()
        self._bg_image = round_photo(
            self, w, h, self._radius, colors["bg"], colors["border"], outline_width=2
        )
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")
        self.coords(self._window, w / 2, h / 2)
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
        self._redraw()

    def _on_click(self, _e=None) -> None:
        if self._enabled and self.command:
            self.command()

    def configure(self, cnf=None, **kwargs):  # noqa: A003
        if cnf:
            kwargs = {**cnf, **kwargs}
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._enabled = state not in (tk.DISABLED, "disabled")
            self._hover = False
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


class ModernSelect(tk.Canvas):
    """Rounded select with leading icon in trigger + options (OS default cursor)."""

    _open_menu: ModernSelect | None = None

    def __init__(
        self,
        master,
        *,
        values: Sequence[str],
        variable: tk.StringVar | None = None,
        width: int = 11,
        command: Callable | None = None,
        icon: tk.PhotoImage | None = None,
        radius: int = 12,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(master, highlightthickness=0, bd=0, bg=parent_bg, **kwargs)
        self.values = list(values)
        self.variable = variable or tk.StringVar(value=self.values[0] if self.values else "")
        self.command = command
        self._enabled = True
        self._popup: tk.Toplevel | None = None
        self._radius = radius
        self._parent_bg = parent_bg
        self._hover = False
        self._bg_image: tk.PhotoImage | None = None
        self._popup_bg: tk.PhotoImage | None = None
        self._leading_icon = icon

        root = self.winfo_toplevel()
        self._chevron = photo("chevron", 12, MUTED, master=root)
        self._check = photo("check", 12, ACCENT, master=root)

        self.inner = tk.Frame(self, bg=SURFACE)
        if icon is not None:
            self.leading_lbl = tk.Label(self.inner, image=icon, bg=SURFACE, bd=0)
            self.leading_lbl.pack(side=tk.LEFT, padx=(10, 4))
        else:
            self.leading_lbl = None

        self.value_lbl = tk.Label(
            self.inner,
            textvariable=self.variable,
            bg=SURFACE,
            fg=TEXT,
            font=("Helvetica Neue", 12),
            anchor="w",
            width=width,
            padx=4,
            pady=0,
        )
        self.value_lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.chevron_lbl = tk.Label(self.inner, image=self._chevron, bg=SURFACE, padx=8)
        self.chevron_lbl.pack(side=tk.RIGHT)

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
        w = self.inner.winfo_reqwidth() + 16
        h = max(34, self.inner.winfo_reqheight() + 10)
        self.configure(width=w, height=h)
        self._redraw()

    def _colors(self) -> dict[str, str]:
        if not self._enabled:
            return {"bg": "#F8FAFC", "fg": "#94A3B8", "border": BORDER}
        if self._popup or self._hover:
            return {"bg": HOVER, "fg": TEXT, "border": ACCENT}
        return {"bg": SURFACE, "fg": TEXT, "border": BORDER}

    def _redraw(self, _e=None) -> None:
        self.update_idletasks()
        w = max(self.winfo_width(), 80)
        h = max(self.winfo_height(), 34)
        colors = self._colors()
        self._bg_image = round_photo(
            self, w, h, self._radius, colors["bg"], colors["border"], outline_width=2
        )
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")
        self.coords(self._window, w / 2, h / 2)
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
        y = self.winfo_rooty() + self.winfo_height() + 6
        width = max(self.winfo_width(), 160)
        row_h = 36
        height = min(len(self.values) * row_h + 14, 300)

        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=self._parent_bg)

        canvas = tk.Canvas(
            popup, width=width, height=height, highlightthickness=0, bd=0, bg=self._parent_bg
        )
        canvas.pack(fill=tk.BOTH, expand=True)
        self._popup_bg = round_photo(popup, width, height, 14, SURFACE, BORDER, outline_width=2)
        canvas.create_image(0, 0, image=self._popup_bg, anchor="nw")

        menu = tk.Frame(canvas, bg=SURFACE)
        canvas.create_window(8, 8, window=menu, anchor="nw", width=width - 16)

        current = self.variable.get()
        for value in self.values:
            selected = value == current
            row = tk.Frame(menu, bg="#F0FDFA" if selected else SURFACE)
            row.pack(fill=tk.X, pady=1)

            if self._leading_icon is not None:
                ic = tk.Label(
                    row,
                    image=self._leading_icon,
                    bg=row["bg"],
                    bd=0,
                    padx=8,
                )
                ic.pack(side=tk.LEFT, padx=(4, 0))
            else:
                ic = None

            lbl = tk.Label(
                row,
                text=value,
                bg=row["bg"],
                fg=ACCENT if selected else TEXT,
                font=("Helvetica Neue", 12, "bold" if selected else "normal"),
                anchor="w",
                padx=8,
                pady=7,
            )
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            mark = tk.Label(
                row,
                image=self._check if selected else "",
                bg=row["bg"],
                width=16,
                padx=8,
            )
            mark.pack(side=tk.RIGHT)

            def _enter(e, r=row, l=lbl, m=mark, i=ic, sel=selected):  # noqa: E741
                bg = "#CCFBF1" if sel else HOVER
                r.configure(bg=bg)
                l.configure(bg=bg)
                m.configure(bg=bg)
                if i is not None:
                    i.configure(bg=bg)

            def _leave(e, r=row, l=lbl, m=mark, i=ic, sel=selected):  # noqa: E741
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


class ModernEntry(tk.Canvas):
    """Rounded text field. Use fixed_width for compact fields (Start/End)."""

    def __init__(
        self,
        master,
        *,
        textvariable: tk.StringVar | None = None,
        font=("Helvetica Neue", 13),
        radius: int = 12,
        show: str | None = None,
        width: int | None = None,
        fixed_width: int | None = None,
        **kwargs,
    ):
        parent_bg = kwargs.pop("bg", None) or _parent_bg(master)
        super().__init__(master, highlightthickness=0, bd=0, bg=parent_bg, **kwargs)
        self._radius = radius
        self._parent_bg = parent_bg
        self._focused = False
        self._hover = False
        self._fixed_width = fixed_width
        self._bg_image: tk.PhotoImage | None = None

        self.inner = tk.Frame(self, bg=SURFACE)
        entry_kw: dict = {
            "textvariable": textvariable,
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
        self.entry.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=6)

        self._window = self.create_window(0, 0, window=self.inner, anchor="center")
        self.bind("<Configure>", self._redraw)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        for w in (self, self.inner, self.entry):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if fixed_width:
            self.configure(width=fixed_width, height=34)
        self.after_idle(self._fit)

    def _fit(self) -> None:
        self.inner.update_idletasks()
        h = 34
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
        if self._fixed_width:
            w = self._fixed_width
        else:
            w = max(self.winfo_width(), 120)
        h = max(self.winfo_height(), 34)
        colors = self._colors()
        self._bg_image = round_photo(
            self, w, h, self._radius, colors["bg"], colors["border"], outline_width=2
        )
        self.delete("bg")
        self.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")
        self.tag_lower("bg")
        self.coords(self._window, w / 2, h / 2)
        # Keep inner content sized to the rounded area
        self.itemconfigure(self._window, width=w - 4, height=h - 4)
        self.inner.configure(bg=colors["bg"])
        self.entry.configure(bg=colors["bg"])

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
