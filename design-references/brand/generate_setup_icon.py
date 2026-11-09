"""
The IntraForge Setup icon: the brand mark (generated/icon-512.png, never redrawn) with a small "install" badge -- a
brand-blue circle with a white download arrow -- so IntraForge-Setup.exe is never mistaken for the installed app.

At 16 and 24 px a badge would be an unreadable smudge, so those sizes are the plain mark (the same rule Windows' own
setup icons follow). Every size is drawn at 4x and reduced, and the .ico stores each size as its own PNG.

Run: python design-references/brand/generate_setup_icon.py
"""

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MARK = ROOT / "design-references/brand/generated/icon-512.png"
OUT_ICO = ROOT / "scripts/shop-kit/setup-stub/setup.ico"
OUT_PNG = ROOT / "design-references/brand/generated/setup-icon-256.png"
SIZES = (256, 128, 64, 48, 32, 24, 16)
BRAND = (37, 99, 235, 255)  # DESIGN.md --color-brand-600
SS = 4  # supersampling


def badge(canvas: Image.Image) -> None:
    w = canvas.width
    r = round(w * 0.18)  # badge radius
    ring = max(SS * 2, round(w * 0.028))
    cx, cy = w - r - ring // 2, w - r - ring // 2
    d = ImageDraw.Draw(canvas)
    d.ellipse((cx - r - ring, cy - r - ring, cx + r + ring, cy + r + ring), fill=(255, 255, 255, 255))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BRAND)
    s = round(r * 0.16)  # stroke width
    white = (255, 255, 255, 255)
    # the arrow: a shaft and a head, then a tray
    top, tip = cy - r * 0.52, cy + r * 0.18
    d.line((cx, top, cx, tip), fill=white, width=s)
    head = r * 0.34
    d.line((cx - head, tip - head, cx, tip), fill=white, width=s)
    d.line((cx + head, tip - head, cx, tip), fill=white, width=s)
    for x, y in ((cx - head, tip - head), (cx + head, tip - head), (cx, tip), (cx, top)):
        d.ellipse((x - s / 2, y - s / 2, x + s / 2, y + s / 2), fill=white)
    tray_y, tray_w = cy + r * 0.52, r * 0.56
    d.line((cx - tray_w, tray_y, cx + tray_w, tray_y), fill=white, width=s)
    for x in (cx - tray_w, cx + tray_w):
        d.ellipse((x - s / 2, tray_y - s / 2, x + s / 2, tray_y + s / 2), fill=white)


def render(size: int) -> Image.Image:
    big = size * SS
    mark = Image.open(MARK).convert("RGBA").resize((big, big), Image.LANCZOS)
    if size >= 32:
        badge(mark)
    return mark.resize((size, size), Image.LANCZOS)


def write_ico(images: list[Image.Image], path: Path) -> None:
    blobs = []
    for im in images:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        blobs.append(buf.getvalue())
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for im, blob in zip(images, blobs):
        dim = 0 if im.width >= 256 else im.width
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(header + entries + b"".join(blobs))


if __name__ == "__main__":
    images = [render(s) for s in SIZES]
    write_ico(images, OUT_ICO)
    images[0].save(OUT_PNG)
    print(f"{OUT_ICO} ({OUT_ICO.stat().st_size:,} bytes, sizes {', '.join(map(str, SIZES))})")
