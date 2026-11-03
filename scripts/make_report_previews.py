"""Generate screenshot previews from the example report PDF.

Run from the repository root:
    python scripts/make_report_previews.py

Requires: pymupdf and pillow (both are already dependencies of the app).

Produces:
    assets/screenshots/12-example-report-cover.png    (page 1)
    assets/screenshots/13-example-report-results.png  (page 5, forward chaining results)
    assets/screenshots/14-example-report-pages.png    (all 9 pages, 5x2 contact sheet)
"""
import os

import pymupdf
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "assets", "examples", "laporan-contoh.pdf")
OUT_DIR = os.path.join(ROOT, "assets", "screenshots")

SINGLES = {
    0: "12-example-report-cover.png",
    4: "13-example-report-results.png",
}
CONTACT_SHEET = "14-example-report-pages.png"

BG = (243, 244, 246)  # light gray canvas
BORDER = (209, 213, 219)
FG = (55, 65, 81)  # page number label


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def main() -> None:
    doc = pymupdf.open(PDF)

    for page_index, name in SINGLES.items():
        pix = doc[page_index].get_pixmap(dpi=110)
        pix.save(os.path.join(OUT_DIR, name))
        print(f"saved {name} ({pix.width}x{pix.height})")

    # Contact sheet: 5 columns x 2 rows so the result is landscape and
    # stays compact when GitHub renders it full-width.
    thumbs = [
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        for pix in (page.get_pixmap(dpi=45) for page in doc)
    ]
    cols = 5
    gap = 24
    label_h = 34
    w, h = thumbs[0].size
    rows = (len(thumbs) + cols - 1) // cols
    sheet_w = cols * w + (cols + 1) * gap
    sheet_h = rows * (h + label_h) + (rows + 1) * gap

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)
    font = load_font(22)

    for idx, thumb in enumerate(thumbs):
        r, c = divmod(idx, cols)
        x = gap + c * (w + gap)
        y = gap + r * (h + label_h + gap)
        draw.rectangle([x - 1, y - 1, x + w, y + h], outline=BORDER)
        sheet.paste(thumb, (x, y))

        label = str(idx + 1)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (x + (w - tw) / 2 - bbox[0], y + h + (label_h - th) / 2 - bbox[1]),
            label,
            fill=FG,
            font=font,
        )

    sheet.save(os.path.join(OUT_DIR, CONTACT_SHEET))
    print(f"saved {CONTACT_SHEET} ({sheet_w}x{sheet_h})")


if __name__ == "__main__":
    main()
