"""Dev tool: render the trainer UI off-screen-free and save screenshots of every page.

Run:  python tools/dev_shots.py [output_dir]
The window is non-elevated so a normal screen grab can capture it (no UAC prompt).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab  # noqa: E402

from re4_trainer.config import ConfigStore  # noqa: E402
from re4_trainer.ui.window import TrainerWindow  # noqa: E402

PAGES = ["overview", "skins", "checkpoint", "gameplay"]


def main() -> int:
    args = [a for a in sys.argv[1:] if a]
    out_dir = Path(args[0]) if args else ROOT / "tools" / "shots"
    palette = args[1] if len(args) > 1 else ""
    pages = args[2].split(",") if len(args) > 2 else PAGES
    out_dir.mkdir(parents=True, exist_ok=True)

    config = ConfigStore()
    if palette:
        config.settings.palette = palette
    win = TrainerWindow(config, admin=False)
    win.attributes("-topmost", True)
    win.geometry(config.settings.window_geometry)
    win.update()
    win.geometry("+40+40")          # always grab from the primary monitor corner
    win.lift()
    win.update()
    time.sleep(1.0)

    for page in pages:
        try:
            win._show_page(page)
        except Exception as exc:  # noqa: BLE001
            print(f"  page '{page}' failed: {exc}")
            continue
        win.update()
        time.sleep(0.6)
        win.lift()
        win.update()
        x, y = win.winfo_rootx(), win.winfo_rooty()
        w, h = win.winfo_width(), win.winfo_height()
        img = ImageGrab.grab(bbox=(x - 8, y - 40, x + w + 8, y + h + 8), all_screens=True)
        path = out_dir / f"{page}.png"
        img.save(path)
        print(f"  saved {path}  ({img.width}x{img.height})")

    win.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
