"""Main trainer window."""

from __future__ import annotations

import re
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from .. import APP_NAME
from ..config import ConfigStore
from ..core.gamepaths import discover
from ..core.process import (
    close_game_processes,
    find_game_exe_path,
    find_game_processes,
    launch_game,
)
from ..core.winapi import elevate
from ..features.checkpoint import CheckpointManager
from ..features.skins import (
    LEON_OUTFITS,
    OUTFIT_MODE_LABELS,
    OUTFIT_MODES,
    SkinManager,
    model_index,
    pack_index,
)
from ..features.skipdeath import SkipDeathEngine
from . import dialogs
from .skin_dialog import AddSkinDialog
from .theme import (
    COLORS,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_GLYPH,
    FONT_H1,
    FONT_H2,
    FONT_MONO,
    FONT_NUM,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_TINY,
    GAP,
    ICONS,
    PALETTE_LABELS,
    RADIUS,
    RADIUS_SM,
    WINDOW_TITLE,
    apply_palette,
    apply_theme,
)
from .widgets import (
    Card,
    Chip,
    NavButton,
    StatTile,
    StatusPill,
    danger_button,
    ghost_button,
    primary_button,
    toast,
)

LOG_LIMIT = 250


class TrainerWindow(ctk.CTk):
    def __init__(self, config: ConfigStore, admin: bool):
        apply_theme()
        apply_palette(config.settings.palette)
        super().__init__()

        self.config_store = config
        self.settings = config.settings
        self.admin = admin

        self.paths = discover(self.settings.game_dir, self.settings.save_dir)
        if self.paths.game_dir:
            self.settings.game_dir = str(self.paths.game_dir)
        if self.paths.save_dir:
            self.settings.save_dir = str(self.paths.save_dir)
        self.config_store.save()

        self.skins = SkinManager(config, self.game_dir, self.log, legacy_install_dir=self.paths.game_dir)
        self.checkpoint = CheckpointManager(config, self.log)
        self.engine = SkipDeathEngine(self.log)
        self.engine.set_continue_key(self.settings.continue_key)
        self.engine.start()

        self.selected_skin: str = self.settings.selected_skin
        self._game_running = False
        self._skin_signature = None
        self._checkpoint_signature = None
        self._log_lines = 0
        self._active_page = "overview"
        self._page_frames = {}
        self._nav_buttons = {}
        self._pulse_on = False
        self._hp_shown = 0.0
        self._hp_target = 0.0
        self._hp_anim_running = False

        self.title(WINDOW_TITLE)
        self.geometry(self.settings.window_geometry or "1220x820")
        self.minsize(1080, 760)
        self.configure(fg_color=COLORS["bg"])
        self._set_window_icon()

        self._build()
        self.engine.set_enabled(bool(self.settings.skip_death))
        self.engine.set_protection(bool(self.settings.protection))
        self.engine.set_yes_position(self.settings.yes_click_x, self.settings.yes_click_y)
        self._refresh_skins()
        self.log("info", f"Trainer started ({'administrator' if admin else 'standard user'}).")
        self.log("info", "MADE BY ABO 3MAD DULE server")
        self.after(250, self._tick)

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _asset_path(name: str) -> Optional[Path]:
        """Find a bundled asset (works both from source and from the frozen exe)."""
        roots = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        roots.append(Path(__file__).resolve().parents[2])
        for root in roots:
            candidate = root / "packaging" / name
            if candidate.is_file():
                return candidate
        return None

    def _load_avatar(self):
        try:
            from PIL import Image

            path = self._asset_path("dule_brand.png") or self._asset_path("dule_avatar.png")
            if path:
                image = Image.open(path).copy()
                return ctk.CTkImage(light_image=image, dark_image=image, size=(46, 46))
        except Exception:
            return None
        return None

    def _load_steam_avatar(self):
        try:
            from PIL import Image, ImageDraw

            path = self._asset_path("steam_avatar.png")
            if not path:
                return None
            image = Image.open(path).convert("RGBA")
            side = min(image.size)
            image = image.crop(
                (
                    (image.width - side) // 2,
                    (image.height - side) // 2,
                    (image.width + side) // 2,
                    (image.height + side) // 2,
                )
            )
            image = image.resize((96, 96), Image.LANCZOS)
            mask = Image.new("L", (96, 96), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 95, 95), fill=255)
            rounded = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
            rounded.paste(image, (0, 0), mask)
            return ctk.CTkImage(light_image=rounded, dark_image=rounded, size=(44, 44))
        except Exception:
            return None

    def _set_window_icon(self) -> None:
        try:
            path = self._asset_path("icon.ico")
            if path:
                self.iconbitmap(str(path))
        except Exception:
            pass

    def game_dir(self) -> Optional[Path]:
        if self.settings.game_dir:
            candidate = Path(self.settings.game_dir)
            if candidate.is_dir():
                return candidate
        return self.paths.game_dir

    def post(self, fn: Callable[[], None]) -> None:
        try:
            self.after(0, fn)
        except (RuntimeError, tk.TclError):
            pass

    def log(self, level: str, message: str) -> None:
        self.post(lambda: self._append_log(level, message))

    def _append_log(self, level: str, message: str) -> None:
        from datetime import datetime

        stamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "i", "warn": "!", "error": "x"}.get(level, "-")
        line = f"[{stamp}] {prefix} {message}\n"
        # keep a file log so problems can be checked later
        try:
            log_file = self.config_store.logs_dir / "trainer.log"
            with open(log_file, "a", encoding="utf-8") as handle:
                handle.write(f"{datetime.now().strftime('%Y-%m-%d ')}{line}")
        except OSError:
            pass
        if not hasattr(self, "log_box"):
            print(f"[{level}] {message}")
            return
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self._log_lines += 1
        if self._log_lines > LOG_LIMIT:
            self.log_box.delete("1.0", "2.0")
            self._log_lines -= 1
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _run_async(self, fn: Callable[[], object], on_done: Optional[Callable[[object], None]] = None) -> None:
        def worker() -> None:
            try:
                result = fn()
            except Exception as exc:  # surface to the UI
                self.post(lambda e=exc: self.error("Something went wrong", str(e)))
                return
            if on_done:
                self.post(lambda r=result: on_done(r))

        threading.Thread(target=worker, daemon=True).start()

    def _require_admin(self, action: str) -> bool:
        if self.admin:
            return True
        if self.confirm(
            "Administrator rights",
            f"{action} needs administrator rights because the game is installed "
            "under Program Files.\n\nRestart the trainer as administrator now?",
        ):
            self._relaunch_elevated()
        return False

    def _relaunch_elevated(self) -> None:
        if getattr(sys, "frozen", False):
            exe, params = sys.executable, ""
            workdir = str(Path(sys.executable).parent)
        else:
            exe, params = sys.executable, "-m re4_trainer"
            workdir = str(Path(__file__).resolve().parents[2])
        self.log("info", "Requesting administrator rights...")
        if elevate(exe, params, workdir):
            self.after(400, self._on_close)

    # ------------------------------------------------------------------ dialogs
    def confirm(self, title: str, message: str, yes: str = "Yes", no: str = "No") -> bool:
        return dialogs.ask_yes_no(self, title, message, yes=yes, no=no)

    def note(self, title: str, message: str) -> None:
        dialogs.show_info(self, title, message)

    def toast(self, message: str, kind: str = "ok") -> None:
        """Small non-blocking notification, smoother than a modal box."""
        colors = {"ok": COLORS["green"], "info": COLORS["blue"], "warn": COLORS["amber"],
                  "error": COLORS["red"]}
        icons = {"ok": ICONS["check"], "info": ICONS["info"], "warn": ICONS["warning"],
                 "error": ICONS["error"]}
        try:
            toast(self, message, color=colors.get(kind, COLORS["green"]),
                  icon=icons.get(kind, ICONS["check"]))
        except Exception:
            pass

    def warn(self, title: str, message: str) -> None:
        dialogs.show_warning(self, title, message)

    def error(self, title: str, message: str) -> None:
        dialogs.show_error(self, title, message)

    # ------------------------------------------------------------------- view
    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()
        self._show_page("overview")

    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=COLORS["panel"], corner_radius=0, width=228)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(20, 14))
        avatar = self._load_avatar()
        if avatar is not None:
            holder = ctk.CTkFrame(brand, fg_color=COLORS["bg_soft"], corner_radius=999,
                                  border_width=1, border_color=COLORS["border_soft"])
            holder.pack(side="left", padx=(0, 11))
            ctk.CTkLabel(holder, text="", image=avatar).pack(padx=3, pady=3)
        names = ctk.CTkFrame(brand, fg_color="transparent")
        names.pack(side="left")
        ctk.CTkLabel(names, text="D U L E", font=FONT_BODY_BOLD(), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(names, text="RE4 CLASSIC TRAINER", font=FONT_TINY(), text_color=COLORS["accent"]).pack(
            anchor="w", pady=(2, 0)
        )

        ctk.CTkFrame(bar, fg_color=COLORS["border_soft"], height=1).pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(bar, text="MENU", font=FONT_TINY(), text_color=COLORS["text_faint"], anchor="w").pack(
            fill="x", padx=22, pady=(0, 6)
        )
        for key, label, glyph in (
            ("overview", "Overview", ICONS["home"]),
            ("skins", "Leon Skins", ICONS["people"]),
            ("checkpoint", "Checkpoint", ICONS["save"]),
            ("gameplay", "Gameplay", ICONS["bolt"]),
        ):
            button = NavButton(bar, label, glyph, command=lambda k=key: self._show_page(k))
            button.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = button

        spacer = ctk.CTkFrame(bar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        footer = ctk.CTkFrame(bar, fg_color=COLORS["bg_soft"], corner_radius=RADIUS_SM)
        footer.pack(fill="x", padx=12, pady=(0, 14))
        ctk.CTkLabel(
            footer,
            text="MADE BY ABO 3MAD",
            font=FONT_SMALL_BOLD(),
            text_color=COLORS["accent"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(
            footer,
            text="DULE server  ·  v1.0\nSteam release (2005 / UHD)",
            font=FONT_TINY(),
            text_color=COLORS["text_faint"],
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 8))

        theme_row = ctk.CTkFrame(bar, fg_color="transparent")
        theme_row.pack(fill="x", padx=12, pady=(0, 14))
        ctk.CTkLabel(theme_row, text=ICONS["brush"], font=FONT_GLYPH(),
                     text_color=COLORS["text_faint"]).pack(side="left", padx=(2, 6))
        self._palette_label_to_key = {label: key for key, label in PALETTE_LABELS.items()}
        self.palette_var = ctk.StringVar(
            value=PALETTE_LABELS.get(self.settings.palette, PALETTE_LABELS["neon"])
        )
        self.palette_menu = ctk.CTkOptionMenu(
            theme_row,
            variable=self.palette_var,
            values=list(self._palette_label_to_key),
            command=self._on_palette,
            height=28,
            corner_radius=8,
            font=FONT_TINY(),
            dropdown_font=FONT_SMALL(),
            fg_color=COLORS["panel_alt"],
            button_color=COLORS["panel_hover"],
            button_hover_color=COLORS["panel_hover"],
            text_color=COLORS["text_dim"],
            dropdown_fg_color=COLORS["panel_alt"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["panel_hover"],
        )
        self.palette_menu.pack(side="left", fill="x", expand=True)

    def _build_content(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=1, sticky="nsew", padx=(22, 26), pady=(18, 18))
        container.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(container, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="DULE SERVER   ·   TRAINER", font=FONT_TINY(),
                     text_color=COLORS["accent"], anchor="w").pack(anchor="w", pady=(0, 2))
        self.page_title = ctk.CTkLabel(titles, text="Overview", font=FONT_H1(), text_color=COLORS["text"])
        self.page_title.pack(anchor="w")
        self.page_sub = ctk.CTkLabel(titles, text="", font=FONT_SMALL(), text_color=COLORS["text_faint"])
        self.page_sub.pack(anchor="w", pady=(1, 0))
        steam_avatar = self._load_steam_avatar()
        if steam_avatar is not None:
            holder = ctk.CTkFrame(head, fg_color=COLORS["panel_alt"], corner_radius=999,
                                  border_width=1, border_color=COLORS["border_soft"])
            holder.pack(side="right", padx=(12, 0), pady=2)
            ctk.CTkLabel(holder, text="", image=steam_avatar).pack(padx=2, pady=2)
        self.status_pill = StatusPill(head, "Searching for game...", COLORS["text_dim"])
        self.status_pill.pack(side="right")

        row = 1
        if not self.admin:
            banner = ctk.CTkFrame(
                container,
                fg_color=COLORS["amber_soft"],
                corner_radius=RADIUS,
                border_width=1,
                border_color=COLORS["amber_border"],
            )
            banner.grid(row=row, column=0, sticky="ew", pady=(0, 12))
            ctk.CTkLabel(
                banner,
                text=f"{ICONS["shield"]}  Standard user mode - applying skins and loading "
                     "checkpoints needs administrator rights.",
                font=FONT_SMALL(),
                text_color=COLORS["amber"],
            ).pack(side="left", padx=16, pady=9)
            ctk.CTkButton(
                banner,
                text="Restart as administrator",
                command=self._relaunch_elevated,
                fg_color=COLORS["amber_border"],
                hover_color="#7E6229",
                text_color="#FFFFFF",
                height=28,
                corner_radius=8,
                font=FONT_SMALL_BOLD(),
            ).pack(side="right", padx=10, pady=6)
            row += 1

        self.page_host = ctk.CTkFrame(container, fg_color="transparent")
        self.page_host.grid(row=row, column=0, sticky="nsew")
        # without these two lines a page only gets its natural width and the whole
        # window looks half empty
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(row, weight=1)

        for key in ("overview", "skins", "checkpoint", "gameplay"):
            frame = ctk.CTkFrame(self.page_host, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            self._page_frames[key] = frame

        self._build_overview_page(self._page_frames["overview"])
        self._build_skins_page(self._page_frames["skins"])
        self._build_checkpoint_page(self._page_frames["checkpoint"])
        self._build_gameplay_page(self._page_frames["gameplay"])

    def _show_page(self, key: str) -> None:
        self._active_page = key
        frame = self._page_frames.get(key)
        if frame is not None:
            frame.tkraise()
        titles = {
            "overview": ("Overview", "Game status, quick actions and live activity"),
            "skins": ("Leon Skins", "Import, apply and restore character skins"),
            "checkpoint": ("Last Checkpoint", "Snapshot and restore your save file"),
            "gameplay": ("Gameplay", "Instant respawn and optional damage protection"),
        }
        title, subtitle = titles.get(key, (key.title(), ""))
        self.page_title.configure(text=title)
        self.page_sub.configure(text=subtitle)
        for name, button in self._nav_buttons.items():
            button.set_active(name == key)
        if key == "skins":
            self._refresh_skins()

    def _stat_card(self, parent, column: int, caption: str, value: str, color: str, glyph: str = ""):
        tile = StatTile(parent, caption, value, color, glyph)
        tile.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else GAP, 0))
        parent.grid_columnconfigure(column, weight=1)
        return tile

    def _build_overview_page(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)

        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.grid(row=0, column=0, sticky="ew", pady=(0, GAP))
        self.ov_conn = self._stat_card(stats, 0, "Connection", "Searching...", COLORS["text_faint"],
                                       ICONS["dot"])
        self.ov_health = self._stat_card(stats, 1, "Health", "-", COLORS["text_dim"], ICONS["heart"])
        self.ov_deaths = self._stat_card(stats, 2, "Instant respawns", "0", COLORS["text_dim"], ICONS["bolt"])
        self.ov_handled = self._stat_card(stats, 3, "Deaths handled", "0", COLORS["text_dim"], ICONS["check"])

        quick = ctk.CTkFrame(parent, fg_color="transparent")
        quick.grid(row=1, column=0, sticky="ew", pady=(0, GAP))
        primary_button(quick, f"{ICONS["save"]}  Save Last Checkpoint", self._save_checkpoint).pack(side="left")
        ghost_button(quick, f"{ICONS["heart"]}  Heal Leon", self._heal_now).pack(side="left", padx=8)
        ghost_button(quick, f"{ICONS["people"]}  Open Skins", lambda: self._show_page("skins")).pack(side="left")

        path_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["panel"],
            corner_radius=RADIUS,
            border_width=1,
            border_color=COLORS["border_soft"],
        )
        path_card.grid(row=2, column=0, sticky="ew", pady=(0, GAP))
        ctk.CTkLabel(path_card, text=ICONS["folder"], font=FONT_GLYPH(),
                     text_color=COLORS["text_faint"]).pack(side="left", padx=(14, 8), pady=10)
        self.path_label = ctk.CTkLabel(
            path_card,
            text="Game folder: detecting...",
            font=FONT_SMALL(),
            text_color=COLORS["text_faint"],
            anchor="w",
        )
        self.path_label.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=10)
        ghost_button(path_card, "Browse", self._browse_game_dir, height=28,
                     corner_radius=8, width=76).pack(side="right", padx=(6, 12), pady=7)
        ghost_button(path_card, "Detect again", self._detect_paths, height=28,
                     corner_radius=8, width=104).pack(side="right", pady=7)

        activity = Card(parent, "Activity log", "Every action the trainer takes, newest at the bottom.",
                        glyph=ICONS["reload"])
        activity.grid(row=3, column=0, sticky="nsew")
        self.log_box = ctk.CTkTextbox(
            activity.body,
            fg_color=COLORS["bg_soft"],
            border_width=0,
            corner_radius=10,
            font=FONT_MONO(),
            wrap="word",
            text_color=COLORS["text_dim"],
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def _build_skins_page(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=RADIUS, border_width=1,
                           border_color=COLORS["border_soft"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, GAP))
        intro = ctk.CTkFrame(top, fg_color="transparent")
        intro.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        ctk.CTkLabel(intro, text="Leon skin library", font=FONT_H2(), text_color=COLORS["text"],
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(
            intro,
            text="Add a .lfs skin, select it, then Apply. The originals of the game copy you run "
                 "are backed up first, so Restore always brings them back.",
            font=FONT_SMALL(),
            text_color=COLORS["text_faint"],
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(anchor="w", pady=(2, 0))

        outfit_box = ctk.CTkFrame(top, fg_color="transparent")
        outfit_box.pack(side="right", padx=16, pady=12)
        ctk.CTkLabel(outfit_box, text="Change outfit", font=FONT_SMALL(),
                     text_color=COLORS["text_dim"]).pack(anchor="e")
        self._outfit_label_to_mode = {label: mode for mode, label in OUTFIT_MODE_LABELS.items()}
        mode = self.settings.skin_outfit_mode
        if mode not in OUTFIT_MODES:
            mode = "both"
        self.outfit_var = ctk.StringVar(value=OUTFIT_MODE_LABELS[mode])
        self.outfit_menu = ctk.CTkOptionMenu(
            outfit_box,
            variable=self.outfit_var,
            values=list(self._outfit_label_to_mode),
            command=self._on_outfit_mode,
            width=248,
            height=32,
            corner_radius=9,
            font=FONT_SMALL(),
            dropdown_font=FONT_SMALL(),
            fg_color=COLORS["panel_alt"],
            button_color=COLORS["panel_hover"],
            button_hover_color=COLORS["panel_hover"],
            text_color=COLORS["text_dim"],
            dropdown_fg_color=COLORS["panel_alt"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["panel_hover"],
        )
        self.outfit_menu.pack(anchor="e", pady=(5, 0))

        self.skin_list = ctk.CTkScrollableFrame(parent, fg_color=COLORS["panel"], corner_radius=RADIUS,
                                                border_width=1, border_color=COLORS["border_soft"])
        self.skin_list.grid(row=1, column=0, sticky="nsew")

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(GAP, 0))
        self.add_skin_btn = ghost_button(actions, f"+  Add skin", self._open_add_skin)
        self.add_skin_btn.pack(side="left")
        self.rename_skin_btn = ghost_button(actions, "Rename", self._rename_skin, width=92)
        self.rename_skin_btn.pack(side="left", padx=8)
        self.delete_skin_btn = danger_button(actions, f"{ICONS['delete']}  Delete", self._delete_skin, width=96)
        self.delete_skin_btn.pack(side="left")
        self.apply_skin_btn = primary_button(actions, f"{ICONS["check"]}  Apply Selected", self._apply_skin)
        self.apply_skin_btn.pack(side="right")
        self.restore_btn = ghost_button(actions, f"{ICONS["reload"]}  Restore Original", self._restore_original)
        self.restore_btn.pack(side="right", padx=8)

        self.skins_status = ctk.CTkLabel(parent, text="", font=FONT_SMALL(),
                                         text_color=COLORS["text_faint"], anchor="w", justify="left")
        self.skins_status.grid(row=3, column=0, sticky="ew", pady=(10, 0))

    def _build_checkpoint_page(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)

        card = Card(
            parent,
            "Last checkpoint",
            "A snapshot of your save file. Restoring always stores a safety copy of the current "
            "save first, so nothing is ever lost.",
            glyph=ICONS["save"],
        )
        card.grid(row=0, column=0, sticky="ew")
        body = card.body

        self.ck_status = ctk.CTkLabel(body, text="Checking...", font=FONT_H2(),
                                      text_color=COLORS["text_dim"], anchor="w")
        self.ck_status.pack(fill="x", pady=(0, 4))
        self.ck_hint = ctk.CTkLabel(body, text="", font=FONT_SMALL(), text_color=COLORS["text_faint"],
                                    anchor="w", wraplength=760, justify="left")
        self.ck_hint.pack(fill="x")

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(14, 0))
        self.ck_save_btn = primary_button(buttons, f"{ICONS["save"]}  Save Last Checkpoint", self._save_checkpoint)
        self.ck_save_btn.pack(side="left")
        self.ck_load_btn = ghost_button(buttons, f"{ICONS["reload"]}  Load Last Checkpoint", self._load_checkpoint)
        self.ck_load_btn.pack(side="left", padx=8)

        steps = Card(parent, "How it works", glyph=ICONS["dot"])
        steps.grid(row=1, column=0, sticky="ew", pady=(GAP, 0))
        for number, text in (
            ("1", "Save at a typewriter in-game."),
            ("2", "Press Save Last Checkpoint here."),
            ("3", "Play on. To go back later: close the game, press Load Last Checkpoint, then "
                  "start the game and choose Load Game."),
        ):
            line = ctk.CTkFrame(steps.body, fg_color="transparent")
            line.pack(fill="x", pady=3)
            ctk.CTkLabel(line, text=number, font=FONT_SMALL_BOLD(), text_color=COLORS["accent"],
                         fg_color=COLORS["bg_soft"], corner_radius=6, width=22).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(line, text=text, font=FONT_SMALL(), text_color=COLORS["text_dim"],
                         anchor="w", justify="left", wraplength=700).pack(side="left", fill="x", expand=True)

    def _build_gameplay_page(self, parent) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        respawn = Card(
            parent,
            "Instant respawn",
            "You take normal damage - the moment health would hit zero, Leon is revived on the "
            "spot. No death animation, no death screen.",
            glyph=ICONS["bolt"],
            wrap=380,
        )
        respawn.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2))
        body = respawn.body
        self.skip_var = tk.BooleanVar(value=bool(self.settings.skip_death))
        self.skip_switch = ctk.CTkSwitch(
            body,
            text="Skip Death",
            variable=self.skip_var,
            command=self._toggle_skip_death,
            font=FONT_BODY_BOLD(),
            progress_color=COLORS["accent"],
            button_color=COLORS["text"],
            button_hover_color=COLORS["text"],
        )
        self.skip_switch.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(
            body,
            text="Your health is polled 250 times a second, so the killing blow is cancelled before "
                 "the game can start the death sequence. Forced deaths (traps, scripted scenes) are "
                 "answered on the death prompt as a last resort.",
            font=FONT_SMALL(),
            text_color=COLORS["text_faint"],
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(fill="x")

        protection = Card(
            parent,
            "Damage protection",
            "Optional extra. Off = normal damage, exactly like the game. On = health stays full "
            "the whole time.",
            glyph=ICONS["shield"],
            wrap=380,
        )
        protection.grid(row=0, column=1, sticky="nsew", padx=(GAP // 2, 0))
        pbody = protection.body
        self.protection_var = tk.BooleanVar(value=bool(self.settings.protection))
        self.protection_switch = ctk.CTkSwitch(
            pbody,
            text="Prevent damage",
            variable=self.protection_var,
            command=self._toggle_protection,
            font=FONT_BODY_BOLD(),
            progress_color=COLORS["accent"],
            button_color=COLORS["text"],
            button_hover_color=COLORS["text"],
        )
        self.protection_switch.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(
            pbody,
            text="Keeps Leon at full health for as long as it is on - useful while testing skins, "
                 "not recommended for normal play.",
            font=FONT_SMALL(),
            text_color=COLORS["text_faint"],
            wraplength=420,
            justify="left",
            anchor="w",
        ).pack(fill="x")

        status_card = Card(parent, "Live status", glyph=ICONS["heart"])
        status_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(GAP, 0))
        sbody = status_card.body

        hp_line = ctk.CTkFrame(sbody, fg_color="transparent")
        hp_line.pack(fill="x")
        self.hp_label = ctk.CTkLabel(hp_line, text="Health: -", font=FONT_H2(),
                                     text_color=COLORS["text_dim"], anchor="w")
        self.hp_label.pack(side="left")
        self.deaths_label = ctk.CTkLabel(hp_line, text="", font=FONT_SMALL(),
                                         text_color=COLORS["text_faint"], anchor="e")
        self.deaths_label.pack(side="right")

        self.hp_bar = ctk.CTkProgressBar(sbody, height=10, corner_radius=6,
                                         fg_color=COLORS["bg_soft"], progress_color=COLORS["accent"])
        self.hp_bar.pack(fill="x", pady=(8, 6))
        self.hp_bar.set(0)

        self.protection_label = ctk.CTkLabel(sbody, text="", font=FONT_SMALL(),
                                             text_color=COLORS["text_faint"], anchor="w",
                                             wraplength=760, justify="left")
        self.protection_label.pack(fill="x")
        self.heal_btn = ghost_button(sbody, f"{ICONS["heart"]}  Heal Leon now (test connection)",
                                     self._heal_now)
        self.heal_btn.pack(fill="x", pady=(12, 0))

        notes = Card(parent, "Good to know", glyph=ICONS["dot"])
        notes.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(GAP, 0))
        parent.grid_rowconfigure(2, weight=1)
        for glyph, text in (
            (ICONS["skins"], "Skins: RE4 keeps Leon's model in memory for the whole session, so a skin "
                             "only shows after the game is closed and started again. The trainer offers "
                             "to restart it for you when you press Apply."),
            (ICONS["save"], "Checkpoints: Save Last Checkpoint stores the save of your last typewriter. "
                            "Loading it always makes a safety copy of the current save first."),
            (ICONS["folder"], "Game folder: the trainer follows whichever copy you actually run, and backs "
                              "up the original files of that copy only - so your mods stay untouched."),
        ):
            line = ctk.CTkFrame(notes.body, fg_color="transparent")
            line.pack(fill="x", pady=3)
            ctk.CTkLabel(line, text=glyph, font=FONT_GLYPH(), text_color=COLORS["accent"],
                         width=22).pack(side="left", padx=(0, 8), anchor="n")
            ctk.CTkLabel(line, text=text, font=FONT_SMALL(), text_color=COLORS["text_dim"], anchor="w",
                         justify="left", wraplength=800).pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------------ skins
    # ------------------------------------------------------------------ skins
    def _refresh_skins(self) -> None:
        for child in self.skin_list.winfo_children():
            child.destroy()
        applied = self.skins.applied_skin()
        if not self.skins.library:
            ctk.CTkLabel(
                self.skin_list,
                text="No skins yet.\n\nUse 'Add Skin' and pick a .lfs file (e.g. pl00.udas.lfs) "
                     "or a folder/zip with the mod files.",
                font=FONT_SMALL(),
                text_color=COLORS["text_dim"],
                justify="left",
            ).pack(anchor="w", padx=10, pady=12)
        for skin in self.skins.library:
            self._add_skin_row(skin, selected=skin.id == self.selected_skin, applied=skin.id == applied)
        self._skin_signature = (applied, tuple(s.id for s in self.skins.library))
        self._update_action_states()
        self._update_skins_status()

    def _costume_tags(self, skin) -> str:
        tags = [LEON_OUTFITS[index] for index in self.skins.leon_outfits(skin)]
        if tags:
            return "  ·  " + " + ".join(tags) + " model"
        if any(pack_index(target) for target in skin.targets()):
            return "  ·  textures only"
        return ""

    def _add_skin_row(self, skin, selected: bool, applied: bool) -> None:
        base = COLORS["selected"] if selected else COLORS["panel_alt"]
        row = ctk.CTkFrame(
            self.skin_list,
            fg_color=base,
            corner_radius=RADIUS_SM,
            border_width=1,
            border_color=COLORS["accent_border"] if selected else COLORS["border_soft"],
        )
        row.pack(fill="x", pady=4, padx=5)

        def select(_event=None, skin_id=skin.id):
            self.selected_skin = skin_id
            self.settings.selected_skin = skin_id
            self.config_store.save()
            self._refresh_skins()

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=13, pady=(10, 0))
        mark = ctk.CTkFrame(top, fg_color=COLORS["accent"] if selected else COLORS["text_faint"],
                            width=8, height=8, corner_radius=999)
        mark.pack(side="left", padx=(0, 9))
        name = ctk.CTkLabel(top, text=skin.name, font=FONT_BODY_BOLD(), text_color=COLORS["text"], anchor="w")
        name.pack(side="left")
        if applied:
            ctk.CTkLabel(top, text="APPLIED", font=FONT_TINY(), text_color=COLORS["green"],
                         fg_color=COLORS["green_soft"], corner_radius=999).pack(side="right", ipadx=9, ipady=2)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(fill="x", padx=13, pady=(4, 10))
        outfits = self.skins.leon_outfits(skin)
        for index in outfits:
            Chip(info, LEON_OUTFITS[index], color=COLORS["gold"], fill=COLORS["bg_soft"],
                 glyph=ICONS["skins"]).pack(side="left", padx=(0, 6))
        if any(pack_index(target) for target in skin.targets()):
            Chip(info, "textures", color=COLORS["blue"], fill=COLORS["bg_soft"]).pack(side="left", padx=(0, 6))
        preview = ", ".join(Path(t).name for t in skin.targets()[:2])
        if skin.file_count > 2:
            preview += f"  (+{skin.file_count - 2} more)"
        sub = ctk.CTkLabel(info, text=f"{skin.file_count} file(s)  ·  {preview}",
                           font=FONT_TINY(), text_color=COLORS["text_faint"], anchor="e")
        sub.pack(side="right")

        widgets = [row, top, name, info, sub, mark]

        def on_enter(_event=None):
            row.configure(fg_color=COLORS["panel_hover"])

        def on_leave(_event=None):
            row.configure(fg_color=base)

        def on_double(_event=None):
            select()
            self.after(60, self._rename_skin)

        for widget in widgets:
            widget.bind("<Button-1>", select)
            widget.bind("<Double-Button-1>", on_double)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _update_skins_status(self) -> None:
        applied = self.skins.applied_skin()
        skin = self.skins.get(applied) if applied else None
        if skin:
            planned = {model_index(item.target) for item in self.skins.plan_apply(skin, self._outfit_mode())}
            note = "" if "00" in planned else "   ·   note: this skin does not change the Normal outfit"
            text = f"{ICONS["check"]}  Active skin: {skin.name}   ·   {self.skins.backup_count()} backup file(s){note}"
        else:
            text = f"{ICONS["dot"]}  Active: original game files   ·   {self.skins.backup_count()} backup file(s)"
        self.skins_status.configure(text=text)

    def _open_add_skin(self) -> None:
        if not self.game_dir():
            self.warn("Game folder", "Game folder not found. Use 'Browse...' first.")
            return
        AddSkinDialog(self, self.skins, on_added=self._on_skin_added)

    def _rename_skin(self) -> None:
        skin = self.skins.get(self.selected_skin)
        if not skin:
            self.note("Leon Skins", "Select a skin in the list first.")
            return
        name = dialogs.ask_text(
            self,
            "Rename skin",
            "Give this skin a name you will recognise in the list:",
            initial=skin.name,
        )
        if not name or name == skin.name:
            return
        try:
            self.skins.rename_skin(skin.id, name)
        except Exception as exc:  # noqa: BLE001
            self.error("Rename skin", str(exc))
            return
        self.log("info", f"Skin renamed to '{name}'.")
        self._refresh_skins()

    def _on_skin_added(self, skin) -> None:
        self.selected_skin = skin.id
        self.settings.selected_skin = skin.id
        self.config_store.save()
        self._refresh_skins()

    def _delete_skin(self) -> None:
        skin = self.skins.get(self.selected_skin)
        if not skin:
            self.note("Leon Skins", "Select a skin in the list first.")
            return
        if not self.confirm("Delete skin", f"Remove '{skin.name}' from the library?"):
            return
        self.skins.delete_skin(skin.id)
        self.selected_skin = ""
        self.settings.selected_skin = ""
        self.config_store.save()
        self._refresh_skins()

    def _on_outfit_mode(self, label: str) -> None:
        mode = self._outfit_label_to_mode.get(label, "both")
        self.settings.skin_outfit_mode = mode
        self.config_store.save()
        self._update_skins_status()

    def _on_palette(self, label: str) -> None:
        """Switch colour palette live: colours are shared, so the UI is rebuilt in place."""
        key = self._palette_label_to_key.get(label)
        if not key or key == self.settings.palette:
            return
        self.settings.palette = key
        self.config_store.save()
        apply_palette(key)
        current_page = self._active_page
        for child in self.winfo_children():
            child.destroy()
        self._page_frames = {}
        self._nav_buttons = {}
        self.configure(fg_color=COLORS["bg"])
        self._build()
        self._show_page(current_page)
        self._refresh_skins()
        self._refresh_checkpoint(force=True)
        self.log("info", f"Colours changed: {label}.")

    def _outfit_mode(self) -> str:
        mode = self._outfit_label_to_mode.get(self.outfit_var.get(), "both")
        return mode if mode in OUTFIT_MODES else "both"

    def _apply_skin(self) -> None:
        skin = self.skins.get(self.selected_skin)
        if not skin:
            self.note("Leon Skins", "Select a skin in the list first.")
            return
        if not self._require_admin("Applying a skin"):
            return
        mode = self._outfit_mode()
        plan = self.skins.apply_preview(skin, mode)
        files_text = "\n".join(f"   {line}" for line in plan)
        was_running = self._game_running
        restart = False
        if was_running:
            choice = dialogs.ask_choice(
                self,
                "Apply skin",
                f"'{skin.name}' will be written into the game files right now "
                f"({len(plan)} file(s)):\n\n{files_text}\n\n"
                "RE4 keeps Leon's model in memory for the whole session, so a running game "
                "can never show the new skin - it has to be closed and started again.\n\n"
                "Choose \"Apply + restart game\" and the trainer does that for you: your save "
                "is untouched, you only load it again from the main menu.",
                choices=[
                    ("Apply + restart game", "restart"),
                    ("Apply only", "apply"),
                ],
            )
            if not choice:
                return
            restart = choice == "restart"
        elif not self.confirm(
            "Apply skin",
            f"Apply '{skin.name}' now?\n\n{len(plan)} game file(s) will be replaced:\n\n{files_text}",
        ):
            return

        def done(name: str) -> None:
            self._refresh_skins()
            self.log("info", f"Applied skin: {name}")
            self.toast(f"Skin applied: {name}")
            if restart:
                self.log("info", "Restarting the game so Leon loads with the new skin...")
                self._run_async(self._restart_game, self._after_restart_note)
            elif was_running:
                self.note(
                    "Skin applied",
                    "Skin files updated.\n\nThe game must be closed and started again before "
                    "the skin shows - then choose LOAD GAME in the main menu and load your save.",
                )

        self._run_async(
            lambda: self.skins.apply_skin(skin.id, game_running=was_running, outfit_mode=mode),
            done,
        )

    def _restart_game(self) -> bool:
        """Close the running game and start it again (so a skin swap is picked up)."""
        exe_path = self.engine.snapshot().exe_path or find_game_exe_path()
        if not exe_path:
            self.log("warn", "Could not find the running game to restart it.")
            return False
        if not close_game_processes():
            self.log("warn", "The game did not close; it has to be closed manually.")
            return False
        time.sleep(1.5)
        if not launch_game(exe_path):
            self.log("warn", f"Could not start the game again: {exe_path}")
            return False
        self.log("info", f"Game restarted: {exe_path}")
        return True

    def _after_restart_note(self, ok: object) -> None:
        if ok:
            self.note(
                "Game restarted",
                "The game was closed and started again with the new files.\n\n"
                "In the main menu choose LOAD GAME and load your save - Leon is now wearing "
                "the new skin.",
            )
        else:
            self.note(
                "Restart the game",
                "The files are in place, but the game could not be restarted for you.\n\n"
                "Close Resident Evil 4 and start it again, then choose LOAD GAME.",
            )

    def _restore_original(self) -> None:
        if self.skins.backup_count() == 0:
            self.note("Restore original", "There are no backed-up game files to restore.")
            return
        if not self._require_admin("Restoring original files"):
            return
        was_running = self._game_running
        restart = False
        if was_running:
            choice = dialogs.ask_choice(
                self,
                "Restore original",
                "The original files will be restored right now.\n\n"
                "A running game keeps Leon's old model in memory, so it has to be closed and "
                "started again for the original files to show.",
                choices=[
                    ("Restore + restart game", "restart"),
                    ("Restore only", "apply"),
                ],
            )
            if not choice:
                return
            restart = choice == "restart"
        elif not self.confirm("Restore original", "Restore all original game files and remove the active skin?"):
            return

        def done(count: int) -> None:
            self._refresh_skins()
            self.log("info", f"Restored {count} original file(s).")
            if restart:
                self.log("info", "Restarting the game...")
                self._run_async(self._restart_game, self._after_restart_note)
            elif was_running:
                self.note(
                    "Original restored",
                    "Original files restored.\n\nClose the game and start it again to see them.",
                )

        self._run_async(lambda: self.skins.restore_original(game_running=was_running), done)

    # ------------------------------------------------------------- checkpoint
    def _save_checkpoint(self) -> None:
        self._run_async(self.checkpoint.create, self._after_checkpoint_change)

    def _load_checkpoint(self) -> None:
        status = self.checkpoint.status()
        if not status.exists:
            self.note("Checkpoint", "No checkpoint saved yet.")
            return
        if self._game_running:
            self.warn("Checkpoint", "Close Resident Evil 4 before loading a checkpoint.")
            return
        if not self._require_admin("Loading a checkpoint"):
            return
        if not self.confirm(
            "Load checkpoint",
            f"Replace your current save with the checkpoint from {status.created}?\n\n"
            "A safety copy of your current save is created first.",
        ):
            return

        def done(result) -> None:
            self._after_checkpoint_change(None)
            self.toast("Checkpoint restored - start the game and Load Game", "ok")
            self.note(
                "Checkpoint restored",
                f"Checkpoint restored.\n\nSave folder:\n{result['save_dir']}\n\n"
                f"Safety copy of the previous save:\n{result['safety_backup']}\n\n"
                "Start the game and choose Load Game.",
            )

        self._run_async(self.checkpoint.restore, done)

    def _after_checkpoint_change(self, _result) -> None:
        self._refresh_checkpoint(force=True)
        self.toast("Checkpoint saved", "ok")

    def _refresh_checkpoint(self, force: bool = False) -> None:
        status = self.checkpoint.status()
        signature = (status.exists, status.created, status.file_count, status.total_bytes)
        if not force and signature == self._checkpoint_signature:
            return
        self._checkpoint_signature = signature
        if status.exists:
            self.ck_status.configure(text="Last Checkpoint: Available", text_color=COLORS["green"])
            folder = Path(status.source_dir).name if status.source_dir else "-"
            self.ck_hint.configure(text=f"Saved {status.created}   ·   from '{folder}'")
        else:
            self.ck_status.configure(text="Last Checkpoint: Not Saved", text_color=COLORS["text_dim"])
            self.ck_hint.configure(text="Save in-game first, then press Save Last Checkpoint.")
        self._update_action_states()

    # ---------------------------------------------------------------- actions
    def _toggle_skip_death(self) -> None:
        enabled = bool(self.skip_var.get())
        self.engine.set_enabled(enabled)
        self.settings.skip_death = enabled
        self.config_store.save()
        self.log("info", f"Skip Death {'enabled' if enabled else 'disabled'}.")

    def _toggle_protection(self) -> None:
        enabled = bool(self.protection_var.get())
        self.engine.set_protection(enabled)
        self.settings.protection = enabled
        self.config_store.save()
        self.log("info", f"Damage protection {'enabled' if enabled else 'disabled'}.")

    def _heal_now(self) -> None:
        ok = self.engine.heal_now()
        if ok:
            self.log("info", "Heal sent - Leon should be at full health.")
            self.toast("Healed - Leon is at full health", "ok")
        else:
            self.log("warn", "Could not write health. Is the game running and the trainer attached?")
            self.toast("Could not heal - is the game running?", "warn")

    def _find_game_root(self, folder: Path) -> Optional[Path]:
        """Locate the real game root (the one with Bin32\\bio4.exe), even if the
        user picked a parent, the BIO4 data folder, or a nearby sub-folder."""
        def is_root(path: Path) -> bool:
            try:
                return (path / "Bin32" / "bio4.exe").is_file()
            except OSError:
                return False

        if is_root(folder):
            return folder
        # user may have picked the "BIO4" data folder or a folder inside the install
        for parent in (folder.parent, folder.parent.parent):
            if is_root(parent):
                return parent
        # or a folder that contains the install one/two levels down
        try:
            for child in folder.iterdir():
                if child.is_dir():
                    if is_root(child):
                        return child
                    try:
                        for grand in child.iterdir():
                            if grand.is_dir() and is_root(grand):
                                return grand
                    except OSError:
                        continue
        except OSError:
            pass
        return None

    def _browse_game_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select the folder that contains Bin32 and BIO4 (the game install)")
        if not folder:
            return
        candidate = Path(folder)
        game_root = self._find_game_root(candidate)
        if not game_root:
            self.warn(
                "Game folder",
                "Could not find Bin32\\bio4.exe in that folder or nearby.\n\n"
                "Pick the folder that contains the 'Bin32' and 'BIO4' folders.",
            )
            return
        if game_root != candidate:
            self.log("info", f"Detected the game root at: {game_root}")
        self.settings.game_dir = str(game_root)
        self.paths.game_dir = game_root
        self.skins._file_index = None
        self.config_store.save()
        self._update_path_label()
        self.log("info", f"Game folder set to {game_root}")

    def _sync_game_dir_from_running(self, exe_path: str) -> None:
        """Follow whichever game copy the player actually runs (some users keep several)."""
        try:
            exe = Path(exe_path)
            if not exe.is_file() or exe.name.lower() != "bio4.exe":
                return
            root = exe.parent.parent
            if not (root / "BIO4").is_dir():
                return
            current = self.game_dir()
            if current and root.resolve() == current.resolve():
                return
            self.settings.game_dir = str(root)
            self.paths.game_dir = root
            self.skins._file_index = None
            self.config_store.save()
            self.log("warn", f"Running game detected in another folder - skins now target: {root}")
            self._update_path_label()
            self._refresh_skins()
        except Exception as exc:
            self.log("warn", f"Could not follow the running game folder: {exc}")

    def _detect_paths(self) -> None:
        self.paths = discover(self.settings.game_dir, self.settings.save_dir)
        if self.paths.game_dir:
            self.settings.game_dir = str(self.paths.game_dir)
        if self.paths.save_dir:
            self.settings.save_dir = str(self.paths.save_dir)
            self.config_store.save()
        self._update_path_label()
        self._refresh_checkpoint(force=True)
        self.log("info", "Detection refreshed.")

    def _update_path_label(self) -> None:
        game = self.game_dir()
        if game:
            self.path_label.configure(text=f"Game folder: {game}", text_color=COLORS["text_dim"])
        else:
            self.path_label.configure(text="Game folder: not found - use Browse... to point at it", text_color=COLORS["amber"])

    def _update_action_states(self) -> None:
        selected = bool(self.skins.get(self.selected_skin))
        can_write = self.admin
        status = self.checkpoint.status()

        def style(button, enabled: bool, accent: bool = False) -> None:
            if enabled:
                button.configure(
                    state="normal",
                    fg_color=COLORS["accent"] if accent else COLORS["panel_alt"],
                    hover_color=COLORS["accent_hover"] if accent else COLORS["panel_hover"],
                    text_color="#FFFFFF" if accent else COLORS["text_dim"],
                )
            else:
                button.configure(
                    state="disabled",
                    fg_color=COLORS["panel_alt"],
                    text_color=COLORS["text_faint"],
                )

        style(self.apply_skin_btn, selected and can_write, accent=True)
        style(self.restore_btn, self.skins.backup_count() > 0 and can_write)
        style(self.ck_load_btn, status.exists and can_write)
        style(self.ck_save_btn, True, accent=True)

    # ------------------------------------------------------------------- tick
    def _animate_hp(self, target: float) -> None:
        """Move the health bar smoothly instead of jumping on every poll."""
        self._hp_target = target
        if getattr(self, "_hp_anim_running", False):
            return
        self._hp_anim_running = True
        self._step_hp()

    def _step_hp(self) -> None:
        try:
            if not self.winfo_exists():
                self._hp_anim_running = False
                return
            current = getattr(self, "_hp_shown", 0.0)
            target = getattr(self, "_hp_target", 0.0)
            diff = target - current
            if abs(diff) < 0.004:
                self._hp_shown = target
                self.hp_bar.set(target)
                self.hp_bar.configure(
                    progress_color=COLORS["accent"] if target <= 0 or target > 0.25 else COLORS["red"]
                )
                self._hp_anim_running = False
                return
            self._hp_shown = current + diff * 0.3
            self.hp_bar.set(self._hp_shown)
            self.hp_bar.configure(
                progress_color=COLORS["accent"] if self._hp_shown <= 0 or self._hp_shown > 0.25
                else COLORS["red"]
            )
            self.after(16, self._step_hp)
        except Exception:
            self._hp_anim_running = False

    def _tick(self) -> None:
        try:
            self._game_running = bool(find_game_processes())
            snapshot = self.engine.snapshot()
            self._pulse_on = not self._pulse_on
            if snapshot.attached and snapshot.exe_path:
                self._sync_game_dir_from_running(snapshot.exe_path)

            if self._game_running and snapshot.attached:
                dot = COLORS["green"] if self._pulse_on else "#2E7D5B"
                self.status_pill.set(f"Resident Evil 4 detected - attached (PID {snapshot.pid})", dot)
            elif self._game_running:
                self.status_pill.set("Resident Evil 4 running - connecting...", COLORS["amber"])
            else:
                self.status_pill.set("Game not running", COLORS["text_faint"])

            if snapshot.attached and snapshot.hp is not None:
                self.hp_label.configure(text=f"Health   {snapshot.hp} / {snapshot.hp_max}", text_color=COLORS["text"])
                self.ov_health.set(f"{snapshot.hp} / {snapshot.hp_max}", COLORS["text"])
                try:
                    maximum = max(1, int(snapshot.hp_max or 1))
                    self._animate_hp(min(1.0, max(0.0, float(snapshot.hp or 0) / maximum)))
                except Exception:
                    pass
            else:
                self.hp_label.configure(text=f"Health   -   {snapshot.message}", text_color=COLORS["text_dim"])
                self.ov_health.set("-", COLORS["text_faint"])
                try:
                    self._animate_hp(0.0)
                except Exception:
                    pass

            if self._game_running and snapshot.attached:
                self.ov_conn.set(f"Attached  ·  PID {snapshot.pid}", COLORS["green"])
            elif self._game_running:
                self.ov_conn.set("Connecting...", COLORS["amber"])
            else:
                self.ov_conn.set("Game not running", COLORS["text_faint"])
            self.ov_deaths.set(str(snapshot.respawns), COLORS["text"] if snapshot.respawns else COLORS["text_dim"])
            self.ov_handled.set(str(snapshot.deaths_skipped),
                                COLORS["text"] if snapshot.deaths_skipped else COLORS["text_dim"])

            if not snapshot.enabled:
                text = "Skip Death is OFF."
            elif not snapshot.attached:
                text = "Waiting for the game to start..."
            elif snapshot.protection and snapshot.re4_tweaks:
                text = "Damage protection: ON (health guard + re4_tweaks invulnerability)."
            elif snapshot.protection:
                text = "Damage protection: ON (health guard only - re4_tweaks not detected)."
            else:
                text = (
                    "Normal damage - but the moment Leon would die he is revived instantly "
                    "(no death screen, nothing clicked)."
                )
            self.protection_label.configure(text=text)
            self.deaths_label.configure(
                text=f"{snapshot.respawns} instant respawn(s)   ·   {snapshot.deaths_skipped} death(s) handled"
            )

            self._update_path_label()
            self._refresh_checkpoint()
            signature = (self.skins.applied_skin(), tuple(s.id for s in self.skins.library))
            if signature != self._skin_signature:
                self._refresh_skins()
            self._update_action_states()
        except Exception as exc:  # never let the UI loop die
            self.log("error", f"UI refresh problem: {exc}")
        finally:
            if self.winfo_exists():
                self.after(500, self._tick)

    # ------------------------------------------------------------------ close
    def _on_close(self) -> None:
        try:
            self.settings.window_geometry = self.geometry()
            self.settings.selected_skin = self.selected_skin
            self.config_store.save()
        except Exception:
            pass
        try:
            self.engine.stop()
        except Exception:
            pass
        self.destroy()
