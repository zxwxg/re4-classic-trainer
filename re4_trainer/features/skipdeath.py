"""Skip Death engine.

Verified mechanics of the Steam re-release of RE4 (2005) / re4_tweaks:

* Leon's health lives in the global work struct: ``GLOBAL_WK.playerHpCur_4FB4``
  (int16) and ``playerHpMax_4FB6`` (int16).  The struct pointer is stored in a
  static variable that we find with the exact AOB patterns re4_tweaks uses.
* The game has a debug flag ``DBG_NO_DEATH2`` (bit 0x400 of ``flags_DEBUG_3``
  at GLOBAL_WK+0x6C).  re4_tweaks installs code patches that consult that flag
  every frame; turning the flag on gives real invulnerability (this is the
  same switch as re4_tweaks' in-game "Invulnerability" option).

Skip Death itself is an **instant respawn**: the health is polled at 250 Hz
while Leon is badly hurt, and the moment it would reach zero the trainer puts
it straight back to full.  Leon is revived where he stands - there is no death
animation, no "You are dead" screen and nothing is clicked for you.

Deaths the game commits on its own (traps, scripted deaths, falling out of the
world) cannot be cancelled that way, so a small safety net answers the death
prompt for those cases only.  It is a fallback, not the normal path.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from ..core.process import GameProcess, find_game_processes
from ..core.pattern import Pattern
from ..core import winapi as w

# AOB patterns (the same ones re4_tweaks uses for this game version)
PATTERN_GLOBALS = "A1 ?? ?? ?? ?? B9 FF FF FF 7F 21 48 ?? A1"   # pointer to GLOBAL_WK*
PATTERN_PLAYER = "A1 ?? ?? ?? ?? D8 CC D8 C9 D8 CA D9 5D ?? D9 45 ??"  # pointer to cPlayer*

OFF_HP_CUR = 0x4FB4
OFF_HP_MAX = 0x4FB6

OFF_FLAGS_DEBUG_3 = 0x6C
DBG_NO_DEATH2 = 0x400

VK_KEYS = {
    "RETURN": 0x0D,
    "SPACE": 0x20,
    "NUMPADENTER": 0x0D,
    "E": 0x45,
    "F": 0x46,
}

POLL_INTERVAL = 0.025          # 40 Hz health polling
FAST_POLL_INTERVAL = 0.004     # 250 Hz while Leon is hurt - catches the killing blow
RESCAN_INTERVAL = 1.5          # when the game isn't running
FLAG_REASSERT_INTERVAL = 0.5   # re-write the invulnerability bit every 0.5 s
DEATH_COOLDOWN = 8.0           # seconds between two auto-continues
RECENT_ALIVE_WINDOW = 5.0      # hp must have been > 0 recently before we revive
RESPAWN_SETTLE_SECONDS = 1.5   # time the game gets to accept an instant respawn
RESPAWN_RETRY_GAP = 0.02       # how often the health is re-asserted while reviving
CONTINUE_MAX_SECONDS = 30.0    # keep skipping until Leon respawns
CONTINUE_PRESS_GAP = 1.0
# The "Yes" choice on the mouse-only "Retry? Yes/No" prompt, as a fraction of
# the game's client area. The loop sweeps slightly around this point so small
# layout differences still land on "Yes" (and never on "No").
YES_X_FRACTION = 0.40
YES_Y_FRACTION = 0.70
YES_SWEEP = (0.0, -0.018, 0.018, -0.032, -0.008, 0.032)


@dataclass
class SkipDeathSnapshot:
    attached: bool = False
    pid: Optional[int] = None
    exe_path: str = ""
    hp: Optional[int] = None
    hp_max: Optional[int] = None
    re4_tweaks: bool = False
    invulnerability: bool = False
    protection: bool = False
    deaths_skipped: int = 0
    respawns: int = 0
    respawning: bool = False
    last_event: str = ""
    message: str = "Searching for Resident Evil 4..."
    globals_ptr: Optional[int] = None
    enabled: bool = False


class SkipDeathEngine:
    def __init__(self, log: Optional[Callable[[str, str], None]] = None) -> None:
        self._log = log or (lambda level, message: None)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._enabled = False
        self._protection = False
        self._continue_key = "RETURN"
        self._yes_x = YES_X_FRACTION
        self._yes_y = YES_Y_FRACTION
        self._proc: Optional[GameProcess] = None
        self._pG_static: Optional[int] = None
        self._pPL_static: Optional[int] = None
        self._exe_path: str = ""
        self._globals: Optional[int] = None

        self._re4_tweaks = False
        self._we_set_flag = False
        self._prev_flag_value: Optional[int] = None
        self._last_flag_write = 0.0

        self._armed = False
        self._last_positive = 0.0
        self._last_continue = 0.0
        self._last_revive = 0.0
        self._reviving = False
        self._revive_deadline = 0.0
        self._revive_writes = 0
        self._respawns = 0
        self._continuing = False
        self._deaths = 0
        self._last_rescan = 0.0
        self._last_event = ""
        self._message = "Searching for Resident Evil 4..."
        self._invulnerability = False

    # -- thread control ------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="skip-death", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None
        self._disable_flags()
        self._detach()

    # -- public API ----------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            if enabled == self._enabled:
                return
            self._enabled = enabled
            if not enabled:
                self._disable_flags()
                self._log("info", "Skip Death disabled.")
            else:
                self._log("info", "Skip Death enabled - instant respawn armed.")
                self._message = "Skip Death on - looking for the game..."

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_protection(self, enabled: bool) -> None:
        """Optional no-damage protection (health guard + re4_tweaks invulnerability)."""
        with self._lock:
            if enabled == self._protection:
                return
            self._protection = enabled
        if not enabled:
            self._disable_flags()
        self._log("info", f"Damage protection {'enabled' if enabled else 'disabled'}.")

    def set_continue_key(self, key: str) -> None:
        with self._lock:
            self._continue_key = key if key in VK_KEYS else "RETURN"

    def set_yes_position(self, x_fraction: float, y_fraction: float) -> None:
        """Position of the 'Yes' option on the death prompt (fractions 0..1)."""
        with self._lock:
            self._yes_x = min(0.95, max(0.05, float(x_fraction)))
            self._yes_y = min(0.95, max(0.05, float(y_fraction)))

    def heal_now(self) -> bool:
        with self._lock:
            proc, globals_ptr = self._proc, self._globals
            hp_max = None
            if proc and globals_ptr:
                hp_max = proc.read_i16(globals_ptr + OFF_HP_MAX)
            if proc and globals_ptr and hp_max:
                return proc.write_i16(globals_ptr + OFF_HP_CUR, hp_max)
        return False

    def snapshot(self) -> SkipDeathSnapshot:
        with self._lock:
            return SkipDeathSnapshot(
                attached=self._proc is not None and self._pG_static is not None,
                pid=self._proc.pid if self._proc else None,
                exe_path=self._exe_path,
                hp=self._hp,
                hp_max=self._hp_max,
                re4_tweaks=self._re4_tweaks,
                invulnerability=self._invulnerability,
                protection=self._protection,
                deaths_skipped=self._deaths,
                respawns=self._respawns,
                respawning=self._reviving,
                last_event=self._last_event,
                message=self._message,
                globals_ptr=self._globals,
                enabled=self._enabled,
            )

    # -- internals -----------------------------------------------------------
    _hp: Optional[int] = None
    _hp_max: Optional[int] = None

    def _poll_interval(self) -> float:
        """Poll fast whenever a killing blow is plausible, so we win the frame."""
        if self._reviving:
            return FAST_POLL_INTERVAL
        hp, hp_max = self._hp, self._hp_max
        if hp is not None and hp_max:
            if 0 < hp <= hp_max * 0.5:
                return FAST_POLL_INTERVAL
        return POLL_INTERVAL

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if self._proc is None or not self._proc.is_alive():
                    self._detach()
                    self._try_attach()
                if self._proc is not None:
                    self._tick()
            except Exception as exc:  # keep the worker alive no matter what
                self._message = f"Engine error: {exc}"
                self._log("error", f"Skip Death engine error: {exc}")
                self._detach()
            self._stop.wait(self._poll_interval())

    def _detach(self) -> None:
        if self._proc is not None:
            self._log("info", "Disconnected from the game.")
            self._proc.close()
        self._proc = None
        self._pG_static = None
        self._pPL_static = None
        self._globals = None
        self._re4_tweaks = False
        self._invulnerability = False
        self._we_set_flag = False
        self._prev_flag_value = None
        self._last_flag_write = 0.0
        self._exe_path = ""
        self._armed = False
        self._hp = None
        self._hp_max = None
        self._reviving = False
        self._message = "Searching for Resident Evil 4..."

    def _try_attach(self) -> None:
        now = time.monotonic()
        if now - self._last_rescan < RESCAN_INTERVAL:
            return
        self._last_rescan = now
        processes = find_game_processes()
        if not processes:
            return
        info = processes[0]
        try:
            proc = GameProcess(info.pid)
        except OSError as exc:
            self._message = f"Could not open the game process: {exc}"
            return
        module = proc.module_info("bio4.exe")
        if not module:
            self._message = "bio4.exe module not found yet, retrying..."
            proc.close()
            return
        data = proc.read_module("bio4.exe")
        if data is None:
            self._message = "Could not read the game's code. Run the trainer as administrator."
            proc.close()
            return
        globals_hit = Pattern(PATTERN_GLOBALS).find_first(data)
        player_hit = Pattern(PATTERN_PLAYER).find_first(data)
        base = module[0]
        if globals_hit is None:
            self._message = "Unsupported bio4.exe version (health pattern not found)."
            self._log("warn", "AOB pattern for GLOBAL_WK was not found - unsupported exe version?")
            proc.close()
            return
        self._proc = proc
        self._pG_static = base + globals_hit + 1
        self._pPL_static = base + player_hit + 1 if player_hit is not None else None
        self._re4_tweaks = proc.module_info("dinput8.dll") is not None
        self._exe_path = proc.exe_path() or ""
        self._message = f"Connected to bio4.exe (PID {info.pid})."
        self._log(
            "info",
            f"Connected to bio4.exe (PID {info.pid}). re4_tweaks: "
            f"{'detected' if self._re4_tweaks else 'not detected'}.",
        )
        self._armed = False
        self._last_positive = time.monotonic()

    def _write_flag_bit(self, value: bool) -> None:
        proc, globals_ptr = self._proc, self._globals
        if not proc or not globals_ptr:
            return
        current = proc.read_u32(globals_ptr + OFF_FLAGS_DEBUG_3)
        if current is None:
            return
        if value:
            new_value = current | DBG_NO_DEATH2
            if not (current & DBG_NO_DEATH2):
                self._we_set_flag = True
        else:
            if not self._we_set_flag:
                return
            new_value = current & ~DBG_NO_DEATH2
        if new_value != current:
            proc.write_u32(globals_ptr + OFF_FLAGS_DEBUG_3, new_value)
        self._prev_flag_value = new_value
        self._last_flag_write = time.monotonic()

    def _disable_flags(self) -> None:
        if self._we_set_flag:
            self._write_flag_bit(False)
            self._we_set_flag = False
            self._log("info", "re4_tweaks invulnerability flag cleared.")
        self._invulnerability = False

    def _tick(self) -> None:
        proc = self._proc
        if proc is None or self._pG_static is None:
            return
        # The AOB pattern matched `mov eax, [imm32]` inside the game's code.
        # imm32 is the address of a static `GLOBAL_WK*` variable, so it takes
        # two reads to get to the struct itself.
        gvar = proc.read_u32(self._pG_static)
        globals_ptr = proc.read_u32(gvar) if gvar and gvar > 0x10000 else None
        if not globals_ptr or globals_ptr < 0x10000:
            self._message = "Waiting for the game to initialise..."
            return
        self._globals = globals_ptr
        hp = proc.read_i16(globals_ptr + OFF_HP_CUR)
        hp_max = proc.read_i16(globals_ptr + OFF_HP_MAX)
        now = time.monotonic()

        with self._lock:
            enabled = self._enabled
            protection = self._protection
            key = self._continue_key
        self._hp = hp
        self._hp_max = hp_max

        # --- detect death while we still have the raw values -----------------
        if hp is not None and hp > 0:
            self._armed = True
            self._last_positive = now

        # --- instant respawn -------------------------------------------------
        # Leon keeps taking normal damage; the moment his health would reach zero
        # we put it straight back to full, so he is revived where he stands -
        # no death animation, no death screen, nothing clicked for him.
        if enabled and hp is not None and self._armed and hp <= 0 and not self._continuing:
            if now - self._last_positive <= RECENT_ALIVE_WINDOW:
                if not self._reviving:
                    self._armed = False
                    self._reviving = True
                    self._last_revive = now
                    self._revive_deadline = now + RESPAWN_SETTLE_SECONDS
                    self._revive_writes = 0
                    self._deaths += 1
                    self._last_event = "Health hit zero - respawning Leon"
                    self._log(
                        "warn",
                        "Health reached zero - instant respawn (no death screen, nothing clicked).",
                    )
                if hp_max and hp_max > 0:
                    self._last_revive = now
                    if proc.write_i16(globals_ptr + OFF_HP_CUR, hp_max):
                        self._revive_writes += 1

        # --- did the game take the respawn, or did the death commit? ---------
        if self._reviving:
            if hp is not None and hp > 0:
                self._reviving = False
                self._respawns += 1
                self._armed = True
                self._last_positive = now
                self._last_event = f"Instant respawn #{self._respawns}"
                self._log(
                    "info",
                    f"Instant respawn #{self._respawns} - Leon was revived in place "
                    f"({self._revive_writes} write(s)), no death screen.",
                )
            elif now >= self._revive_deadline:
                # deaths the game commits on its own (traps, scripted deaths)
                self._reviving = False
                self._continuing = True
                self._last_continue = now
                self._last_event = "Death committed - prompt fallback"
                self._log(
                    "warn",
                    "The game had already committed this death - using the death-prompt fallback.",
                )
                threading.Thread(target=self._auto_continue, args=(key,), daemon=True).start()

        # --- optional no-damage protection -----------------------------------
        if enabled and protection and proc is not None and globals_ptr:
            if self._re4_tweaks:
                stale = now - self._last_flag_write > FLAG_REASSERT_INTERVAL
                needs = self._prev_flag_value is None or not (self._prev_flag_value & DBG_NO_DEATH2)
                if stale or needs:
                    self._write_flag_bit(True)
                self._invulnerability = True
            else:
                self._invulnerability = False

            if hp is not None and hp_max is not None and hp_max > 0:
                if 0 < hp < hp_max:
                    proc.write_i16(globals_ptr + OFF_HP_CUR, hp_max)
                elif hp <= 0 and now - self._last_positive <= RECENT_ALIVE_WINDOW and now - self._last_revive >= 0.5:
                    # the game may not have committed the death yet - try to cancel it
                    proc.write_i16(globals_ptr + OFF_HP_CUR, hp_max)
                    self._last_revive = now
        else:
            self._invulnerability = False

    def _auto_continue(self, key: str) -> None:
        """Fallback for deaths the game commits by itself (traps, scripted deaths).

        The "Retry? Yes / No" death prompt is mouse-only (the keyboard cannot move
        the selection, and Enter picks the default "No").  So we shove the game's
        cursor to the top-left corner with raw relative input, move it onto "Yes"
        and click, until Leon respawns.  Normal deaths never reach this code -
        they are cancelled by the instant respawn above.
        """
        proc = self._proc
        if proc is None:
            self._continuing = False
            return
        try:
            if not proc.focus_window():
                self._log("warn", "Could not focus the game window for the death skip.")
                return
            size = proc.client_size()
            if not size:
                self._log("warn", "Could not read the game window size.")
                return
            width, height = size

            deadline = time.monotonic() + CONTINUE_MAX_SECONDS
            clicks = 0
            time.sleep(0.4)
            while time.monotonic() < deadline and not self._stop.is_set():
                with self._lock:
                    hp = self._hp
                if hp is not None and hp > 0:
                    break  # respawned
                offset = YES_SWEEP[clicks % len(YES_SWEEP)]
                click_x = int(width * (self._yes_x + offset))
                click_y = int(height * self._yes_y)
                # 1) shove the game cursor into the top-left corner
                w.move_mouse_relative(-4000, -4000, steps=40, delay=0.008)
                # 2) move it onto "Yes"
                w.move_mouse_relative(click_x, click_y, steps=60, delay=0.008)
                # 3) click it
                w.click_mouse_left()
                clicks += 1
                if self._stop.wait(CONTINUE_PRESS_GAP):
                    break
            self._log("info", f"Death skip: clicked Yes {clicks} time(s); checkpoint should be loading.")
        except Exception as exc:
            self._log("error", f"Death skip failed: {exc}")
        finally:
            self._continuing = False
