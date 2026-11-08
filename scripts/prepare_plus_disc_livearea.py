#!/usr/bin/env python3
"""Fit the supplied Plus Disc artwork to the Vita's required asset dimensions."""
import argparse
from pathlib import Path
from PIL import Image, ImageOps


def save(image, path):
    image.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                  dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)
    if path.stat().st_size > 420 * 1024:
        raise ValueError(f"LiveArea asset exceeds the size limit: {path}")
    print(f"{path.name}: {image.width}x{image.height}, {path.stat().st_size} bytes")


def panel(art, logo, size):
    width, height = size
    scaled = ImageOps.contain(art, (width, height), Image.Resampling.LANCZOS)
    # Preserve the complete landscape illustration. Its unused lower space
    # becomes a matching blue title band containing the supplied logo.
    color = logo.convert("RGB").getpixel((logo.width - 1, logo.height - 1))
    canvas = Image.new("RGB", size, color)
    canvas.paste(scaled, ((width - scaled.width) // 2, 0))
    free = height - scaled.height
    title = ImageOps.contain(logo, (int(width * 0.88), max(1, free - 8)),
                             Image.Resampling.LANCZOS)
    canvas.paste(title, ((width - title.width) // 2,
                        scaled.height + (free - title.height) // 2), title)
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icon", type=Path, required=True)
    parser.add_argument("--background", type=Path, required=True)
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("assets/plus-disc-livearea"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with Image.open(args.icon) as source:
        icon = ImageOps.exif_transpose(source).convert("RGB")
        save(ImageOps.fit(icon, (128, 128), Image.Resampling.LANCZOS), args.output / "icon0.png")
    with Image.open(args.background) as source, Image.open(args.logo) as title:
        art = ImageOps.exif_transpose(source).convert("RGB")
        logo = title.convert("RGBA")
        for name, size in (("bg.png", (840, 500)), ("startup.png", (280, 158))):
            save(panel(art, logo, size), args.output / name)


if __name__ == "__main__":
    main()
