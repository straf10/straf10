#!/usr/bin/env python3
"""Turn a photo into ascii.svg — a character-ramp portrait for the profile README.

Pipeline (see the ASCII Portrait README Guide + Part 1 fixes):
  1. rembg cut-out          — background → white → blank end of the ramp
  2. bilateral filter       — smooth skin, keep edges
  3. CLAHE (clip ≈ 3.0)     — local contrast so flat light still has shape
  4. darkening curve ^1.7   — the fix that keeps glasses / brows / lips
  5. map to 13-step ramp    — leading space clears the background

Geometry assumes JetBrains Mono's 0.600 em advance
(CHAR_W = 7.74 at font-size 12.9). After writing ascii.svg, run
embed_portrait_font.py so Windows viewers don't squeeze the grid.

Usage:
  python3 scripts/generate_portrait.py [path/to/photo.jpg]
"""
from __future__ import annotations

import math
import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(HERE, "source", "portrait.jpg")
OUT = os.path.join(ROOT, "ascii.svg")

# Display geometry — 90 columns at 460px wide in the README.
FS = 12.9
CHAR_W = 7.74          # 0.600 em * 12.9
LINE_H = 15.0
PAD = 14.0
COLS = 90
CURSOR_W = 6.0
LINE_DUR = 0.09
# Monospace glyphs are ~2× taller than wide → 0.48 row factor.
ROW_FACTOR = 0.48

# Quiet → loud. 13 brightness levels.
RAMP = " .`-:+=*cs#%@"


def prepare(path: str) -> np.ndarray:
    """Load → rembg → crop subject → bilateral → CLAHE → darkening curve."""
    with open(path, "rb") as f:
        cut = remove(f.read())  # PNG bytes, RGBA, bg removed
    rgba = np.array(Image.open(__import__("io").BytesIO(cut)).convert("RGBA"))

    # Tight crop to the opaque subject so tall phone photos don't leave a
    # giant empty margin that collapses the face to a few dozen characters.
    alpha_u8 = rgba[:, :, 3]
    ys, xs = np.where(alpha_u8 > 16)
    if len(xs) > 0:
        pad = 8
        y0, y1 = max(0, ys.min() - pad), min(rgba.shape[0], ys.max() + pad + 1)
        x0, x1 = max(0, xs.min() - pad), min(rgba.shape[1], xs.max() + pad + 1)
        rgba = rgba[y0:y1, x0:x1]

    # Composite onto white so the removed background maps to the blank ramp.
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    rgb = rgba[:, :, :3].astype(np.float32)
    comp = (rgb * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)

    grey = cv2.cvtColor(comp, cv2.COLOR_RGB2GRAY)
    grey = cv2.bilateralFilter(grey, d=9, sigmaColor=75, sigmaSpace=75)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    grey = clahe.apply(grey)

    # Darkening curve — without this the face washes out.
    v = grey.astype(np.float32) / 255.0
    grey = np.clip((v ** 1.7) * 255.0, 0, 255).astype(np.uint8)
    return grey


def sample_grid(grey: np.ndarray, cols: int) -> list[str]:
    h, w = grey.shape
    rows = max(1, int(round(cols * (h / w) * ROW_FACTOR)))

    # Cover-fit into cols×rows, crop overflow (slight upward bias for faces).
    scale = max(cols / w, rows / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    resized = cv2.resize(grey, (nw, nh), interpolation=cv2.INTER_AREA)
    left = max(0, (nw - cols) // 2)
    top = max(0, (nh - rows) // 5)
    crop = resized[top:top + rows, left:left + cols]
    if crop.shape != (rows, cols):
        crop = cv2.resize(crop, (cols, rows), interpolation=cv2.INTER_AREA)

    n = len(RAMP) - 1
    lines: list[str] = []
    for y in range(rows):
        chars = []
        for x in range(cols):
            # Dark → denser glyphs. White bg (255) → space.
            v = 255 - int(crop[y, x])
            idx = int(round((v / 255.0) * n))
            chars.append(RAMP[idx])
        lines.append("".join(chars).rstrip(" "))
    return lines


def escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def draw(lines: list[str]) -> str:
    max_len = max((len(l) for l in lines), default=1)
    width = int(math.ceil(PAD * 2 + max_len * CHAR_W + CURSOR_W + 8))
    height = int(math.ceil(PAD * 2 + len(lines) * LINE_H))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'
        f'&apos;Liberation Mono&apos;,monospace">'
        f'<style>.a{{fill:#6e7681}}'
        f'@media(prefers-color-scheme:dark){{.a{{fill:#c9d1d9}}}}</style>'
    ]

    for i, line in enumerate(lines):
        if not line:
            line = " "
        y = PAD + i * LINE_H
        text_y = y + FS - 1.7
        wipe = len(line) * CHAR_W
        delay = i * LINE_DUR
        end = delay + LINE_DUR
        parts.append(
            f'<clipPath id="c{i}"><rect x="{PAD:.0f}" y="{y:.0f}" '
            f'height="{LINE_H:.0f}" width="0">'
            f'<animate attributeName="width" from="0" to="{wipe:.1f}" '
            f'begin="{delay:.2f}s" dur="{LINE_DUR:.2f}s" fill="freeze"/>'
            f'</rect></clipPath>'
            f'<g clip-path="url(#c{i})">'
            f'<text xml:space="preserve" x="{PAD:.0f}" y="{text_y:.1f}" '
            f'class="a" font-size="{FS}">{escape(line)}</text></g>'
            f'<rect y="{y + 1:.0f}" width="{CURSOR_W:.0f}" height="12" '
            f'class="a" opacity="0">'
            f'<animate attributeName="x" from="{PAD:.0f}" '
            f'to="{PAD + wipe:.1f}" begin="{delay:.2f}s" '
            f'dur="{LINE_DUR:.2f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.8" begin="{delay:.2f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{end:.2f}s"/>'
            f'</rect>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.exists(src):
        sys.exit(f"missing source image: {src}")

    grey = prepare(src)
    lines = sample_grid(grey, COLS)
    svg = draw(lines)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{OUT}: {len(lines)}×{COLS} from {src} "
          f"({os.path.getsize(OUT)} bytes, ~{len(lines) * LINE_DUR:.1f}s type-on)")
    print("next: python3 scripts/embed_portrait_font.py")


if __name__ == "__main__":
    main()
