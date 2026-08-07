"""Generate small local sample PDFs for manual / integration testing."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image, ImageDraw


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    samples = root / "samples"
    samples.mkdir(exist_ok=True)

    digital_path = samples / "digital_layout_sample.pdf"
    scan_path = samples / "scanned_image_only_sample.pdf"
    mixed_path = samples / "mixed_digital_and_scanned.pdf"

    _write_digital(digital_path)
    _write_scanned(scan_path)
    _write_mixed(digital_path, scan_path, mixed_path)

    for path in (digital_path, scan_path, mixed_path):
        print(f"{path} ({path.stat().st_size} bytes)")


def _write_digital(path: Path) -> None:
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Layout Test Document", fontsize=22, fontname="helv")
    page.insert_text(
        (72, 110),
        "Digital page with text and an embedded image.",
        fontsize=12,
        fontname="helv",
    )
    body = (
        "This paragraph is native PDF text. The converter should keep it editable "
        "and place the figure below in approximate reading order.\n\n"
        "Second paragraph sits under the first with a larger gap."
    )
    page.insert_textbox(fitz.Rect(72, 140, 540, 260), body, fontsize=11, fontname="helv")

    img = Image.new("RGB", (320, 160), (40, 110, 180))
    draw = ImageDraw.Draw(img)
    draw.rectangle((20, 20, 300, 140), outline=(255, 220, 80), width=4)
    draw.text((40, 70), "SAMPLE FIGURE", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page.insert_image(fitz.Rect(72, 280, 392, 440), stream=buf.getvalue())
    page.insert_text(
        (72, 460),
        "Caption: sample figure under the paragraphs.",
        fontsize=10,
        fontname="helv",
    )

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((72, 72), "Page 2 - Columns and Table", fontsize=18, fontname="helv")
    left = "Left column line one.\nLeft column line two.\nLeft column line three."
    right = "Right column line one.\nRight column line two.\nRight column line three."
    page2.insert_textbox(fitz.Rect(72, 110, 280, 220), left, fontsize=11, fontname="helv")
    page2.insert_textbox(fitz.Rect(320, 110, 540, 220), right, fontsize=11, fontname="helv")

    y0 = 280
    rows = [
        ["Name", "Qty", "Notes"],
        ["Alpha", "3", "Blue"],
        ["Beta", "12", "Green"],
        ["Gamma", "7", "Red"],
    ]
    col_x = [72, 220, 320, 520]
    row_h = 24
    for r, row in enumerate(rows):
        y = y0 + r * row_h
        for c, cell in enumerate(row):
            page2.insert_text((col_x[c] + 6, y + 16), cell, fontsize=11, fontname="helv")
        page2.draw_line((col_x[0], y), (col_x[-1], y), color=(0, 0, 0), width=0.7)
    page2.draw_line(
        (col_x[0], y0 + len(rows) * row_h),
        (col_x[-1], y0 + len(rows) * row_h),
        color=(0, 0, 0),
        width=0.7,
    )
    for x in col_x:
        page2.draw_line((x, y0), (x, y0 + len(rows) * row_h), color=(0, 0, 0), width=0.7)

    doc.save(path)
    doc.close()


def _write_scanned(path: Path) -> None:
    scan_img = Image.new("RGB", (850, 1100), (245, 245, 240))
    d = ImageDraw.Draw(scan_img)
    d.rectangle((40, 40, 810, 1060), outline=(30, 30, 30), width=2)
    d.text((60, 80), "SCANNED SAMPLE PAGE", fill=(20, 20, 20))
    d.text((60, 130), "This page has no PDF text layer.", fill=(20, 20, 20))
    d.text((60, 170), "OCR should recover these lines.", fill=(20, 20, 20))
    d.text((60, 210), "A figure region is below.", fill=(20, 20, 20))
    d.ellipse((120, 300, 620, 620), fill=(200, 80, 60), outline=(20, 20, 20), width=3)
    d.rectangle((150, 700, 680, 900), fill=(70, 140, 90))
    d.text((200, 780), "GREEN BLOCK IMAGE", fill=(255, 255, 255))

    scan_buf = io.BytesIO()
    scan_img.save(scan_buf, format="JPEG", quality=85)
    scan_doc = fitz.open()
    scan_page = scan_doc.new_page(width=612, height=792)
    scan_page.insert_image(scan_page.rect, stream=scan_buf.getvalue())
    scan_doc.save(path, deflate=True, garbage=4)
    scan_doc.close()


def _write_mixed(digital_path: Path, scan_path: Path, mixed_path: Path) -> None:
    mixed = fitz.open()
    digital = fitz.open(digital_path)
    scanned = fitz.open(scan_path)
    mixed.insert_pdf(digital, from_page=0, to_page=0)
    mixed.insert_pdf(scanned, from_page=0, to_page=0)
    mixed.save(mixed_path)
    mixed.close()
    digital.close()
    scanned.close()


if __name__ == "__main__":
    main()
