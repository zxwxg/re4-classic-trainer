"""Dump widget geometry of the main window (no interaction)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from re4_trainer.config import ConfigStore
from re4_trainer.ui.window import TrainerWindow


def dump(widget, depth: int = 0, max_depth: int = 4) -> None:
    for child in widget.winfo_children():
        pad = "  " * depth
        print(
            f"{pad}{child.__class__.__name__:22s} name={str(child.winfo_name()):18s} "
            f"xy=({child.winfo_x()},{child.winfo_y()}) size={child.winfo_width()}x{child.winfo_height()} "
            f"manager={child.winfo_manager()}"
        )
        if depth < max_depth:
            dump(child, depth + 1, max_depth)


def main() -> None:
    config = ConfigStore()
    app = TrainerWindow(config, admin=False)
    app.update()
    app.update_idletasks()
    print("=" * 100)
    dump(app, max_depth=3)
    app.after(200, app.destroy)
    app.mainloop()


if __name__ == "__main__":
    main()
