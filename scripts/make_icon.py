"""Generate the Hammurabi app icon (flat, sharp, on-brand).

A black field, a sharp accent border (no rounding), and a bold monospace "H".
Reuses the dashboard palette/font so the icon matches the app.

Run:  .venv/bin/python scripts/make_icon.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from render import ACCENT, BG, COLOR_RESIDENT, _font  # noqa: E402

W = 256


def main() -> int:
    im = Image.new("RGB", (W, W), BG)
    d = ImageDraw.Draw(im)
    # sharp border (flat, no radius)
    d.rectangle([6, 6, W - 7, W - 7], outline=ACCENT, width=3)
    # bold centred H
    d.text((W // 2, W // 2 - 6), "H", fill=ACCENT, font=_font(190, bold=True), anchor="mm")
    # a couple of pixel accents nodding to the city map
    for x, y, c in ((34, 34, COLOR_RESIDENT), (W - 44, W - 44, COLOR_RESIDENT)):
        d.rectangle([x, y, x + 8, y + 8], fill=c)

    out = Path(__file__).resolve().parents[1] / "assets" / "hammurabi.png"
    out.parent.mkdir(exist_ok=True)
    im.save(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
