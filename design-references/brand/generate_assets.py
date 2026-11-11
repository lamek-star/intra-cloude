"""
One-shot brand-asset extraction for the IntraForge rebrand.

Source: design-references/brand/source/logo-original.jpg (a lockup —
cloud/network-nodes icon + "intraforge" wordmark — on a near-white
background, no alpha channel).

This script does NOT redraw or restyle the mark. It only:
  1. Removes the white background via alpha de-matting (standard
     "unblend from known background color" math), preserving the
     original stroke/gradient pixels and their anti-aliased edges.
  2. Crops the icon-only region out of the full lockup.
  3. Produces a dark-background wordmark variant by remapping only the
     near-black wordmark ink to white -- the icon's blue/green gradient
     is left untouched, since it already reads fine on a dark navy
     ground (confirmed by eye against DESIGN.md's --chrome-from/-to
     navy tokens).
  4. Resizes the icon into every size this app actually needs
     (favicon .ico, PWA manifest icons, Windows app/installer icon).

Run: python design-references/brand/generate_assets.py
"""

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "design-references/brand/source/logo-original.jpg"
OUT = ROOT / "design-references/brand/generated"
OUT.mkdir(parents=True, exist_ok=True)


def de_matte_white(rgb: np.ndarray) -> np.ndarray:
    """rgb: (H,W,3) uint8 array on a white background -> (H,W,4) RGBA
    with the white background removed. Standard matte-removal: observed
    = alpha*fg + (1-alpha)*white, solved for fg given alpha estimated
    from how far each pixel already is from pure white."""
    rgb = rgb.astype(np.float64)
    alpha = 255.0 - rgb.min(axis=2)  # 0 where pixel is pure white
    alpha = np.clip(alpha, 0, 255)
    a_norm = np.where(alpha > 0, alpha / 255.0, 1.0)[..., None]
    fg = (rgb - (1 - a_norm) * 255.0) / a_norm
    fg = np.clip(fg, 0, 255)
    out = np.dstack([fg, alpha]).astype(np.uint8)
    return out


def content_bbox(alpha: np.ndarray, threshold: int = 8) -> tuple[int, int, int, int]:
    mask = alpha > threshold
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def main():
    src = Image.open(SRC).convert("RGB")
    arr = np.array(src)
    rgba = de_matte_white(arr)

    full_alpha = rgba[..., 3]
    x0, y0, x1, y1 = content_bbox(full_alpha)
    print("full content bbox:", (x0, y0, x1, y1))

    # Find the icon/wordmark gap: scan columns within the content bbox
    # for a run of near-zero-alpha columns -- that's the space between
    # the icon and the wordmark.
    col_has_content = (full_alpha[:, x0:x1] > 8).any(axis=0)
    gap_start = None
    for i, has in enumerate(col_has_content):
        if not has and gap_start is None:
            # only count as a real gap if it's more than a stray few px
            run_len = 0
            j = i
            while j < len(col_has_content) and not col_has_content[j]:
                j += 1
                run_len += 1
            if run_len > 15:
                gap_start = i
                gap_end = j
                break
    if gap_start is None:
        raise RuntimeError("couldn't find icon/wordmark gap; inspect image manually")
    icon_x1 = x0 + gap_start
    word_x0 = x0 + gap_end
    print("icon spans", (x0, icon_x1), "wordmark spans", (word_x0, x1))

    full_img = Image.fromarray(rgba, "RGBA")

    # --- Full lockup, transparent bg, light-surface version ---
    lockup_light = full_img.crop((x0, y0, x1, y1))
    lockup_light.save(OUT / "intraforge-lockup-light.png")

    # --- Icon only, square-padded, transparent bg ---
    icon_crop = full_img.crop((x0, y0, icon_x1, y1))
    iw, ih = icon_crop.size
    side = max(iw, ih)
    pad = int(side * 0.08)
    canvas = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
    canvas.paste(icon_crop, ((canvas.width - iw) // 2, (canvas.height - ih) // 2), icon_crop)
    canvas.save(OUT / "intraforge-icon.png")
    print("icon-only canvas size:", canvas.size)

    # --- Wordmark only, transparent bg (light-surface version, navy ink) ---
    word_crop = full_img.crop((word_x0, y0, x1, y1))
    word_crop.save(OUT / "intraforge-wordmark-light.png")

    # --- Dark-background wordmark: remap near-black ink to near-white,
    # preserve alpha (anti-aliasing) exactly. Threshold chosen from the
    # sampled ink color (~ (4,6,29)) with headroom for AA blending. ---
    word_arr = np.array(word_crop)
    r, g, b, a = word_arr[..., 0], word_arr[..., 1], word_arr[..., 2], word_arr[..., 3]
    ink_mask = (r < 90) & (g < 90) & (b < 110)
    word_dark = word_arr.copy()
    word_dark[..., 0][ink_mask] = 248
    word_dark[..., 1][ink_mask] = 250
    word_dark[..., 2][ink_mask] = 252
    Image.fromarray(word_dark, "RGBA").save(OUT / "intraforge-wordmark-dark.png")

    # --- Full lockup, dark-background version (icon untouched + white wordmark) ---
    lockup_dark = full_img.crop((x0, y0, x1, y1)).copy()
    ld_arr = np.array(lockup_dark)
    # word_x0/x1 relative to the lockup crop's own coordinate space
    rel_word_x0 = word_x0 - x0
    region = ld_arr[:, rel_word_x0:]
    rr, gg, bb = region[..., 0], region[..., 1], region[..., 2]
    m = (rr < 90) & (gg < 90) & (bb < 110)
    region[..., 0][m] = 248
    region[..., 1][m] = 250
    region[..., 2][m] = 252
    Image.fromarray(ld_arr, "RGBA").save(OUT / "intraforge-lockup-dark.png")

    # --- Icon-color sample report (for design-token accuracy) ---
    icon_arr = np.array(icon_crop)
    ia = icon_arr[..., 3]
    ys, xs = np.where(ia > 200)  # fully-opaque stroke pixels only
    # leftmost 10% (blue end) vs rightmost 10% (green end) of the icon's
    # opaque pixels, sampled by x position
    xs_sorted_idx = np.argsort(xs)
    n = len(xs_sorted_idx)
    left_idx = xs_sorted_idx[: max(1, n // 20)]
    right_idx = xs_sorted_idx[-max(1, n // 20) :]

    def avg_color(idx):
        px = icon_arr[ys[idx], xs[idx], :3]
        return tuple(int(v) for v in px.mean(axis=0))

    print("icon gradient LEFT (blue end) avg RGB:", avg_color(left_idx))
    print("icon gradient RIGHT (green end) avg RGB:", avg_color(right_idx))

    # --- Icon raster sizes (favicon / manifest / windows) ---
    sizes = [16, 24, 32, 48, 64, 96, 128, 180, 192, 256, 512]
    icon_master = canvas  # square, padded
    for s in sizes:
        resized = icon_master.resize((s, s), Image.LANCZOS)
        resized.save(OUT / f"icon-{s}.png")

    # --- favicon.ico (multi-size) ---
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    icon_master.save(
        OUT / "favicon.ico",
        sizes=[(s, s) for s in ico_sizes],
    )

    print("done. outputs in", OUT)


if __name__ == "__main__":
    main()
