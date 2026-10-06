"""PyInstaller / direct-run entry point (keeps relative imports working)."""

from __future__ import annotations

from re4_trainer.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
