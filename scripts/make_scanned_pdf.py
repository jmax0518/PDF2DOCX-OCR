"""Rasterize digital PDFs into image-only 'scanned' PDFs for OCR testing."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def rasterize_pdf(
    input_path: Path,
    output_path: Path,
    dpi: int = 200,
    max_pages: int | None = 3,
    jpeg_quality: int = 85,
) -> None:
    src = fitz.open(input_path)
    out = fitz.open()
    page_count = src.page_count if max_pages is None else min(src.page_count, max_pages)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for i in range(page_count):
        page = src.load_page(i)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        # JPEG keeps scanned-PDF size manageable
        img_bytes = pix.tobytes("jpeg", jpg_quality=jpeg_quality)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=img_bytes)

    out.save(output_path, deflate=True, garbage=4)
    out.close()
    src.close()
    print(f"Wrote {output_path} ({page_count} pages, {dpi} DPI)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--suffix", default="_scanned")
    args = parser.parse_args()

    for path in args.inputs:
        out = path.with_name(f"{path.stem}{args.suffix}.pdf")
        rasterize_pdf(path, out, dpi=args.dpi, max_pages=args.max_pages)


if __name__ == "__main__":
    main()
