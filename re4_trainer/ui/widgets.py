"""Reusable small widgets for the trainer UI."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from .theme import (
    COLORS,
    FONT_BODY,
    FONT_GLYPH,
    FONT_GLYPH_BIG,
    FONT_GLYPH_NAV,
    FONT_H2,
    FONT_NUM,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_TINY,
    RADIUS,
    RADIUS_SM,
)


class Card(ctk.CTkFrame):
    """A titled panel with a small accent mark, header and separator."""

    def __init__(self, master, title: str, subtitle: str = "", glyph: str = "", wrap: int = 760, **kwargs):
        kwargs.setdefault("fg_color", COLORS["panel"])
        kwargs.setdefault("corner_radius", RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_soft"])
        super().__init__(master, **kwargs)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(15, 4))
        if glyph:
            ctk.CTkLabel(
                header,
                text=glyph,
                font=FONT_GLYPH(),
                text_color=COLORS["accent"],
                fg_color=COLORS["bg_soft"],
                corner_radius=7,
                width=26,
                height=26,
            ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header, text=title, font=FONT_H2(), text_color=COLORS["text"]).pack(side="left")
        self.header_extra = ctk.CTkFrame(header, fg_color="transparent", width=1, height=1)
        self.header_extra.pack(side="right")

        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=FONT_SMALL(),
                text_color=COLORS["text_faint"],
                anchor="w",
                justify="left",
                wraplength=wrap,
            ).pack(fill="x", padx=18, pady=(0, 10))
        else:
            ctk.CTkFrame(self, fg_color="transparent", height=6).pack(fill="x")

        ctk.CTkFrame(self, fg_color=COLORS["border_soft"], height=1).pack(fill="x", padx=18)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=18, pady=(14, 16))


class StatTile(ctk.CTkFrame):
    """Big number + caption tile used on the overview row."""

    def __init__(self, master, caption: str, value: str = "-", color: str = COLORS["text_dim"],
                 glyph: str = "", **kwargs):
        kwargs.setdefault("fg_color", COLORS["panel"])
        kwargs.setdefault("corner_radius", RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_soft"])
        super().__init__(master, **kwargs)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(13, 0))
        if glyph:
            ctk.CTkLabel(top, text=glyph, font=FONT_GLYPH(), text_color=COLORS["text_faint"]).pack(
                side="right", padx=(6, 0)
            )
        ctk.CTkLabel(top, text=caption.upper(), font=FONT_TINY(), text_color=COLORS["text_faint"],
                     anchor="w").pack(side="left", fill="x", expand=True)

        self.value = ctk.CTkLabel(self, text=value, font=FONT_NUM(), text_color=color, anchor="w")
        self.value.pack(fill="x", padx=16, pady=(2, 14))

    def set(self, text: str, color: Optional[str] = None) -> None:
        self.value.configure(text=text, text_color=color or COLORS["text_dim"])


class Chip(ctk.CTkFrame):
    """Tiny rounded label used for skin tags."""

    def __init__(self, master, text: str, color: str = COLORS["text_faint"],
                 fill: str = COLORS["bg_soft"], glyph: str = "", **kwargs):
        kwargs.setdefault("fg_color", fill)
        kwargs.setdefault("corner_radius", 999)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COLORS["border_soft"])
        super().__init__(master, **kwargs)
        label = f"{glyph} {text}" if glyph else text
        ctk.CTkLabel(self, text=label, font=FONT_TINY(), text_color=color).pack(padx=9, pady=2)


class StatusPill(ctk.CTkFrame):
    """Rounded dot + text used for the game connection status."""

    def __init__(self, master, text: str = "Checking...", color: str = COLORS["text_dim"]):
        super().__init__(
            master,
            fg_color=COLORS["panel_alt"],
            corner_radius=999,
            border_width=1,
            border_color=COLORS["border_soft"],
        )
        self.dot = ctk.CTkLabel(self, text="●", font=FONT_SMALL(), text_color=color)
        self.dot.pack(side="left", padx=(13, 7), pady=6)
        self.label = ctk.CTkLabel(self, text=text, font=FONT_SMALL(), text_color=COLORS["text_dim"])
        self.label.pack(side="left", padx=(0, 14), pady=6)

    def set(self, text: str, color: str) -> None:
        self.dot.configure(text_color=color)
        self.label.configure(text=text)


class InfoRow(ctk.CTkFrame):
    """Left label + right value line."""

    def __init__(self, master, label: str, value: str = "-", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        ctk.CTkLabel(
            self, text=label, font=FONT_SMALL(), text_color=COLORS["text_faint"], anchor="w", width=96
        ).pack(side="left")
        self.value = ctk.CTkLabel(
            self, text=value, font=FONT_BODY(), text_color=COLORS["text_dim"], anchor="e", justify="right"
        )
        self.value.pack(side="right", fill="x", expand=True)

    def set(self, value: str, color: Optional[str] = None) -> None:
        self.value.configure(text=value, text_color=color or COLORS["text_dim"])


class NavButton(ctk.CTkFrame):
    """Sidebar navigation entry: glyph + label, with a left accent bar when active."""

    def __init__(self, master, label: str, glyph: str, command, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", RADIUS_SM)
        super().__init__(master, **kwargs)
        self._command = command
        self._active = False

        self.bar = ctk.CTkFrame(self, fg_color="transparent", width=3, height=22, corner_radius=2)
        self.bar.pack(side="left", padx=(6, 0))
        self.icon = ctk.CTkLabel(self, text=glyph, font=FONT_GLYPH_NAV(),
                                 text_color=COLORS["text_faint"], width=22)
        self.icon.pack(side="left", padx=(8, 4), pady=9)
        self.label = ctk.CTkLabel(self, text=label, font=FONT_BODY(), text_color=COLORS["text_dim"], anchor="w")
        self.label.pack(side="left", fill="x", expand=True, padx=(2, 10))

        for widget in (self, self.icon, self.label, self.bar):
            widget.bind("<Button-1>", lambda _e: self._command())
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event=None) -> None:
        if not self._active:
            self.configure(fg_color=COLORS["panel_hover"])

    def _on_leave(self, _event=None) -> None:
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(fg_color=COLORS["nav_active"] if active else "transparent")
        self.bar.configure(fg_color=COLORS["accent"] if active else "transparent")
        self.label.configure(text_color=COLORS["text"] if active else COLORS["text_dim"])
        self.icon.configure(text_color=COLORS["accent"] if active else COLORS["text_faint"])


class Divider(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COLORS["border_soft"])
        kwargs.setdefault("height", 1)
        super().__init__(master, **kwargs)


def primary_button(master, text: str, command, **kwargs):
    options = dict(
        height=36,
        corner_radius=10,
        font=FONT_SMALL_BOLD(),
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        text_color="#FFFFFF",
        border_width=1,
        border_color=COLORS["accent_border"],
        command=command,
    )
    options.update(kwargs)
    return ctk.CTkButton(master, text=text, **options)


def ghost_button(master, text: str, command, **kwargs):
    options = dict(
        height=36,
        corner_radius=10,
        font=FONT_SMALL(),
        fg_color=COLORS["panel_alt"],
        hover_color=COLORS["panel_hover"],
        text_color=COLORS["text_dim"],
        border_width=1,
        border_color=COLORS["border"],
        command=command,
    )
    options.update(kwargs)
    return ctk.CTkButton(master, text=text, **options)


def danger_button(master, text: str, command, **kwargs):
    options = dict(
        height=36,
        corner_radius=10,
        font=FONT_SMALL(),
        fg_color=COLORS["panel_alt"],
        hover_color=COLORS["red"],
        text_color=COLORS["red"],
        border_width=1,
        border_color=COLORS["border"],
        command=command,
    )
    options.update(kwargs)
    return ctk.CTkButton(master, text=text, **options)


class Toast(ctk.CTkFrame):
    """Smooth notification that slides in at the top-right and slides away again."""

    _open_toasts: int = 0

    def __init__(self, master, text: str, color: str = COLORS["green"], icon: str = "\uE73E",
                 duration: int = 2600):
        super().__init__(master, fg_color=COLORS["panel_alt"], corner_radius=RADIUS_SM,
                         border_width=1, border_color=color)
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(padx=14, pady=9)
        ctk.CTkLabel(inner, text=icon, font=FONT_GLYPH(), text_color=color).pack(side="left", padx=(0, 9))
        ctk.CTkLabel(inner, text=text, font=FONT_SMALL(), text_color=COLORS["text"]).pack(side="left")

        self._slot = Toast._open_toasts
        Toast._open_toasts += 1
        self._target_y = 16 + self._slot * 54
        self._y = 0
        self.place(relx=1.0, x=-20, y=0, anchor="ne")
        self.after(10, self._slide_in)
        self.after(duration, self._slide_out)

    def _slide_in(self) -> None:
        if not self.winfo_exists():
            return
        self._y = min(self._y + 12, self._target_y)
        self.place_configure(y=self._y)
        if self._y < self._target_y:
            self.after(12, self._slide_in)

    def _slide_out(self) -> None:
        if not self.winfo_exists():
            return
        self._y -= 10
        self.place_configure(y=self._y)
        if self._y > -80 - self._slot * 54:
            self.after(12, self._slide_out)
        else:
            self._release()

    def _release(self) -> None:
        Toast._open_toasts = max(0, Toast._open_toasts - 1)
        self.destroy()


def toast(master, text: str, color: str = COLORS["green"], icon: str = "\uE73E",
          duration: int = 2600) -> Toast:
    return Toast(master, text, color=color, icon=icon, duration=duration)

