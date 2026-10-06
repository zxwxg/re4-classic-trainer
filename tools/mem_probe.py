"""Attach to a running bio4.exe and print the trainer's memory anchors.

Usage (run as administrator):  python tools/mem_probe.py

Useful to verify Skip Death support without the GUI.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from re4_trainer.core.pattern import Pattern
from re4_trainer.core.process import GameProcess, find_game_processes
from re4_trainer.features.skipdeath import (
    DBG_NO_DEATH2,
    OFF_FLAGS_DEBUG_3,
    OFF_HP_CUR,
    OFF_HP_MAX,
    PATTERN_GLOBALS,
    PATTERN_PLAYER,
)


def main() -> int:
    processes = find_game_processes()
    if not processes:
        print("bio4.exe is not running. Start the game first.")
        return 1
    info = processes[0]
    print(f"Found {info.name} (PID {info.pid})")
    with GameProcess(info.pid) as proc:
        module = proc.module_info("bio4.exe")
        if not module:
            print("bio4.exe module not found (is it a different exe?)")
            return 1
        base, size = module
        print(f"Module base: {base:#010x}  size: {size:#x}")
        data = proc.read_module("bio4.exe")
        if data is None:
            print("Could not read module memory - run as administrator.")
            return 1
        globals_hit = Pattern(PATTERN_GLOBALS).find_first(data)
        player_hit = Pattern(PATTERN_PLAYER).find_first(data)
        print(f"GLOBAL_WK pattern: {('found at ' + hex(base + globals_hit)) if globals_hit is not None else 'NOT FOUND'}")
        print(f"cPlayer pattern:   {('found at ' + hex(base + player_hit)) if player_hit is not None else 'NOT FOUND'}")
        if globals_hit is None:
            print("Unsupported bio4.exe build.")
            return 1
        pG_static = base + globals_hit + 1
        print("Sampling health (Ctrl+C to stop)...")
        for _ in range(10):
            gvar = proc.read_u32(pG_static)
            globals_ptr = proc.read_u32(gvar) if gvar and gvar > 0x10000 else None
            if globals_ptr and globals_ptr > 0x10000:
                hp = proc.read_i16(globals_ptr + OFF_HP_CUR)
                hp_max = proc.read_i16(globals_ptr + OFF_HP_MAX)
                flags = proc.read_u32(globals_ptr + OFF_FLAGS_DEBUG_3) or 0
                # harmless write test: write the same value back
                write_ok = hp is None or proc.write_i16(globals_ptr + OFF_HP_CUR, hp)
                print(
                    f"  pG var @{gvar:#010x} -> GLOBAL_WK={globals_ptr:#010x}  hp={hp}/{hp_max}  "
                    f"DBG_NO_DEATH2={'on' if flags & DBG_NO_DEATH2 else 'off'}  write_ok={write_ok}"
                )
            else:
                print(f"  pG var @{gvar if gvar else 0:#010x} -> globals not initialised yet (main menu / loading?)")
            time.sleep(0.5)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
