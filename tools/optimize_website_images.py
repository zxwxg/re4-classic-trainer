"""Shrink the website images so one visit costs a fraction of the bandwidth."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

IMG = Path(r"C:\Users\nasse\OneDrive\Desktop\New folder\RE4ClassicTrainer\website\assets\img")


def save_webp(path: Path, target: Path, size: int, quality: int = 82) -> None:
    image = Image.open(path).convert("RGBA" if path.suffix.lower() == ".png" else "RGB")
    image.thumbnail((size, size), Image.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    if image.mode == "RGBA" and target.suffix.lower() not in (".webp",):
        image = image.convert("RGB")
    image.save(target, quality=quality, method=6)
    print(f"  {target.name:<26} {target.stat().st_size/1024:>7.0f} KB  ({image.size[0]}px)")


print("hero badge")
save_webp(IMG / "dule-badge.png", IMG / "dule-badge.webp", 760, 84)
save_webp(IMG / "dule-badge.png", IMG / "dule-badge.png", 760, 84)          # PNG fallback, smaller

print("nav / footer badge")
save_webp(IMG / "dule-badge-512.png", IMG / "dule-badge-512.webp", 128, 86)
save_webp(IMG / "dule-badge-512.png", IMG / "dule-badge-512.png", 128, 86)

print("favicon")
save_webp(IMG / "icon.png", IMG / "icon.png", 96, 88)

print("social preview (jpg, only crawlers read it)")
art = Image.open(IMG / "dule-keyart.png").convert("RGB")
art.thumbnail((900, 900), Image.LANCZOS)
art.save(IMG / "dule-keyart.jpg", quality=85, optimize=True)
print(f"  dule-keyart.jpg            {(IMG / 'dule-keyart.jpg').stat().st_size/1024:>7.0f} KB  ({art.size[0]}px)")
(IMG / "dule-keyart.png").unlink(missing_ok=True)

print("app screenshots")
for name in ("app-overview", "app-skins", "app-gameplay", "app-checkpoint"):
    save_webp(IMG / f"{name}.png", IMG / f"{name}.webp", 1220, 84)
    (IMG / f"{name}.png").unlink(missing_ok=True)

print("dropping unused assets")
for name in ("dule-avatar.png", "icon-umbrella.png", "steam-avatar.png"):
    (IMG / name).unlink(missing_ok=True)
    print(f"  removed {name}")

total = sum(p.stat().st_size for p in IMG.rglob("*") if p.is_file())
print(f"\nimages folder total: {total/1024/1024:.2f} MB")
