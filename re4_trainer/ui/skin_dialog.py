"""Dialog: add a skin to the library and choose which game files it replaces."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from ..features.skins import SKIN_FILE_SUFFIX, SkinCandidate, SkinError
from . import dialogs
from .theme import COLORS, FONT_BODY, FONT_H2, FONT_SMALL


class TargetPicker(ctk.CTkToplevel):
    """Searchable list of game files to install a mod file as."""

    def __init__(self, master, targets: List[str], current: Optional[str] = None):
        super().__init__(master)
        self.title("Choose install target")
        self.geometry("640x480")
        self.transient(master)
        self.grab_set()
        self.result: Optional[str] = None
        self._all = targets

        ctk.CTkLabel(self, text="Which game file should this replace?", font=FONT_H2()).pack(anchor="w", padx=16, pady=(14, 4))

        self.filter_var = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self.filter_var, placeholder_text="Type to filter (e.g. pl00)...")
        entry.pack(fill="x", padx=16, pady=(0, 8))
        entry.bind("<KeyRelease>", lambda _e: self._refresh())

        list_frame = ctk.CTkFrame(self, fg_color=COLORS["panel_alt"], corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.listbox = tk.Listbox(
            list_frame,
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground="#FFFFFF",
            highlightthickness=0,
            bd=0,
            activestyle="none",
            font=("Consolas", 10),
        )
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox.bind("<Double-Button-1>", lambda _e: self._accept())

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(buttons, text="Select", command=self._accept, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]).pack(side="right")
        ctk.CTkButton(buttons, text="Cancel", command=self.destroy, fg_color=COLORS["panel_alt"], hover_color=COLORS["panel_hover"]).pack(side="right", padx=8)

        if current:
            self.filter_var.set(Path(current).name)
        self._refresh()
        entry.focus_set()

    def _refresh(self) -> None:
        needle = self.filter_var.get().strip().lower()
        self.listbox.delete(0, "end")
        self._shown: List[str] = []
        for target in self._all:
            if needle and needle not in target.lower():
                continue
            self._shown.append(target)
            self.listbox.insert("end", target)
        if self._shown:
            self.listbox.selection_set(0)

    def _accept(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.result = self._shown[selection[0]]
        self.destroy()


class AddSkinDialog(ctk.CTkToplevel):
    def __init__(self, master, skin_manager, on_added: Callable[[object], None]):
        super().__init__(master)
        self.title("Add Leon skin")
        self.geometry("780x560")
        self.minsize(680, 480)
        self.transient(master)
        self.grab_set()

        self.manager = skin_manager
        self.on_added = on_added
        self._row_widgets: List[Dict] = []
        self._index = None
        self._candidates: Optional[List[str]] = None

        ctk.CTkLabel(self, text="Add a skin to your library", font=FONT_H2()).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            self,
            text="Pick the mod's .lfs file(s), its whole folder, or a .zip - skin files are found "
                 "automatically, even inside sub-folders or nested .zip files, and even if they are "
                 "renamed (their LFS content is detected). Each file is matched to the same-named "
                 "game file; you can change or remove any entry before adding. (.rar mods: extract first.)",
            font=FONT_SMALL(),
            text_color=COLORS["text_dim"],
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 8))

        name_row = ctk.CTkFrame(self, fg_color="transparent")
        name_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(name_row, text="Skin name:", font=FONT_BODY()).pack(side="left")
        self.name_var = tk.StringVar(value="")
        ctk.CTkEntry(name_row, textvariable=self.name_var, width=300).pack(side="left", padx=8)

        pick_row = ctk.CTkFrame(self, fg_color="transparent")
        pick_row.pack(fill="x", padx=16)
        ctk.CTkButton(
            pick_row, text="Choose folder...", command=self._choose_folder,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
        ).pack(side="left")
        ctk.CTkButton(
            pick_row, text="Choose files...", command=self._choose_files,
            fg_color=COLORS["panel_alt"], hover_color=COLORS["panel_hover"],
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            pick_row, text="Clear", width=64, command=self._clear_rows,
            fg_color=COLORS["panel_alt"], hover_color=COLORS["panel_hover"],
        ).pack(side="left", padx=(0, 8))
        self.status = ctk.CTkLabel(pick_row, text="", font=FONT_SMALL(), text_color=COLORS["text_dim"])
        self.status.pack(side="left", padx=8)

        self.rows_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["panel_alt"], corner_radius=8)
        self.rows_frame.pack(fill="both", expand=True, padx=16, pady=10)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 14))
        self.add_button = ctk.CTkButton(footer, text="Add to Library", command=self._submit, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
        self.add_button.pack(side="right")
        ctk.CTkButton(footer, text="Cancel", command=self.destroy, fg_color=COLORS["panel_alt"], hover_color=COLORS["panel_hover"]).pack(side="right", padx=8)

    # -- source selection ----------------------------------------------------
    def _choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select skin files",
            filetypes=[("RE4 archives", "*.lfs *.udas"), ("All files", "*.*")],
        )
        if paths:
            self._load_sources([Path(p) for p in paths])

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select a folder containing the skin files")
        if folder:
            self._load_sources([Path(folder)])

    def _load_sources(self, paths: List[Path]) -> None:
        try:
            candidates = self.manager.collect_candidates(paths)
        except SkinError as exc:
            dialogs.show_error(self, "Add skin", str(exc))
            return
        if not candidates:
            dialogs.show_warning(
                self,
                "Add skin",
                "No skin files were found in the selection.\n\n"
                "Supported: .lfs archives (even renamed ones - detected by content), folders "
                "containing them (including nested .zip files), and .zip archives directly. "
                "If your mod is a .rar file, extract it first.",
            )
            return
        if not self.name_var.get().strip():
            self.name_var.set(paths[0].stem if paths[0].is_file() else paths[0].name)
        self.status.configure(text=f"Found {len(candidates)} file(s) - scanning game files...")
        self.after(40, lambda c=candidates: self._add_rows_async(c))

    def _add_rows_async(self, candidates: List[SkinCandidate]) -> None:
        if self._index is None:
            self._index = self.manager.game_file_index(refresh=True)
        if self._candidates is None:
            self._candidates = self.manager.candidate_targets()
        existing = {str(row["source"]).lower() for row in self._row_widgets}
        for candidate in candidates:
            key = str(candidate.path).lower()
            if key in existing:
                continue
            existing.add(key)
            target = self.manager.auto_target(candidate.path.name, self._index, rel_hint=candidate.rel_hint) or ""
            self._add_row(candidate.path, target)
        self._update_count()

    def _clear_rows(self) -> None:
        for row in list(self._row_widgets):
            row["frame"].destroy()
        self._row_widgets.clear()
        self._update_count()

    def _update_count(self) -> None:
        self.status.configure(text=f"{len(self._row_widgets)} file(s) ready")

    def _add_row(self, source: Path, target: str) -> None:
        frame = ctk.CTkFrame(self.rows_frame, fg_color=COLORS["panel"], corner_radius=8)
        frame.pack(fill="x", pady=3, padx=2)

        text = ctk.CTkFrame(frame, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=8)
        ctk.CTkLabel(text, text=source.name, font=FONT_BODY(), anchor="w").pack(fill="x")
        target_label = ctk.CTkLabel(
            text,
            text=target or "No matching game file - choose one",
            font=FONT_SMALL(),
            text_color=COLORS["text_dim"] if target else COLORS["amber"],
            anchor="w",
        )
        target_label.pack(fill="x")

        state = {"source": source, "target": target, "label": target_label, "frame": frame}

        def choose() -> None:
            picker = TargetPicker(self, self._candidates or [], current=state["target"] or None)
            self.wait_window(picker)
            if picker.result:
                state["target"] = picker.result
                state["label"].configure(text=picker.result, text_color=COLORS["text_dim"])

        def remove() -> None:
            if state in self._row_widgets:
                self._row_widgets.remove(state)
            frame.destroy()
            self._update_count()

        ctk.CTkButton(
            frame, text="X", width=30, command=remove,
            fg_color="#3A2226", hover_color="#523036", text_color=COLORS["red"],
        ).pack(side="right", padx=(0, 10))
        ctk.CTkButton(frame, text="Target...", width=90, command=choose, fg_color=COLORS["panel_alt"], hover_color=COLORS["panel_hover"]).pack(side="right", padx=6)
        self._row_widgets.append(state)

    # -- submit --------------------------------------------------------------
    def _submit(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            dialogs.show_warning(self, "Add skin", "Give the skin a name first.")
            return
        if not self._row_widgets:
            dialogs.show_warning(self, "Add skin", "Choose the skin files first.")
            return
        missing = [row for row in self._row_widgets if not row["target"]]
        if missing:
            names = "\n".join(f"- {row['source'].name}" for row in missing[:10])
            if len(missing) > 10:
                names += f"\n...and {len(missing) - 10} more"
            if not dialogs.ask_yes_no(
                self,
                "Add skin",
                "These files have no install target (the game does not have a matching file):\n"
                f"{names}\n\nSkip them and add the other file(s)?",
            ):
                return
        entries = [(row["source"], row["target"]) for row in self._row_widgets if row["target"]]
        if not entries:
            dialogs.show_warning(self, "Add skin", "No file with an install target was left.")
            return
        try:
            skin = self.manager.add_skin(name, entries)
        except SkinError as exc:
            dialogs.show_error(self, "Add skin", str(exc))
            return
        self.on_added(skin)
        self.destroy()
