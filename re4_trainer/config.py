"""Persistent configuration and app data locations."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

APP_ID = "RE4ClassicTrainer"


def default_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / APP_ID


@dataclass
class Settings:
    game_dir: str = ""
    save_dir: str = ""
    skip_death: bool = False
    protection: bool = False
    continue_key: str = "RETURN"
    yes_click_x: float = 0.40
    yes_click_y: float = 0.70
    selected_skin: str = ""
    applied_skin: str = ""
    skin_outfit_mode: str = "both"
    palette: str = "neon"
    window_geometry: str = "1140x880"


class ConfigStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else default_data_root()
        self.skins_dir = self.root / "skins"
        self.backups_dir = self.root / "backups"
        self.game_backups_dir = self.backups_dir / "game"
        self.save_backups_dir = self.backups_dir / "saves"
        self.checkpoints_dir = self.root / "checkpoints"
        self.last_checkpoint_dir = self.checkpoints_dir / "last"
        self.checkpoint_history_dir = self.checkpoints_dir / "history"
        self.logs_dir = self.root / "logs"
        self.settings_path = self.root / "settings.json"
        self.state_path = self.root / "state.json"
        self.settings = Settings()
        self.ensure_dirs()
        self.load()

    def ensure_dirs(self) -> None:
        for d in (
            self.root,
            self.skins_dir,
            self.game_backups_dir,
            self.save_backups_dir,
            self.last_checkpoint_dir,
            self.checkpoint_history_dir,
            self.logs_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    # -- settings ------------------------------------------------------------
    def load(self) -> Settings:
        if self.settings_path.exists():
            try:
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
                for key, value in data.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
            except Exception:
                pass
        return self.settings

    def save(self) -> None:
        tmp = self.settings_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self.settings), indent=2), encoding="utf-8")
        tmp.replace(self.settings_path)

    # -- mutable app state (which skin is applied etc.) ----------------------
    def load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)
