"""Locating the Steam install, the game folder and the save (Steam Cloud) folder."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import winreg  # type: ignore
except ImportError:  # pragma: no cover - non-Windows dev environments
    winreg = None  # type: ignore

GAME_APPID = "254700"
GAME_DIR_NAME = "Resident Evil 4"
GAME_EXE = Path("Bin32") / "bio4.exe"
SAVE_GLOB = "savegame*.sav"


def _clean_path(text: str) -> Path:
    return Path(text.replace("\\\\", "\\"))


def steam_root_from_registry() -> Optional[Path]:
    if winreg is None:
        return None
    attempts = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]
    for hive, key, value in attempts:
        try:
            with winreg.OpenKey(hive, key) as handle:
                data, _ = winreg.QueryValueEx(handle, value)
                path = Path(data)
                if path.exists():
                    return path
        except OSError:
            continue
    return None


def candidate_steam_roots() -> List[Path]:
    roots: List[Path] = []
    reg = steam_root_from_registry()
    if reg:
        roots.append(reg)
    for base in ("C:/Program Files (x86)", "C:/Program Files", "D:/", "E:/", "F:/"):
        root = Path(base) / "Steam"
        if root.exists():
            roots.append(root)
    # de-duplicate, keep order
    seen = set()
    unique: List[Path] = []
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def steam_libraries(steam_root: Path) -> List[Path]:
    libraries: List[Path] = [steam_root]
    vdf = steam_root / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        text = vdf.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            path = _clean_path(match.group(1))
            if path.exists() and path not in libraries:
                libraries.append(path)
    return libraries


def find_game_install(steam_roots: Optional[Iterable[Path]] = None) -> Optional[Path]:
    roots = list(steam_roots) if steam_roots else candidate_steam_roots()
    for root in roots:
        for library in steam_libraries(root):
            candidate = library / "steamapps" / "common" / GAME_DIR_NAME
            if (candidate / GAME_EXE).exists():
                return candidate
            # sometimes installed with a slightly different name
            common = library / "steamapps" / "common"
            if common.is_dir():
                try:
                    for folder in common.iterdir():
                        if folder.is_dir() and "resident evil 4" in folder.name.lower():
                            if (folder / GAME_EXE).exists():
                                return folder
                except OSError:
                    pass
    return None


def active_steam_id(steam_root: Path) -> Optional[str]:
    login = steam_root / "config" / "loginusers.vdf"
    if not login.exists():
        return None
    text = login.read_text(encoding="utf-8", errors="replace")
    most_recent = None
    for match in re.finditer(r'"(\d{15,20})"\s*\{([^}]*)\}', text, re.S):
        steam_id, block = match.groups()
        if re.search(r'"MostRecent"\s*"1"', block):
            most_recent = steam_id
    return most_recent


def find_save_dirs(steam_roots: Optional[Iterable[Path]] = None) -> List[Path]:
    """All userdata 254700\\remote folders that contain savegame*.sav."""
    roots = list(steam_roots) if steam_roots else candidate_steam_roots()
    found: List[Path] = []
    for root in roots:
        userdata = root / "userdata"
        if not userdata.is_dir():
            continue
        try:
            for user in userdata.iterdir():
                remote = user / GAME_APPID / "remote"
                if remote.is_dir() and any(remote.glob(SAVE_GLOB)):
                    if remote not in found:
                        found.append(remote)
        except OSError:
            continue
    return found


def newest_save_mtime(save_dir: Path) -> float:
    newest = 0.0
    try:
        for file in save_dir.glob(SAVE_GLOB):
            newest = max(newest, file.stat().st_mtime)
    except OSError:
        pass
    return newest


def resolve_save_dir(preferred: str = "", steam_roots: Optional[Iterable[Path]] = None) -> Optional[Path]:
    """Pick the save folder: explicit preference first, otherwise the active user's."""
    if preferred:
        path = Path(preferred)
        if path.is_dir() and any(path.glob(SAVE_GLOB)):
            return path
    roots = list(steam_roots) if steam_roots else candidate_steam_roots()
    candidates = find_save_dirs(roots)
    if not candidates:
        return None
    for root in roots:
        steam_id = active_steam_id(root)
        if steam_id:
            wanted = (root / "userdata" / steam_id / GAME_APPID / "remote").resolve()
            for candidate in candidates:
                if candidate.resolve() == wanted:
                    return candidate
    return max(candidates, key=newest_save_mtime)


@dataclass
class GamePaths:
    steam_root: Optional[Path] = None
    game_dir: Optional[Path] = None
    save_dir: Optional[Path] = None
    save_dirs: List[Path] = field(default_factory=list)


def discover(preferred_game_dir: str = "", preferred_save_dir: str = "") -> GamePaths:
    result = GamePaths()
    game = Path(preferred_game_dir) if preferred_game_dir else None
    if not game or not (game / GAME_EXE).exists():
        game = find_game_install()
    result.game_dir = game
    result.steam_root = steam_root_from_registry()
    if result.steam_root is None and game:
        # derive from the library folder: <lib>/steamapps/common/Resident Evil 4
        try:
            result.steam_root = game.parents[2]
        except IndexError:
            result.steam_root = None
    roots = [result.steam_root] if result.steam_root else None
    result.save_dirs = find_save_dirs(roots)
    result.save_dir = resolve_save_dir(preferred_save_dir, roots)
    return result
