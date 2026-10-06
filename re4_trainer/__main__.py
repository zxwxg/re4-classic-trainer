"""Entry point: python -m re4_trainer"""

from __future__ import annotations

from .config import ConfigStore
from .core.winapi import is_admin
from .ui.window import TrainerWindow


def main() -> int:
    config = ConfigStore()
    window = TrainerWindow(config, admin=is_admin())
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
