"""Leon skin manager.

Verified behaviour of the Steam re-release of RE4 (2005):

* Character data lives in ``<game>\\BIO4\\Em\\*.udas.lfs``.  Leon's model and
  textures are inside ``pl00.udas.lfs`` (other ``plXX`` files hold the other
  characters/costumes, ``emXX``/``wepXX`` hold enemies/weapons).
* Leon has **two outfits**, and each one is a *separate model file* with its own
  texture pack:

  ==================  ==========================  ===============================
  outfit              model                       4K texture pack
  ==================  ==========================  ===============================
  Normal              ``BIO4\\Em\\pl00.udas.lfs``  ``BIO4\\ImagePackHD\\01000000...``
  Mafia (costume 1)   ``BIO4\\Em\\pl08.udas.lfs``  ``BIO4\\ImagePackHD\\01000008...``
  ==================  ==========================  ===============================

  This is why most downloaded "Leon skins" look like they do nothing: they ship
  only ``pl08``, but a story save wears the Normal outfit (``pl00``), so the
  files the game actually reads are untouched.  :meth:`SkinManager.plan_apply`
  therefore mirrors the skin's model + texture pack into every Leon outfit the
  save might be wearing, which makes the skin show up in any save.
* Community skin mods are distributed as replacement ``.lfs`` files with the
  same name as the game file they replace; installing one is normally
  "backup the original, drop the file in".

This module automates exactly that:

* Skins are copied into a library under ``%LOCALAPPDATA%\\RE4ClassicTrainer``.
* The first time a game file is about to be replaced, the original is backed
  up (with hash + timestamp) - switching skins never touches the backup.
* "Restore Original" copies every backed-up original back.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from ..core.utils import copy_file, now_iso, safe_slug, sha256_file

LFS_MAGICS = (b"RDLX", b"XDLR")
CHARACTER_DIR = Path("BIO4") / "Em"
SKIN_FILE_SUFFIX = ".lfs"

#: Leon's outfit slots: index -> human label (see module docstring).
LEON_OUTFITS: Dict[str, str] = {
    "00": "Normal outfit",
    "08": "Mafia outfit (Special Costume 1)",
}

#: Which Leon outfit slots an apply should fill, per user setting.
OUTFIT_MODES: Dict[str, Tuple[str, ...]] = {
    "both": ("00", "08"),
    "normal": ("00",),
    "gangster": ("08",),
    "as_shipped": (),
}

OUTFIT_MODE_LABELS: Dict[str, str] = {
    "both": "Both outfits (always shows)",
    "normal": "Normal outfit only",
    "gangster": "Mafia outfit only",
    "as_shipped": "Exactly as the skin ships",
}

_EM_INDEX_RE = re.compile(r"\\pl([0-9a-f]{2})\.udas\.lfs$", re.IGNORECASE)
_HD_INDEX_RE = re.compile(r"\\010000([0-9a-f]{2})\.pack(?:\.yz2)?(?:\.lfs)?$", re.IGNORECASE)


def model_index(target: str) -> Optional[str]:
    """``pl08.udas.lfs`` -> ``"08"`` (None for non-Leon models)."""
    match = _EM_INDEX_RE.search(str(target).replace("/", "\\"))
    if not match:
        return None
    index = match.group(1).lower()
    return index if index in LEON_OUTFITS else None


def pack_index(target: str) -> Optional[str]:
    """``01000008.pack.yz2.lfs`` -> ``"08"`` (None for unrelated packs)."""
    match = _HD_INDEX_RE.search(str(target).replace("/", "\\"))
    if not match:
        return None
    index = match.group(1).lower()
    return index if index in LEON_OUTFITS else None


class SkinError(RuntimeError):
    pass


class GameRunningError(SkinError):
    pass


@dataclass
class SkinFile:
    stored_name: str
    target: str          # path relative to the game folder
    size: int
    sha256: str
    source_name: str


@dataclass
class Skin:
    id: str
    name: str
    created: str = ""
    files: List[SkinFile] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.files)

    def targets(self) -> List[str]:
        return [f.target for f in self.files]


@dataclass
class SkinCandidate:
    """A file found for import, with its path relative to the folder/zip it came from."""

    path: Path
    rel_hint: Optional[str] = None


@dataclass
class ApplyItem:
    """One library file -> one game file write, as produced by :meth:`SkinManager.plan_apply`."""

    stored_name: str
    target: str
    source_name: str
    label: str = ""
    mirrored: bool = False


class SkinManager:
    def __init__(
        self,
        config,
        get_game_dir: Callable[[], Optional[Path]],
        log: Optional[Callable[[str, str], None]] = None,
        legacy_install_dir: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.get_game_dir = get_game_dir
        self._log = log or (lambda level, message: None)
        self._legacy_install_dir = Path(legacy_install_dir) if legacy_install_dir else None
        self.library: List[Skin] = []
        self._file_index: Optional[Dict[str, List[str]]] = None
        self.refresh()

    # -- library -------------------------------------------------------------
    def refresh(self) -> List[Skin]:
        skins: List[Skin] = []
        if self.config.skins_dir.is_dir():
            for folder in sorted(self.config.skins_dir.iterdir()):
                manifest = folder / "skin.json"
                if not manifest.is_file():
                    continue
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    files = [SkinFile(**entry) for entry in data.get("files", [])]
                    skins.append(
                        Skin(
                            id=data.get("id", folder.name),
                            name=data.get("name", folder.name),
                            created=data.get("created", ""),
                            files=files,
                        )
                    )
                except Exception as exc:  # corrupt manifest - skip but report
                    self._log("warn", f"Could not read skin '{folder.name}': {exc}")
        self.library = skins
        return skins

    def get(self, skin_id: str) -> Optional[Skin]:
        for skin in self.library:
            if skin.id == skin_id:
                return skin
        return None

    def game_file_index(self, refresh: bool = False) -> Dict[str, List[str]]:
        """Map of lowercase filename -> list of game-relative paths."""
        if self._file_index is not None and not refresh:
            return self._file_index
        index: Dict[str, List[str]] = {}
        game_dir = self.get_game_dir()
        if game_dir and game_dir.is_dir():
            for path in game_dir.rglob("*"):
                if path.is_file():
                    index.setdefault(path.name.lower(), []).append(str(path.relative_to(game_dir)))
        self._file_index = index
        return index

    @staticmethod
    def _prefer(matches: List[str]) -> Optional[str]:
        matches = sorted(set(matches), key=lambda p: (0 if p.lower().startswith("bio4\\") else 1, len(p)))
        return matches[0] if matches else None

    def auto_target(
        self,
        filename: str,
        index: Optional[Dict[str, List[str]]] = None,
        rel_hint: Optional[str] = None,
    ) -> Optional[str]:
        """Best game-relative install target for a mod file.

        When the file came from a folder that mirrors the game layout
        (e.g. ``ImagePackHD\\01000000.pack.yz2.lfs``), the matching game path is
        used even if the same filename also exists in another game folder.
        """
        index = index if index is not None else self.game_file_index()
        name = Path(filename).name.lower()

        if rel_hint:
            rel = str(rel_hint).replace("/", "\\").lower().strip("\\")
            if rel:
                hits: List[str] = []
                for paths in index.values():
                    for game_rel in paths:
                        low = game_rel.lower()
                        if low == rel or low.endswith("\\" + rel):
                            hits.append(game_rel)
                preferred = self._prefer(hits)
                if preferred:
                    return preferred

        matches = list(index.get(name, []))
        if not matches:
            # prefix match: "pl00.udas" -> "pl00.udas.lfs", "pl00" -> "pl00.udas.lfs"
            for game_name, paths in index.items():
                if game_name.startswith(name + "."):
                    matches.extend(paths)
        return self._prefer(matches)

    def candidate_targets(self) -> List[str]:
        """Character-related files, for manual target assignment."""
        index = self.game_file_index()
        targets: List[str] = []
        for paths in index.values():
            for rel in paths:
                low = rel.lower()
                if low.endswith(SKIN_FILE_SUFFIX) and (
                    low.startswith(str(CHARACTER_DIR).lower()) or "\\pl" in low or "\\em" in low or "\\wep" in low
                ):
                    targets.append(rel)
        return sorted(set(targets), key=str.lower)

    def validate_skin_payload(self, path: Path) -> Tuple[bool, str]:
        """Check that a file really is an LFS archive (content decides, not the name)."""
        try:
            with open(path, "rb") as handle:
                head = handle.read(4)
        except OSError as exc:
            return False, f"cannot read file: {exc}"
        if not head:
            return False, "file is empty"
        if head in LFS_MAGICS:
            return True, ""
        if path.suffix.lower() == ".udas":
            return False, (
                "This is an uncompressed .udas file. The game needs a packed .lfs file "
                "(mods normally ship as 'plXX.udas.lfs')."
            )
        return False, "This does not look like an RE4 .lfs archive (missing LFS magic bytes)."

    # -- Leon outfit planning ------------------------------------------------
    def leon_outfits(self, skin: Skin) -> List[str]:
        """Leon outfit slots this skin actually ships a model for."""
        found: List[str] = []
        for entry in skin.files:
            index = model_index(entry.target)
            if index and index not in found:
                found.append(index)
        return sorted(found)

    @staticmethod
    def _pack_target(game_dir: Optional[Path], index: str) -> Optional[str]:
        """Game path of the texture pack that belongs to Leon outfit ``index``."""
        if not game_dir:
            return None
        for folder in (Path("BIO4") / "ImagePackHD", Path("BIO4") / "ImagePack"):
            for name in (
                f"010000{index}.pack.yz2.lfs",
                f"010000{index}.pack.lfs",
                f"010000{index}.pack.yz2",
                f"010000{index}.pack",
            ):
                rel = str(folder / name)
                if (game_dir / rel).is_file():
                    return rel
        return None

    @staticmethod
    def _sibling_variants(game_dir: Path, target: str) -> List[str]:
        """Other installed files sharing a pack's base name (old mod leftovers)."""
        match = _HD_INDEX_RE.search(str(target).replace("/", "\\"))
        if not match:
            return []
        base = f"010000{match.group(1)}"
        folder = Path(target).parent
        mine = Path(target).name.lower()
        try:
            return sorted(
                child.name for child in folder.glob(f"{base}.*") if child.name.lower() != mine
            )
        except OSError:
            return []

    def plan_apply(
        self,
        skin: Skin,
        outfit_mode: str = "both",
        game_dir: Optional[Path] = None,
    ) -> List[ApplyItem]:
        """Exact list of writes an apply would do.

        A skin that only ships ``pl08`` (Mafia) is invisible in a save that wears
        the Normal outfit, so unless the user picks "as shipped" the model *and*
        its texture pack are mirrored into every Leon outfit slot.  Mods are left
        alone otherwise: every other file the skin ships is written as-is.
        """
        if game_dir is None:
            game_dir = self.get_game_dir()
        wanted = OUTFIT_MODES.get(outfit_mode, OUTFIT_MODES["both"])

        items: List[ApplyItem] = []
        shipped_models: Dict[str, SkinFile] = {}
        shipped_packs: Dict[str, SkinFile] = {}
        for entry in skin.files:
            model_slot = model_index(entry.target)
            pack_slot = pack_index(entry.target)
            if model_slot:
                shipped_models.setdefault(model_slot, entry)
            if pack_slot:
                shipped_packs.setdefault(pack_slot, entry)
            # a specific outfit choice also restricts what the skin ships itself
            if wanted and ((model_slot and model_slot not in wanted) or (pack_slot and pack_slot not in wanted)):
                continue
            items.append(ApplyItem(entry.stored_name, entry.target, entry.source_name))
        by_target: Dict[str, ApplyItem] = {item.target.lower(): item for item in items}

        def put(entry: SkinFile, target: str, label: str) -> Optional[ApplyItem]:
            key = target.lower()
            if key in by_target:
                return by_target[key]
            if game_dir and not (game_dir / target).is_file():
                self._log("warn", f"Skipped {target} (this install does not have that file).")
                return None
            item = ApplyItem(entry.stored_name, target, entry.source_name, label, mirrored=True)
            by_target[key] = item
            items.append(item)
            return item

        if not wanted or not shipped_models:
            return items

        for index in wanted:
            label = LEON_OUTFITS[index]
            model = shipped_models.get(index) or next(iter(shipped_models.values()))
            put(model, str(CHARACTER_DIR / f"pl{index}.udas.lfs"), label)
            pack = shipped_packs.get(index)
            if pack is None and len(shipped_packs) == 1:
                pack = next(iter(shipped_packs.values()))
            if pack is None:
                continue
            target = self._pack_target(game_dir, index)
            if target is None:
                continue
            put(pack, target, f"{label} textures")
        return items

    def apply_preview(self, skin: Skin, outfit_mode: str = "both") -> List[str]:
        """Readable plan for the apply dialog."""
        lines: List[str] = []
        for item in self.plan_apply(skin, outfit_mode):
            name = Path(item.target).name
            lines.append(f"{name}  ({item.label})" if item.label else name)
        return lines

    # -- add / delete --------------------------------------------------------
    def _looks_like_lfs(self, path: Path) -> bool:
        try:
            with open(path, "rb") as handle:
                return handle.read(4) in LFS_MAGICS
        except OSError:
            return False

    def _extract_zip(self, item: Path) -> List[SkinCandidate]:
        """Extract a .zip and return the candidate skin files inside it."""
        temp = self.config.root / "tmp_extract" / safe_slug(item.stem)
        temp.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(item) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(SKIN_FILE_SUFFIX) or name.lower().endswith(".udas"):
                        archive.extract(name, temp)
        except zipfile.BadZipFile as exc:
            raise SkinError(f"{item.name} is not a valid .zip archive: {exc}") from exc
        files = sorted(p for p in temp.rglob("*") if p.is_file() and p.suffix.lower() == SKIN_FILE_SUFFIX)
        if not files:
            # fall back to content detection (mod files that are not named *.lfs)
            files = sorted(p for p in temp.rglob("*") if p.is_file() and self._looks_like_lfs(p))
        return [SkinCandidate(path=p, rel_hint=str(p.relative_to(temp))) for p in files]

    def _collect_from_folder(self, folder: Path) -> List[SkinCandidate]:
        """All skin files inside a folder: .lfs anywhere, nested .zip archives,
        plus renamed files that contain an LFS archive."""
        found: List[SkinCandidate] = []
        found_keys = set()

        def remember(path: Path, rel_hint: Optional[str]) -> None:
            key = str(path).lower()
            if key not in found_keys:
                found_keys.add(key)
                found.append(SkinCandidate(path=path, rel_hint=rel_hint))

        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() == SKIN_FILE_SUFFIX:
                remember(path, str(path.relative_to(folder)))
        for archive in sorted(folder.rglob("*.zip")):
            try:
                extracted = self._extract_zip(archive)
            except SkinError:
                continue  # ignore broken zips inside folders
            for candidate in extracted:
                remember(candidate.path, candidate.rel_hint)
        # content detection, e.g. files named "pl00.udas" that are LFS archives
        scanned = 0
        for path in sorted(folder.rglob("*")):
            if scanned >= 5000:  # safety cap for huge trees
                break
            if not path.is_file() or str(path).lower() in found_keys:
                continue
            scanned += 1
            try:
                if path.stat().st_size < 8:
                    continue
            except OSError:
                continue
            if self._looks_like_lfs(path):
                remember(path, str(path.relative_to(folder)))
        return found

    def collect_candidates(self, selected: Sequence[Path]) -> List[SkinCandidate]:
        """Expand files, folders and .zip archives into import candidates."""
        out: List[SkinCandidate] = []
        for item in selected:
            item = Path(item)
            if item.is_dir():
                out.extend(self._collect_from_folder(item))
            elif item.suffix.lower() == ".zip":
                out.extend(self._extract_zip(item))
            elif item.is_file():
                out.append(SkinCandidate(path=item, rel_hint=None))
        # de-duplicate, keep order
        seen = set()
        unique: List[SkinCandidate] = []
        for candidate in out:
            key = str(candidate.path).lower()
            if key not in seen:
                seen.add(key)
                unique.append(candidate)
        return unique

    def collect_input_files(self, selected: Sequence[Path]) -> List[Path]:
        """Flat list of candidate files (convenience wrapper)."""
        return [candidate.path for candidate in self.collect_candidates(selected)]

    def add_skin(self, name: str, entries: Sequence[Tuple[Path, str]]) -> Skin:
        """Copy (source_file, game_relative_target) pairs into the library.

        Refuses to add files that are not .lfs, so the library can never fill
        up with files the game cannot load.
        """
        if not entries:
            raise SkinError("No files were selected.")
        skin_id = uuid.uuid4().hex[:12]
        # keep names unique - importing several folders all called "BIO4" is common
        existing = {s.name for s in self.library}
        unique_name = name
        counter = 2
        while unique_name in existing:
            unique_name = f"{name} ({counter})"
            counter += 1
        name = unique_name
        slug = safe_slug(name) or "skin"
        folder = self.config.skins_dir / f"{slug}_{skin_id[:6]}"
        folder.mkdir(parents=True, exist_ok=False)
        game_dir = self.get_game_dir()

        files: List[SkinFile] = []
        for source, target in entries:
            source = Path(source)
            ok, reason = self.validate_skin_payload(source)
            if not ok:
                raise SkinError(f"{source.name}: {reason}")
            if not target:
                raise SkinError(f"{source.name}: no install target was chosen.")
            target_path = Path(target)
            if target_path.is_absolute() or ".." in target_path.parts:
                raise SkinError(f"Invalid target path: {target}")
            stored_name = f"{len(files):03d}_{source.name}"
            stored_path = folder / stored_name
            copy_file(source, stored_path)
            files.append(
                SkinFile(
                    stored_name=stored_name,
                    target=str(target_path),
                    size=stored_path.stat().st_size,
                    sha256=sha256_file(stored_path),
                    source_name=source.name,
                )
            )
            if game_dir:
                self._log("info", f"Added {source.name} -> {target}")

        manifest = {
            "id": skin_id,
            "name": name,
            "created": now_iso(),
            "files": [asdict(f) for f in files],
        }
        (folder / "skin.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        skin = Skin(id=skin_id, name=name, created=manifest["created"], files=files)
        self.refresh()
        self._log("info", f"Skin '{name}' added to library ({len(files)} file(s)).")
        return skin

    def rename_skin(self, skin_id: str, name: str) -> None:
        """Change the display name of a skin (fixes duplicates like two 'BIO4' entries)."""
        name = (name or "").strip()
        if not name:
            raise SkinError("The name cannot be empty.")
        for folder in self.config.skins_dir.iterdir():
            manifest = folder / "skin.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("id") != skin_id:
                continue
            data["name"] = name
            manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.refresh()
            self._log("info", f"Skin renamed to '{name}'.")
            return
        raise SkinError("Skin files are missing from the library folder.")

    def delete_skin(self, skin_id: str) -> None:
        skin = self.get(skin_id)
        if not skin:
            return
        for folder in self.config.skins_dir.iterdir():
            manifest = folder / "skin.json"
            if not manifest.is_file():
                continue
            try:
                if json.loads(manifest.read_text(encoding="utf-8")).get("id") == skin_id:
                    shutil.rmtree(folder, ignore_errors=True)
                    break
            except Exception:
                continue
        state = self.config.load_state()
        if state.get("applied_skin") == skin_id:
            # keep applied_targets so a future skin swap can still revert these files
            state["applied_skin"] = ""
            self.config.save_state(state)
        self.refresh()
        self._log("info", f"Skin '{skin.name}' removed from library.")

    # -- backups -------------------------------------------------------------
    @staticmethod
    def _install_key(game_dir: Path) -> str:
        digest = hashlib.sha1(str(Path(game_dir).resolve()).lower().encode("utf-8")).hexdigest()
        return digest[:10]

    def _current_install_key(self) -> Optional[str]:
        game_dir = self.get_game_dir()
        if not game_dir:
            return None
        return self._install_key(game_dir)

    def _backup_root(self, install_key: str) -> Path:
        return self.config.game_backups_dir / install_key

    def _backup_manifest_path(self) -> Path:
        return self.config.game_backups_dir / "manifest.json"

    def _load_backup_manifest(self) -> Dict[str, Dict]:
        path = self._backup_manifest_path()
        manifest: Dict[str, Dict] = {}
        if path.exists():
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
        # migrate backups created before per-install storage existed
        if manifest and any("|" not in key for key in manifest) and self._legacy_install_dir:
            legacy_key = self._install_key(self._legacy_install_dir)
            migrated: Dict[str, Dict] = {}
            changed = False
            for key, entry in manifest.items():
                if "|" in key:
                    migrated[key] = entry
                    continue
                migrated[f"{legacy_key}|{key}"] = entry
                changed = True
                old_file = self.config.game_backups_dir / key
                if old_file.is_file():
                    destination = self._backup_root(legacy_key) / key
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(str(old_file), str(destination))
                    except OSError:
                        pass
            if changed:
                self._save_backup_manifest(migrated)
            return migrated
        return manifest

    def _save_backup_manifest(self, manifest: Dict[str, Dict]) -> None:
        self._backup_manifest_path().write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def backup_count(self) -> int:
        manifest = self._load_backup_manifest()
        install_key = self._current_install_key()
        if not install_key:
            return 0
        prefix = f"{install_key}|"
        return sum(1 for key in manifest if key.startswith(prefix))

    def _ensure_backup(self, game_dir: Path, target_rel: str) -> None:
        manifest = self._load_backup_manifest()
        install_key = self._install_key(game_dir)
        key = f"{install_key}|{target_rel}"
        if key in manifest:
            return
        live = game_dir / target_rel
        if not live.is_file():
            raise SkinError(f"Game file does not exist: {live}")
        stored = self._backup_root(install_key) / target_rel
        copy_file(live, stored)
        manifest[key] = {
            "backed_up_at": now_iso(),
            "size": live.stat().st_size,
            "sha256": sha256_file(live),
            "game_dir": str(game_dir),
        }
        self._save_backup_manifest(manifest)
        self._log("info", f"Original backed up: {target_rel}")

    # -- apply / restore -----------------------------------------------------
    def applied_skin(self) -> str:
        state = self.config.load_state()
        skin_id = state.get("applied_skin", "")
        if skin_id and self.get(skin_id):
            return skin_id
        return ""

    def _game_dir_or_raise(self) -> Path:
        game_dir = self.get_game_dir()
        if not game_dir or not game_dir.is_dir():
            raise SkinError("Game folder not found. Use 'Detect again' or browse for it.")
        return game_dir

    @staticmethod
    def _replace_file(source: Path, target: Path, rel: str) -> None:
        try:
            shutil.copy2(source, target)
        except PermissionError as exc:
            raise SkinError(
                f"Windows blocked replacing {rel} (the game may be using it).\n"
                "Close the game and try again."
            ) from exc
        except OSError as exc:
            raise SkinError(f"Could not replace {rel}: {exc}") from exc

    def apply_skin(self, skin_id: str, game_running: bool = False, outfit_mode: Optional[str] = None) -> str:
        skin = self.get(skin_id)
        if not skin:
            raise SkinError("Skin not found in library.")
        mode = outfit_mode or getattr(self.config.settings, "skin_outfit_mode", "both") or "both"
        if mode not in OUTFIT_MODES:
            mode = "both"
        if game_running:
            self._log(
                "warn",
                "Game is running - files swapped now. The new skin appears after the game "
                "reloads Leon (enter a new area, or die and continue).",
            )
        game_dir = self._game_dir_or_raise()
        items = self.plan_apply(skin, mode, game_dir)

        # verify all targets first and make sure every original is backed up
        for item in items:
            if not (game_dir / item.target).is_file():
                raise SkinError(
                    f"Missing game file: {item.target}\n"
                    "The skin target does not match this installation."
                )
            self._ensure_backup(game_dir, item.target)
            others = self._sibling_variants(game_dir, item.target)
            if others:
                self._log(
                    "warn",
                    f"{item.target}: this install also holds {', '.join(others)} (files left by an "
                    "older version of a mod). The trainer writes the file the skin ships; if the "
                    "skin still does not show up, those leftovers are the place to look.",
                )

        # full swap: restore any file the previous skin replaced that this skin
        # does not include, so switching skins never leaves leftovers behind
        state = self.config.load_state()
        new_targets = {item.target for item in items}
        previous_targets = set(state.get("applied_targets", []))
        install_key = self._install_key(game_dir)
        for target in sorted(previous_targets - new_targets):
            backup = self._backup_root(install_key) / target
            if backup.is_file():
                self._replace_file(backup, game_dir / target, target)
                self._log("info", f"Reverted {target} (not used by '{skin.name}')")

        applied = 0
        for item in items:
            source = self._skin_folder(skin) / item.stored_name
            live = game_dir / item.target
            if item.mirrored and source.is_file() and live.is_file():
                try:
                    if live.stat().st_size > source.stat().st_size * 3:
                        self._log(
                            "warn",
                            f"{item.target}: this skin's textures are much smaller than the ones "
                            "in your install - the skin may look lower resolution than your mod.",
                        )
                except OSError:
                    pass
            self._replace_file(source, live, item.target)
            applied += 1
            label = f"  [{item.label}]" if item.label else ""
            self._log("info", f"Replaced {item.target} with {item.source_name}{label}")

        state["applied_skin"] = skin_id
        state["applied_at"] = now_iso()
        state["applied_targets"] = sorted(new_targets)
        state["outfit_mode"] = mode
        self.config.save_state(state)
        self.config.settings.applied_skin = skin_id
        self.config.save()
        self._log("info", f"Skin '{skin.name}' applied ({applied} file(s), outfit: {mode}).")
        return skin.name

    def _skin_folder(self, skin: Skin) -> Path:
        for folder in self.config.skins_dir.iterdir():
            manifest = folder / "skin.json"
            if not manifest.is_file():
                continue
            try:
                if json.loads(manifest.read_text(encoding="utf-8")).get("id") == skin.id:
                    return folder
            except Exception:
                continue
        raise SkinError("Skin files are missing from the library folder.")

    def restore_original(self, game_running: bool = False) -> int:
        if game_running:
            self._log(
                "warn",
                "Game is running - originals restored on disk. They appear after the game "
                "reloads Leon (enter a new area, or die and continue).",
            )
        game_dir = self._game_dir_or_raise()
        manifest = self._load_backup_manifest()
        install_key = self._install_key(game_dir)
        prefix = f"{install_key}|"
        restored = 0
        for key in list(manifest.keys()):
            if not key.startswith(prefix):
                continue
            target_rel = key[len(prefix):]
            backup = self._backup_root(install_key) / target_rel
            if not backup.is_file():
                self._log("warn", f"Backup missing for {target_rel}, skipped.")
                continue
            self._replace_file(backup, game_dir / target_rel, target_rel)
            restored += 1
        state = self.config.load_state()
        state["applied_skin"] = ""
        state["applied_at"] = ""
        state["applied_targets"] = []
        self.config.save_state(state)
        self.config.settings.applied_skin = ""
        self.config.save()
        self._log("info", f"Original files restored ({restored} file(s)).")
        return restored
