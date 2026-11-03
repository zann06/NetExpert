"""Generate screenshot previews from the example report PDF.

Run from the repository root:
    python scripts/make_report_previews.py

Produces:
    assets/screenshots/12-example-report-cover.png    (page 1)
    assets/screenshots/13-example-report-results.png  (page 5, forward chaining results)
    assets/screenshots/14-example-report-pages.png    (all 9 pages as a 3x3 contact sheet)
"""
import os

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "assets", "examples", "laporan-contoh.pdf")
OUT_DIR = os.path.join(ROOT, "assets", "screenshots")

SINGLES = {
    0: "12-example-report-cover.png",
    4: "13-example-report-results.png",
}
CONTACT_SHEET = "14-example-report-pages.png"


def main() -> None:
    doc = pymupdf.open(PDF)

    for page_index, name in SINGLES.items():
        pix = doc[page_index].get_pixmap(dpi=110)
        pix.save(os.path.join(OUT_DIR, name))
        print(f"saved {name} ({pix.width}x{pix.height})")

    thumbs = [page.get_pixmap(dpi=45) for page in doc]
    w, h = thumbs[0].width, thumbs[0].height
    gap = 24
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols

    canvas = pymupdf.Pixmap(
        pymupdf.csRGB,
        pymupdf.IRect(0, 0, cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap),
    )
    canvas.clear_with(243)  # light gray background

    for idx, pix in enumerate(thumbs):
        r, c = divmod(idx, cols)
        x = gap + c * (w + gap)
        y = gap + r * (h + gap)
        canvas.copy(pix, pymupdf.IRect(x, y, x + pix.width, y + pix.height))

    canvas.save(os.path.join(OUT_DIR, CONTACT_SHEET))
    print(f"saved {CONTACT_SHEET} ({canvas.width}x{canvas.height})")


if __name__ == "__main__":
    main()
