"""Build the trainer icon from the Dule Server avatar (packaging/icon.ico).

Uses packaging/dule_avatar.png when present; otherwise draws a simple fallback.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "packaging" / "dule_avatar.png"
OUT = ROOT / "packaging" / "icon.ico"


def circular(image: Image.Image) -> Image.Image:
    """Make sure the logo sits on a transparent circular base."""
    w, h = image.size
    corners = (
        image.getpixel((2, 2))[3],
        image.getpixel((w - 3, 2))[3],
        image.getpixel((2, h - 3))[3],
        image.getpixel((w - 3, h - 3))[3],
    )
    if min(corners) < 10:
        return image  # already transparent around the circle
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w - 1, h - 1), fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(image, (0, 0), mask)
    return out


def fallback_icon() -> Image.Image:
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([6, 6, size - 6, size - 6], radius=54, fill=(17, 20, 26, 255),
                           outline=(210, 69, 63, 255), width=7)
    font = None
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, 104)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    draw.text((size / 2, size / 2), "RE4", font=font, fill=(236, 239, 244, 255), anchor="mm")
    return img


def main() -> None:
    if SRC.is_file():
        image = Image.open(SRC).convert("RGBA")
        image = circular(image)
        print("icon source:", SRC)
    else:
        image = fallback_icon()
        print("icon source: built-in fallback (dule_avatar.png not found)")

    image.thumbnail((256, 256), Image.LANCZOS)
    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    canvas.paste(image, ((256 - image.width) // 2, (256 - image.height) // 2), image)
    canvas.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon written:", OUT)


if __name__ == "__main__":
    main()
