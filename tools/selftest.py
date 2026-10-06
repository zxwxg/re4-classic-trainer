"""Offline self-tests: AOB patterns against the real exe + skins/checkpoint managers.

Run from the project root:  python tools/selftest.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from re4_trainer.config import ConfigStore  # noqa: E402
from re4_trainer.core.pattern import Pattern  # noqa: E402
from re4_trainer.features.checkpoint import CheckpointManager  # noqa: E402
from re4_trainer.features.skins import SkinManager  # noqa: E402

EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Resident Evil 4\Bin32\bio4.exe")

PATTERNS = {
    "globals_pG": "A1 ?? ?? ?? ?? B9 FF FF FF 7F 21 48 ?? A1",
    "player_pPL": "A1 ?? ?? ?? ?? D8 CC D8 C9 D8 CA D9 5D ?? D9 45 ??",
    "ashley_pAS": "A8 02 74 16 8B 15",
    "damage_pD": "8A 8B C3 4F 00 00 89 45 0C",
}


def test_patterns() -> None:
    assert EXE.exists(), f"bio4.exe not found at {EXE}"
    data = EXE.read_bytes()
    for name, pattern in PATTERNS.items():
        hits = Pattern(pattern).find_all(data, limit=10)
        assert hits, f"pattern {name} not found"
        print(f"  [ok] pattern {name}: {len(hits)} hit(s) @ {[hex(h) for h in hits[:3]]}")


def make_fake_game(root: Path) -> None:
    em = root / "BIO4" / "Em"
    em.mkdir(parents=True)
    (em / "pl00.udas.lfs").write_bytes(b"RDLX" + b"ORIGINAL-LEON-" + bytes(64))
    (em / "pl01.udas.lfs").write_bytes(b"RDLX" + b"ORIGINAL-ASHLEY-" + bytes(64))


def make_fake_game_with_outfits(root: Path) -> None:
    """A game folder shaped like the real one: Leon has two outfits, each with its own pack."""
    em = root / "BIO4" / "Em"
    hd = root / "BIO4" / "ImagePackHD"
    em.mkdir(parents=True)
    hd.mkdir(parents=True)
    for index in ("00", "08", "09", "19"):
        (em / f"pl{index}.udas.lfs").write_bytes(f"RDLXORIGINAL-MODEL-{index}".encode())
        (hd / f"010000{index}.pack.yz2.lfs").write_bytes(f"RDLXORIGINAL-TEX-{index}".encode())


def test_skins(tmp: Path) -> None:
    data_root = tmp / "appdata_skins"
    game = tmp / "game"
    make_fake_game(game)
    config = ConfigStore(data_root)
    config.settings.game_dir = str(game)
    manager = SkinManager(config, lambda: game, lambda level, msg: None)

    index = manager.game_file_index()
    auto = manager.auto_target("pl00.udas.lfs", index)
    assert auto and Path(auto).name == "pl00.udas.lfs", auto

    skin_one = tmp / "skin1.lfs"
    skin_one.write_bytes(b"RDLX" + b"SKIN-ONE-" + bytes(32))
    skin_two = tmp / "skin2.lfs"
    skin_two.write_bytes(b"RDLX" + b"SKIN-TWO-" + bytes(32))

    first = manager.add_skin("Skin One", [(skin_one, auto)])
    manager.apply_skin(first.id)
    live = game / "BIO4" / "Em" / "pl00.udas.lfs"
    assert live.read_bytes().startswith(b"RDLX" + b"SKIN-ONE"), "first skin not applied"
    install_key = manager._install_key(game)
    assert (config.game_backups_dir / install_key / Path(auto)).is_file(), "backup missing"

    second = manager.add_skin("Skin Two", [(skin_two, auto)])
    manager.apply_skin(second.id)
    assert live.read_bytes().startswith(b"RDLX" + b"SKIN-TWO"), "second skin not applied"

    restored = manager.restore_original()
    assert restored >= 1
    assert live.read_bytes().startswith(b"RDLX" + b"ORIGINAL-LEON"), "restore did not bring the original back"

    # invalid payload must be rejected
    bad = tmp / "bad.lfs"
    bad.write_bytes(b"NOT-AN-LFS-FILE")
    try:
        manager.add_skin("Bad", [(bad, auto)])
    except Exception as exc:
        print(f"  [ok] invalid skin rejected: {type(exc).__name__}")
    else:
        raise AssertionError("invalid skin file was accepted")

    print(f"  [ok] skins: add/apply/switch/restore + backups ({restored} restored)")


def test_folder_import(tmp: Path) -> None:
    """Folder selection: nested folders, nested .zip files, renamed files."""
    import zipfile

    game = tmp / "game_folder"
    make_fake_game(game)
    config = ConfigStore(tmp / "appdata_folder")
    config.settings.game_dir = str(game)
    manager = SkinManager(config, lambda: game, lambda level, msg: None)

    mod = tmp / "ModFolder"
    (mod / "Sub").mkdir(parents=True)
    (mod / "Extras").mkdir()
    (mod / "Sub" / "pl00.udas.lfs").write_bytes(b"RDLX" + b"FOLDER-SKIN-" + bytes(32))
    with zipfile.ZipFile(mod / "Extras" / "pack.zip", "w") as archive:
        archive.writestr("inner/pl01.udas.lfs", b"RDLX" + b"ZIP-SKIN-" + bytes(32))
    (mod / "renamed_no_ext").write_bytes(b"RDLX" + b"RENAMED-" + bytes(32))

    files = manager.collect_input_files([mod])
    names = sorted(p.name for p in files)
    assert names == ["pl00.udas.lfs", "pl01.udas.lfs", "renamed_no_ext"], names

    # content detection accepts renamed files
    ok, reason = manager.validate_skin_payload(mod / "renamed_no_ext")
    assert ok, reason

    # prefix matching: pl00.udas -> pl00.udas.lfs
    index = manager.game_file_index()
    target = manager.auto_target("pl00.udas", index)
    assert target and Path(target).name == "pl00.udas.lfs", target

    # adding a whole folder in one go
    entries = [(p, manager.auto_target(p.name, index)) for p in files[:2]]
    skin = manager.add_skin("Folder Skin", entries)
    assert skin.file_count == 2
    manager.apply_skin(skin.id)
    live = game / "BIO4" / "Em" / "pl00.udas.lfs"
    assert live.read_bytes().startswith(b"RDLX" + b"FOLDER-SKIN"), "folder skin not applied"
    manager.restore_original()
    assert live.read_bytes().startswith(b"RDLX" + b"ORIGINAL-LEON"), "folder skin restore failed"

    # relative-path targeting: same filename exists in two game folders
    pack = mod / "Pack"
    (pack / "ImagePackHD").mkdir(parents=True)
    (pack / "ImagePackHD" / "01000000.pack.yz2.lfs").write_bytes(b"RDLX" + b"HD-MOD-" + bytes(32))
    (game / "BIO4" / "ImagePack").mkdir(parents=True, exist_ok=True)
    (game / "BIO4" / "ImagePackHD").mkdir(parents=True, exist_ok=True)
    (game / "BIO4" / "ImagePack" / "01000000.pack.yz2.lfs").write_bytes(b"RDLX" + b"IP-ORIG-" + bytes(32))
    (game / "BIO4" / "ImagePackHD" / "01000000.pack.yz2.lfs").write_bytes(b"RDLX" + b"IPHD-ORIG-" + bytes(32))

    index = manager.game_file_index(refresh=True)
    candidates = manager.collect_candidates([pack])
    assert len(candidates) == 1
    hint = candidates[0].rel_hint
    target = manager.auto_target("01000000.pack.yz2.lfs", index, rel_hint=hint)
    assert target and "ImagePackHD" in target, target
    entry = (candidates[0].path, target)
    skin = manager.add_skin("HD Pack", [entry])
    manager.apply_skin(skin.id)
    applied = (game / "BIO4" / "ImagePackHD" / "01000000.pack.yz2.lfs").read_bytes()
    untouched = (game / "BIO4" / "ImagePack" / "01000000.pack.yz2.lfs").read_bytes()
    assert applied.startswith(b"RDLX" + b"HD-MOD-"), "HD pack not applied to ImagePackHD"
    assert untouched.startswith(b"RDLX" + b"IP-ORIG-"), "ImagePack file must stay untouched"
    manager.restore_original()
    assert (game / "BIO4" / "ImagePackHD" / "01000000.pack.yz2.lfs").read_bytes().startswith(b"RDLX" + b"IPHD-ORIG-")

    print("  [ok] folder import: nested folders, nested .zip, renamed files, prefix targets")
    print("  [ok] relative-path targeting picks the right game folder (ImagePackHD)")


def test_skin_swap(tmp: Path) -> None:
    """Switching skins must revert files the previous skin replaced but the new one does not."""
    game = tmp / "game_swap"
    make_fake_game(game)
    config = ConfigStore(tmp / "appdata_swap")
    config.settings.game_dir = str(game)
    manager = SkinManager(config, lambda: game, lambda level, msg: None)

    full = tmp / "full.lfs"
    full.write_bytes(b"RDLX" + b"FULL-LEON-" + bytes(32))
    small = tmp / "small.lfs"
    small.write_bytes(b"RDLX" + b"SMALL-LEON-" + bytes(32))

    skin_full = manager.add_skin("Full", [(full, "BIO4\\Em\\pl00.udas.lfs"), (full, "BIO4\\Em\\pl01.udas.lfs")])
    skin_small = manager.add_skin("Small", [(small, "BIO4\\Em\\pl00.udas.lfs")])

    manager.apply_skin(skin_full.id)
    assert (game / "BIO4" / "Em" / "pl01.udas.lfs").read_bytes().startswith(b"RDLX" + b"FULL-LEON")

    manager.apply_skin(skin_small.id)
    assert (game / "BIO4" / "Em" / "pl00.udas.lfs").read_bytes().startswith(b"RDLX" + b"SMALL-LEON")
    assert (game / "BIO4" / "Em" / "pl01.udas.lfs").read_bytes().startswith(b"RDLX" + b"ORIGINAL-ASHLEY"), (
        "file from the previous skin was not reverted"
    )
    print("  [ok] skin swap: files from the previous skin are reverted automatically")


def test_outfit_mirroring(tmp: Path) -> None:
    """A skin that only ships pl08 must still show up in a save that wears the normal outfit."""
    game = tmp / "game_outfits"
    make_fake_game_with_outfits(game)
    config = ConfigStore(tmp / "appdata_outfits")
    config.settings.game_dir = str(game)
    manager = SkinManager(config, lambda: game, lambda level, msg: None)

    model = tmp / "mafia.lfs"
    model.write_bytes(b"RDLX" + b"SKIN-MAFIA-MODEL" + bytes(32))
    pack = tmp / "pack.lfs"
    pack.write_bytes(b"RDLX" + b"SKIN-MAFIA-TEX" + bytes(32))
    skin = manager.add_skin(
        "Mafia only",
        [
            (model, "BIO4\\Em\\pl08.udas.lfs"),
            (pack, "BIO4\\ImagePackHD\\01000008.pack.yz2.lfs"),
        ],
    )

    manager.apply_skin(skin.id, outfit_mode="as_shipped")
    assert (game / "BIO4" / "Em" / "pl00.udas.lfs").read_bytes().startswith(b"RDLXORIGINAL-MODEL-00"), (
        "as_shipped mode must not touch the other outfit"
    )

    manager.apply_skin(skin.id, outfit_mode="both")
    normal_model = (game / "BIO4" / "Em" / "pl00.udas.lfs").read_bytes()
    normal_pack = (game / "BIO4" / "ImagePackHD" / "01000000.pack.yz2.lfs").read_bytes()
    assert normal_model.startswith(b"RDLX" + b"SKIN-MAFIA-MODEL"), (
        "the skin was not mirrored into the normal outfit model"
    )
    assert normal_pack.startswith(b"RDLX" + b"SKIN-MAFIA-TEX"), (
        "the skin's textures were not mirrored into the normal outfit pack"
    )
    assert (game / "BIO4" / "Em" / "pl09.udas.lfs").read_bytes().startswith(b"RDLXORIGINAL-MODEL-09"), (
        "mirroring must not touch other characters"
    )

    manager.apply_skin(skin.id, outfit_mode="normal")
    assert (game / "BIO4" / "Em" / "pl08.udas.lfs").read_bytes().startswith(b"RDLXORIGINAL-MODEL-08"), (
        "normal-only mode left the Mafia outfit swapped"
    )

    manager.restore_original()
    for index in ("00", "08"):
        assert (game / "BIO4" / "Em" / f"pl{index}.udas.lfs").read_bytes().startswith(
            f"RDLXORIGINAL-MODEL-{index}".encode()
        ), f"original pl{index} was not restored"
    print("  [ok] outfit mirroring: pl08-only skin reaches the normal outfit, restore is clean")


def test_checkpoint(tmp: Path) -> None:
    data_root = tmp / "appdata_checkpoint"
    saves = tmp / "saves"
    saves.mkdir()
    live = saves / "savegame00.sav"
    live.write_bytes(b"SAVE-V1-" + bytes(200))

    config = ConfigStore(data_root)
    config.settings.save_dir = str(saves)
    manager = CheckpointManager(config, lambda level, msg: None)

    status = manager.create()
    assert status.exists and status.file_count == 1, status

    live.write_bytes(b"SAVE-V2-" + bytes(120))
    result = manager.restore()
    assert live.read_bytes().startswith(b"SAVE-V1"), "save was not restored"
    assert Path(result["safety_backup"]).joinpath("savegame00.sav").is_file(), "safety backup missing"

    status = manager.status()
    assert status.exists and status.created
    print(f"  [ok] checkpoint: create/status/restore + safety backup ({result['safety_backup']})")


def main() -> int:
    print("== AOB patterns vs installed bio4.exe ==")
    test_patterns()
    with tempfile.TemporaryDirectory(prefix="re4trainer_test_") as temp:
        tmp = Path(temp)
        print("== skin manager (fake game folder) ==")
        test_skins(tmp)
        print("== folder import (folders / nested zips / renamed files) ==")
        test_folder_import(tmp)
        print("== skin swapping (revert leftover files) ==")
        test_skin_swap(tmp)
        print("== leon outfit mirroring (pl08-only skins) ==")
        test_outfit_mirroring(tmp)
        print("== checkpoint manager (fake save folder) ==")
        test_checkpoint(tmp)
    print("\nAll self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
