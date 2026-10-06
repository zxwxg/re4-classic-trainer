"""Game process discovery, memory reading/writing and in-process AOB scanning."""

from __future__ import annotations

import ctypes
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from . import winapi as w
from .pattern import Pattern

GAME_EXE_NAMES = ("bio4.exe",)


@dataclass
class ProcessInfo:
    pid: int
    name: str
    path: str


def list_processes() -> List[ProcessInfo]:
    out: List[ProcessInfo] = []
    snapshot = w.kernel32.CreateToolhelp32Snapshot(w.TH32CS_SNAPPROCESS, 0)
    if snapshot == w.INVALID_HANDLE_VALUE:
        return out
    try:
        entry = w.PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(w.PROCESSENTRY32W)
        ok = w.kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            out.append(ProcessInfo(entry.th32ProcessID, entry.szExeFile, ""))
            ok = w.kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        w.kernel32.CloseHandle(snapshot)
    return out


def find_game_processes(names: Tuple[str, ...] = GAME_EXE_NAMES) -> List[ProcessInfo]:
    lowered = {n.lower() for n in names}
    return [p for p in list_processes() if p.name.lower() in lowered]


def find_game_exe_path(names: Tuple[str, ...] = GAME_EXE_NAMES) -> str:
    """Full path of the running game executable ("" when the game is not running)."""
    for info in find_game_processes(names):
        try:
            proc = GameProcess(info.pid)
        except OSError:
            continue
        try:
            path = proc.exe_path()
        finally:
            proc.close()
        if path:
            return path
    return ""


def close_game_processes(names: Tuple[str, ...] = GAME_EXE_NAMES, grace: float = 4.0) -> int:
    """Close every running copy of the game: WM_CLOSE first, then terminate.

    Used after swapping skin files, because RE4 only reads Leon's model once per
    session - a clean restart is the only way to make the new skin show up.
    """
    infos = find_game_processes(names)
    if not infos:
        return 0
    for info in infos:
        try:
            proc = GameProcess(info.pid)
        except OSError:
            continue
        try:
            hwnd = proc.main_window()
            if hwnd:
                w.user32.PostMessageW(hwnd, w.WM_CLOSE, 0, 0)
        except Exception:
            pass
        finally:
            proc.close()
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not find_game_processes(names):
            return len(infos)
        time.sleep(0.25)
    for info in find_game_processes(names):
        try:
            proc = GameProcess(info.pid)
        except OSError:
            continue
        try:
            w.kernel32.TerminateProcess(proc.handle, 0)
        except Exception:
            pass
        finally:
            proc.close()
    time.sleep(0.8)
    return len(infos) if not find_game_processes(names) else 0


def launch_game(exe_path: str) -> bool:
    """Start the game again from its own folder (after a trainer-driven restart)."""
    if not exe_path or not Path(exe_path).is_file():
        return False
    folder = Path(exe_path).parent
    work = folder.parent if folder.name.lower() == "bin32" else folder
    try:
        subprocess.Popen([exe_path], cwd=str(work))
        return True
    except OSError:
        return False


