"""Custom in-app dialogs (dark, styled) instead of the default Windows message boxes."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import customtkinter as ctk

from .theme import COLORS, FONT_BODY, FONT_BODY_BOLD, FONT_GLYPH_BIG, FONT_H2, ICONS, RADIUS

_KIND_STYLE = {
    "question": (COLORS["accent"], ICONS["info"]),
    "info": (COLORS["blue"], ICONS["info"]),
    "warning": (COLORS["amber"], ICONS["warning"]),
    "error": (COLORS["red"], ICONS["error"]),
}


class AppDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        title: str,
        message: str,
        kind: str = "info",
        yes_text: str = "OK",
        no_text: Optional[str] = None,
        buttons: Optional[Sequence[Tuple[str, object]]] = None,
    ):
        super().__init__(master)
        self.result: object = False
        self._choice: object = False
        if buttons:
            # [(label, value), ...] - the first entry is the primary (accent) button
            self._buttons: List[Tuple[str, object]] = list(buttons)
        else:
            self._buttons = [(yes_text, True)]
            if no_text is not None:
                self._buttons.append((no_text, False))
        accent, glyph = _KIND_STYLE.get(kind, _KIND_STYLE["info"])

        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.transient(master)

        card = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=RADIUS, border_width=1,
                            border_color=COLORS["border"])
        card.pack(fill="both", expand=True, padx=14, pady=14)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 6))
        ctk.CTkLabel(
            header,
            text=glyph,
            font=FONT_GLYPH_BIG(),
            text_color=accent,
            fg_color=COLORS["bg_soft"],
            corner_radius=8,
            width=32,
            height=32,
        ).pack(side="left", padx=(0, 11))
        ctk.CTkLabel(header, text=title, font=FONT_H2(), text_color=COLORS["text"], anchor="w").pack(
            side="left", fill="x", expand=True
        )

        ctk.CTkFrame(card, fg_color=COLORS["border_soft"], height=1).pack(fill="x", padx=18, pady=(4, 0))

        ctk.CTkLabel(
            card,
            text=message,
            font=FONT_BODY(),
            text_color=COLORS["text_dim"],
            wraplength=430,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=18, pady=(14, 4))

        buttons_box = ctk.CTkFrame(card, fg_color="transparent")
        buttons_box.pack(fill="x", padx=18, pady=(12, 16))
        # packed right-to-left, so the primary button ends up on the far right
        for index, (label, value) in enumerate(self._buttons):
            primary = index == 0
            options = dict(
                width=max(110, min(215, 8 * len(label) + 30)),
                height=34,
                corner_radius=10,
                font=FONT_BODY_BOLD() if primary else FONT_BODY(),
                fg_color=COLORS["accent"] if primary else COLORS["panel_alt"],
                hover_color=COLORS["accent_hover"] if primary else COLORS["panel_hover"],
                border_width=1,
                border_color=COLORS["accent_border"] if primary else COLORS["border"],
                command=lambda v=value: self._done(v),
            )
            if not primary:
                options["text_color"] = COLORS["text_dim"]
            ctk.CTkButton(buttons_box, text=label, **options).pack(
                side="right", padx=(8, 0) if index else 0
            )

        values = [v for _label, v in self._buttons]
        escape_value = None if None in values else values[-1]
        self.bind("<Escape>", lambda _e: self._done(escape_value))
        self.bind("<Return>", lambda _e: self._done(self._buttons[0][1]))

        self.update_idletasks()
        self._center_on(master)
        self.grab_set()
        self.after(60, self.focus_force)

    def _center_on(self, master) -> None:
        try:
            self.update_idletasks()
            width = max(380, self.winfo_reqwidth())
            height = self.winfo_reqheight()
            master.update_idletasks()
            x = master.winfo_rootx() + (master.winfo_width() - width) // 2
            y = master.winfo_rooty() + (master.winfo_height() - height) // 2
            self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _done(self, value: object) -> None:
        self._choice = value
        self.result = value
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def wait(self) -> object:
        try:
            self.master.wait_window(self)
        except Exception:
            pass
        return self._choice


def ask_yes_no(master, title: str, message: str, yes: str = "Yes", no: str = "No") -> bool:
    dialog = AppDialog(master, title, message, kind="question", yes_text=yes, no_text=no)
    return bool(dialog.wait())


def ask_choice(
    master,
    title: str,
    message: str,
    choices: Sequence[Tuple[str, object]],
    cancel: str = "Cancel",
) -> object:
    """Dialog with a custom set of buttons.

    `choices` is a list of (label, value); the first label is the highlighted
    primary action. A "Cancel" button (value None) is added automatically, and
    Escape maps to Cancel as well. Returns the chosen value (None if cancelled).
    """
    buttons: List[Tuple[str, object]] = list(choices)
    buttons.append((cancel, None))
    dialog = AppDialog(master, title, message, kind="question", buttons=buttons)
    return dialog.wait()


def show_info(master, title: str, message: str, ok: str = "OK") -> None:
    AppDialog(master, title, message, kind="info", yes_text=ok).wait()


def show_warning(master, title: str, message: str, ok: str = "OK") -> None:
    AppDialog(master, title, message, kind="warning", yes_text=ok).wait()


def show_error(master, title: str, message: str, ok: str = "OK") -> None:
    AppDialog(master, title, message, kind="error", yes_text=ok).wait()


class _TextDialog(ctk.CTkToplevel):
    """Small single-line input dialog (name / rename)."""

    def __init__(self, master, title: str, message: str, initial: str = "", ok: str = "Save"):
        super().__init__(master)
        self.result: Optional[str] = None
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])
        self.transient(master)

        card = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=RADIUS, border_width=1,
                            border_color=COLORS["border"])
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text=message, font=FONT_BODY(), text_color=COLORS["text_dim"], anchor="w",
                     justify="left", wraplength=380).pack(fill="x", padx=18, pady=(18, 8))
        self.entry = ctk.CTkEntry(card, height=36, corner_radius=10, font=FONT_BODY(),
                                  fg_color=COLORS["bg_soft"], border_color=COLORS["border"])
        self.entry.pack(fill="x", padx=18)
        self.entry.insert(0, initial)
        self.entry.select_range(0, "end")

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=(14, 18))
        ctk.CTkButton(buttons, text=ok, width=110, height=34, corner_radius=10, font=FONT_BODY_BOLD(),
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], border_width=1,
                      border_color=COLORS["accent_border"], command=self._accept).pack(side="right")
        ctk.CTkButton(buttons, text="Cancel", width=100, height=34, corner_radius=10, font=FONT_BODY(),
                      fg_color=COLORS["panel_alt"], hover_color=COLORS["panel_hover"],
                      text_color=COLORS["text_dim"], border_width=1, border_color=COLORS["border"],
                      command=self._cancel).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _e: self._accept())
        self.bind("<Escape>", lambda _e: self._cancel())
        self.update_idletasks()
        try:
            width = max(420, self.winfo_reqwidth())
            height = self.winfo_reqheight()
            x = master.winfo_rootx() + (master.winfo_width() - width) // 2
            y = master.winfo_rooty() + (master.winfo_height() - height) // 2
            self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass
        self.grab_set()
        self.after(60, self._focus)

    def _focus(self) -> None:
        try:
            self.entry.focus_force()
        except Exception:
            pass

    def _accept(self) -> None:
        value = self.entry.get().strip()
        self.result = value or None
        self._close()

    def _cancel(self) -> None:
        self.result = None
        self._close()

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def wait(self) -> Optional[str]:
        try:
            self.master.wait_window(self)
        except Exception:
            pass
        return self.result


def ask_text(master, title: str, message: str, initial: str = "", ok: str = "Save") -> Optional[str]:
    dialog = _TextDialog(master, title, message, initial=initial, ok=ok)
    return dialog.wait()
