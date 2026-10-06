"""'Last Checkpoint' - backup and restore of the game's save data.

How this really works (verified against the Steam re-release of RE4 2005):

* The game stores a single file ``savegame00.sav`` (one file for all story
  slots) inside the Steam Cloud folder:
  ``<Steam>\\userdata\\<id>\\254700\\remote\\savegame00.sav``
* The game only writes that file when you save at a typewriter.  A trainer
  cannot capture unsaved progress, so a "checkpoint" is a snapshot of the
  save file at the moment you press the button (save at a typewriter first).
* Loading a checkpoint is a file restore.  It takes effect the next time the
  game reads the save (main menu "Load Game"), so the game must be closed
  while the files are being swapped.  We always create a safety backup of the
  current save before overwriting it.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..core.gamepaths import SAVE_GLOB, resolve_save_dir
from ..core.utils import copy_file, human_bytes, now_iso, sha256_file, timestamp_slug


class CheckpointError(RuntimeError):
    pass


@dataclass
class CheckpointStatus:
    exists: bool = False
    created: str = ""
    file_count: int = 0
    total_bytes: int = 0
    source_dir: str = ""
    location: str = ""

    @property
    def summary(self) -> str:
        if not self.exists:
            return "Not saved"
        return f"Available - {self.created} ({human_bytes(self.total_bytes)})"


class CheckpointManager:
    def __init__(self, config, log: Optional[Callable[[str, str], None]] = None) -> None:
        self.config = config
        self._log = log or (lambda level, message: None)

    # -- helpers -------------------------------------------------------------
    def resolve_save_dir(self) -> Optional[Path]:
        return resolve_save_dir(self.config.settings.save_dir)

    def _checkpoint_files(self) -> List[Path]:
        if not self.config.last_checkpoint_dir.is_dir():
            return []
        return sorted(self.config.last_checkpoint_dir.glob(SAVE_GLOB))

    def _read_meta(self) -> Dict:
        meta_path = self.config.last_checkpoint_dir / "checkpoint.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    # -- public API ----------------------------------------------------------
    def status(self) -> CheckpointStatus:
        files = self._checkpoint_files()
        if not files:
            return CheckpointStatus(exists=False, location=str(self.config.last_checkpoint_dir))
        meta = self._read_meta()
        return CheckpointStatus(
            exists=True,
            created=meta.get("created", ""),
            file_count=len(files),
            total_bytes=sum(f.stat().st_size for f in files),
            source_dir=meta.get("source_dir", ""),
            location=str(self.config.last_checkpoint_dir),
        )

    def create(self) -> CheckpointStatus:
        """Snapshot the current save files into the Last Checkpoint slot."""
        save_dir = self.resolve_save_dir()
        if not save_dir:
            raise CheckpointError(
                "Could not find the game's save folder. Make sure you have launched "
                "the game at least once, then press 'Detect again'."
            )
        saves = sorted(save_dir.glob(SAVE_GLOB))
        if not saves:
            raise CheckpointError(f"No save files found in:\n{save_dir}")

        # keep the previous checkpoint in history
        if self._checkpoint_files():
            archive = self.config.checkpoint_history_dir / timestamp_slug()
            archive.mkdir(parents=True, exist_ok=True)
            for file in self._checkpoint_files() + [self.config.last_checkpoint_dir / "checkpoint.json"]:
                if file.exists():
                    shutil.copy2(file, archive / file.name)
            self._prune_history()

        entries = []
        for file in saves:
            copy_file(file, self.config.last_checkpoint_dir / file.name)
            entries.append(
                {
                    "name": file.name,
                    "size": file.stat().st_size,
                    "sha256": sha256_file(file),
                }
            )
        meta = {
            "created": now_iso(),
            "source_dir": str(save_dir),
            "files": entries,
        }
        (self.config.last_checkpoint_dir / "checkpoint.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        # remember the save folder for next time
        self.config.settings.save_dir = str(save_dir)
        self.config.save()
        self._log("info", f"Checkpoint saved from {save_dir} ({len(entries)} file(s)).")
        return self.status()

    def _safety_backup(self, save_dir: Path) -> Path:
        dest = self.config.save_backups_dir / timestamp_slug()
        dest.mkdir(parents=True, exist_ok=True)
        for file in save_dir.glob(SAVE_GLOB):
            shutil.copy2(file, dest / file.name)
        return dest

    def restore(self) -> Dict[str, str]:
        """Restore the Last Checkpoint over the live save files (game must be closed)."""
        files = self._checkpoint_files()
        if not files:
            raise CheckpointError("No checkpoint has been saved yet.")
        save_dir = self.resolve_save_dir()
        if not save_dir:
            raise CheckpointError("Could not find the game's save folder.")

        backup = self._safety_backup(save_dir)
        restored = []
        for file in files:
            shutil.copy2(file, save_dir / file.name)
            restored.append(file.name)
        meta = self._read_meta()
        self._log(
            "info",
            f"Checkpoint restored to {save_dir}. Safety backup: {backup}",
        )
        return {
            "restored": ", ".join(restored),
            "save_dir": str(save_dir),
            "safety_backup": str(backup),
            "created": meta.get("created", ""),
        }

    def history(self) -> List[Path]:
        if not self.config.checkpoint_history_dir.is_dir():
            return []
        return sorted(
            (p for p in self.config.checkpoint_history_dir.iterdir() if p.is_dir()),
            reverse=True,
        )

    def _prune_history(self, keep: int = 10) -> None:
        for old in self.history()[keep:]:
            shutil.rmtree(old, ignore_errors=True)
