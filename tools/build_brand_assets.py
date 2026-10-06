"""Build the website/app brand assets from the DULE key art."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SRC = Path(r"C:\Users\nasse\OneDrive\Desktop\New folder\ChatGPT Image Oct 5, 2026, 08_02_08 PM.png")
OUT = Path(r"C:\Users\nasse\OneDrive\Desktop\New folder\RE4ClassicTrainer\website\assets\img")
PACK = Path(r"C:\Users\nasse\OneDrive\Desktop\New folder\RE4ClassicTrainer\packaging")
OUT.mkdir(parents=True, exist_ok=True)

art = Image.open(SRC).convert("RGB")
side = art.size[0]

# ---------------------------------------------------------------- full key art
art.resize((1100, 1100), Image.LANCZOS).save(OUT / "dule-keyart.png", optimize=True)
print("dule-keyart.png", "1100x1100")

# --------------------------------------------------- circular badge (the ring)
# The red ring sits slightly above centre in the source picture.
box = (int(side * 0.028), int(side * 0.012), int(side * 0.982), int(side * 0.966))
circle = art.crop(box).resize((1024, 1024), Image.LANCZOS)
mask = Image.new("L", (1024, 1024), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 1023, 1023), fill=255)
badge = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
badge.paste(circle, (0, 0), mask)
badge.save(OUT / "dule-badge.png", optimize=True)
print("dule-badge.png 1024x1024")
badge.resize((512, 512), Image.LANCZOS).save(OUT / "dule-badge-512.png", optimize=True)

# --------------------------------------------------------- umbrella emblem icon
# Square crop around the Umbrella logo for small sizes (favicon / exe icon).
u_side = int(side * 0.245)
u_cx, u_cy = int(side * 0.500), int(side * 0.442)
u_box = (u_cx - u_side // 2, u_cy - u_side // 2, u_cx + u_side // 2, u_cy + u_side // 2)
emblem = art.crop(u_box).resize((512, 512), Image.LANCZOS)
emblem.save(OUT / "icon-umbrella.png", optimize=True)
print("icon-umbrella.png 512x512")


def app_icon(size: int) -> Image.Image:
    """Dark disc + red ring + umbrella: reads well even at 32 px."""
    canvas = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    s = canvas.size[0]
    draw.ellipse((0, 0, s - 1, s - 1), fill=(11, 12, 16, 255))
    ring = max(3, s // 26)
    draw.ellipse((0, 0, s - 1, s - 1), outline=(224, 58, 47, 255), width=ring)
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((ring, ring, s - ring, s - ring), outline=(224, 58, 47, 110), width=ring * 2)
    glow = glow.filter(ImageFilter.GaussianBlur(s // 40))
    canvas = Image.alpha_composite(canvas, glow)
    inner = int(s * 0.74)
    emblem_small = emblem.resize((inner, inner), Image.LANCZOS).convert("RGBA")
    mask_small = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(mask_small).ellipse((0, 0, inner - 1, inner - 1), fill=255)
    canvas.paste(emblem_small, ((s - inner) // 2, (s - inner) // 2), mask_small)
    return canvas.resize((size, size), Image.LANCZOS)


sizes = [16, 24, 32, 48, 64, 128, 256]
frames = [app_icon(s) for s in sizes]
frames[-1].save(PACK / "icon.ico", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
print("packaging/icon.ico rebuilt")
frames[-1].save(OUT / "icon.png")
print("icon.png 256x256")
