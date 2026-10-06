"""Preview the Add Skin dialog with a fake mod folder (for manual layout checks)."""
from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from re4_trainer.config import ConfigStore
from re4_trainer.ui.skin_dialog import AddSkinDialog
from re4_trainer.ui.window import TrainerWindow


def main() -> None:
    config = ConfigStore()
    app = TrainerWindow(config, admin=False)
    temp = Path(tempfile.mkdtemp(prefix="re4trainer_preview_"))
    mod = temp / "MyLeonSkin"
    (mod / "Sub").mkdir(parents=True)
    (mod / "Extras").mkdir()
    (mod / "Sub" / "pl00.udas.lfs").write_bytes(b"RDLX" + b"preview" * 200)
    with zipfile.ZipFile(mod / "Extras" / "pack.zip", "w") as archive:
        archive.writestr("inner/pl01.udas.lfs", b"RDLX" + b"other" * 200)
    (mod / "renamed_leon_file").write_bytes(b"RDLX" + b"renamed" * 100)

    dialog = AddSkinDialog(app, app.skins, on_added=lambda skin: None)
    dialog.after(600, lambda: dialog._load_sources([mod]))
    app.after(25000, app.destroy)
    app.mainloop()


if __name__ == "__main__":
    main()