class GameProcess:
    """An open handle to the game process with convenience helpers."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.handle = w.kernel32.OpenProcess(w.PROCESS_RIGHTS, False, pid)
        self._modules: Dict[str, Tuple[int, int]] = {}
        self._module_paths: Dict[str, str] = {}
        if not self.handle:
            raise OSError(
                f"OpenProcess failed for pid {pid} (error {ctypes.get_last_error()}). "
                "Try running the trainer as administrator."
            )

    # -- lifecycle -----------------------------------------------------------
    def close(self) -> None:
        if self.handle:
            w.kernel32.CloseHandle(self.handle)
            self.handle = None

    def is_alive(self) -> bool:
        if not self.handle:
            return False
        code = w.wintypes.DWORD(0)
        if not w.kernel32.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            return False
        return code.value == w.STILL_ACTIVE

    def __enter__(self) -> "GameProcess":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- raw memory ----------------------------------------------------------
    def read(self, address: int, size: int) -> Optional[bytes]:
        if not self.handle or size <= 0:
            return None
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        ok = w.kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(address), buf, size, ctypes.byref(read)
        )
        if not ok or read.value != size:
            return None
        return buf.raw[: read.value]

    def write(self, address: int, data: bytes) -> bool:
        if not self.handle:
            return False
        buf = ctypes.create_string_buffer(data, len(data))
        written = ctypes.c_size_t(0)
        ok = w.kernel32.WriteProcessMemory(
            self.handle, ctypes.c_void_p(address), buf, len(data), ctypes.byref(written)
        )
        return bool(ok) and written.value == len(data)

    # -- typed helpers (32-bit game) ----------------------------------------
    def read_u32(self, address: int) -> Optional[int]:
        raw = self.read(address, 4)
        return int.from_bytes(raw, "little") if raw else None

    def read_i16(self, address: int) -> Optional[int]:
        raw = self.read(address, 2)
        return int.from_bytes(raw, "little", signed=True) if raw else None

    def read_u16(self, address: int) -> Optional[int]:
        raw = self.read(address, 2)
        return int.from_bytes(raw, "little") if raw else None

    def write_u32(self, address: int, value: int) -> bool:
        return self.write(address, int(value & 0xFFFFFFFF).to_bytes(4, "little"))

    def write_i16(self, address: int, value: int) -> bool:
        return self.write(address, int(value).to_bytes(2, "little", signed=True))

    # -- modules -------------------------------------------------------------
    def refresh_modules(self) -> Dict[str, Tuple[int, int]]:
        modules: Dict[str, Tuple[int, int]] = {}
        paths: Dict[str, str] = {}
        snapshot = w.kernel32.CreateToolhelp32Snapshot(
            w.TH32CS_SNAPMODULE | w.TH32CS_SNAPMODULE32, self.pid
        )
        if snapshot == w.INVALID_HANDLE_VALUE:
            return modules
        try:
            entry = w.MODULEENTRY32W()
            entry.dwSize = ctypes.sizeof(w.MODULEENTRY32W)
            ok = w.kernel32.Module32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                base = int(entry.modBaseAddr or 0)
                key = entry.szModule.lower()
                modules[key] = (base, int(entry.modBaseSize))
                paths[key] = entry.szExePath
                ok = w.kernel32.Module32NextW(snapshot, ctypes.byref(entry))
        finally:
            w.kernel32.CloseHandle(snapshot)
        self._modules = modules
        self._module_paths = paths
        return modules

    def exe_path(self, name: str = "bio4.exe") -> str:
        """Full path of the running game executable (empty string if unknown)."""
        key = name.lower()
        if key not in self._modules:
            self.refresh_modules()
        return self._module_paths.get(key, "")

    def module_info(self, name: str) -> Optional[Tuple[int, int]]:
        key = name.lower()
        if key not in self._modules:
            self.refresh_modules()
        return self._modules.get(key)

    # -- scanning ------------------------------------------------------------
    def read_module(self, name: str, chunk_size: int = 1 << 20) -> Optional[bytes]:
        info = self.module_info(name)
        if not info:
            return None
        base, size = info
        parts: List[bytes] = []
        addr = base
        end = base + size
        while addr < end:
            n = min(chunk_size, end - addr)
            part = self.read(addr, n)
            if part is None:
                # try a smaller granularity before giving up on the chunk
                part = b""
                sub = 0x1000
                for off in range(0, n, sub):
                    piece = self.read(addr + off, min(sub, n - off))
                    if piece is None:
                        piece = b"\x00" * min(sub, n - off)
                    part += piece
            parts.append(part)
            addr += n
        return b"".join(parts)

    def scan_module(self, pattern: Union[str, Pattern], module: str = "bio4.exe") -> List[int]:
        """Return absolute addresses of every hit inside the module."""
        pat = pattern if isinstance(pattern, Pattern) else Pattern(pattern)
        data = self.read_module(module)
        if data is None:
            return []
        info = self.module_info(module)
        assert info is not None
        base = info[0]
        return [base + off for off in pat.find_all(data)]

    def scan_module_first(self, pattern: Union[str, Pattern], module: str = "bio4.exe") -> Optional[int]:
        hits = self.scan_module(pattern, module)
        return hits[0] if hits else None

    # -- windows -------------------------------------------------------------
    def main_window(self) -> Optional[int]:
        """Best-effort main window handle for this process (largest titled window)."""
        candidates: List[Tuple[int, int, int]] = []

        def _cb(hwnd, _lparam):
            pid = w.wintypes.DWORD(0)
            w.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != self.pid:
                return True
            if not w.user32.IsWindowVisible(hwnd):
                return True
            length = w.user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                w.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
            # prefer windows with a title; keep the first as fallback
            candidates.append((1 if title else 0, hwnd, length))
            return True

        try:
            w.user32.EnumWindows(w.WNDENUMPROC(_cb), 0)
        except Exception:
            return None
        if not candidates:
            return None
        titled = [c for c in candidates if c[0]]
        return (titled or candidates)[0][1]

    def focus_window(self) -> bool:
        hwnd = self.main_window()
        if not hwnd:
            return False
        if w.user32.IsIconic(hwnd):
            w.user32.ShowWindow(hwnd, w.SW_RESTORE)
        w.user32.SetForegroundWindow(hwnd)
        return True

    def client_size(self) -> Optional[Tuple[int, int]]:
        """Client area size of the game window (for UI coordinates)."""
        hwnd = self.main_window()
        if not hwnd:
            return None
        rect = w.wintypes.RECT()
        if not w.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        return rect.right - rect.left, rect.bottom - rect.top

    def send_key(self, vk: int, presses: int = 1, gap: float = 0.35, hold_ms: int = 60) -> int:
        """Focus the game window and press a virtual key `presses` times."""
        if not self.focus_window():
            return 0
        time.sleep(0.12)
        sent = 0
        for i in range(max(1, presses)):
            if w.tap_key(vk, hold_ms=hold_ms):
                sent += 1
            if i + 1 < presses:
                time.sleep(gap)
        return sent
