"""Tests for LayoutDocxBuilder — no OCR binary required."""

import os
import tempfile
import zipfile

from PIL import Image

from pdf2docx_ocr.core.layout_docx_builder import LayoutDocxBuilder
from pdf2docx_ocr.core.layout_model import BBox, ImageBlock, PageLayout, TableBlock, TextBlock


def test_layout_docx_builder_writes_text_image_and_table():
    image = Image.new("RGB", (80, 40), color=(30, 120, 200))
    layout = PageLayout(
        page_index=0,
        width=600,
        height=800,
        elements=[
            TextBlock(text="Title block", bbox=BBox(40, 40, 400, 70), font_size_hint=16),
            ImageBlock(image=image, bbox=BBox(40, 90, 280, 170)),
            TableBlock(
                rows=[["A", "B"], ["1", "2"]],
                bbox=BBox(40, 200, 300, 280),
            ),
            TextBlock(text="Footer note", bbox=BBox(40, 320, 300, 350)),
        ],
    )

    builder = LayoutDocxBuilder(dpi=150)
    builder.add_page(layout)

    paragraphs = [p.text for p in builder.document.paragraphs if p.text.strip()]
    assert "Title block" in paragraphs
    assert "Footer note" in paragraphs
    assert len(builder.document.tables) == 1
    assert builder.document.tables[0].cell(0, 0).text == "A"
    assert builder.document.tables[0].cell(1, 1).text == "2"

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, "layout.docx")
        builder.save(output_path)
        assert os.path.isfile(output_path)

        # DOCX is a zip; media folder should contain the embedded image.
        with zipfile.ZipFile(output_path) as zf:
            media = [n for n in zf.namelist() if n.startswith("word/media/")]
            assert media, "expected at least one embedded image in word/media/"


def test_layout_docx_builder_page_break_between_pages():
    builder = LayoutDocxBuilder(dpi=150)
    page1 = PageLayout(
        page_index=0,
        width=500,
        height=700,
        elements=[TextBlock(text="Page one", bbox=BBox(10, 10, 200, 40))],
    )
    page2 = PageLayout(
        page_index=1,
        width=500,
        height=700,
        elements=[TextBlock(text="Page two", bbox=BBox(10, 10, 200, 40))],
    )
    builder.add_page(page1)
    builder.add_page(page2)

    texts = [p.text for p in builder.document.paragraphs if p.text.strip()]
    assert "Page one" in texts
    assert "Page two" in texts
