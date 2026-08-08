"""Basic sanity tests that don't require a real PDF, Tesseract, or PaddleOCR install."""

import os
import tempfile

from pdf2docx_ocr.core.docx_builder import DocxBuilder
from pdf2docx_ocr.core.ocr_engine import OCRLine, OCRPageResult, OCRWord


def _make_word(text: str, left: int, top: int, width: int = 40, height: int = 20) -> OCRWord:
    return OCRWord(text=text, confidence=95.0, bbox=(left, top, width, height))


def test_ocr_line_joins_words_with_spaces():
    line = OCRLine(
        words=[_make_word("Hello", 0, 0), _make_word("world", 50, 0)],
        bbox=(0, 0, 90, 20),
    )
    assert line.text == "Hello world"


def test_docx_builder_groups_lines_into_paragraphs():
    close_line = OCRLine(words=[_make_word("Line one", 0, 0)], bbox=(0, 0, 100, 20))
    same_paragraph_line = OCRLine(words=[_make_word("Line two", 0, 22)], bbox=(0, 22, 100, 20))
    new_paragraph_line = OCRLine(words=[_make_word("Line three", 0, 90)], bbox=(0, 90, 100, 20))

    page_result = OCRPageResult(
        lines=[close_line, same_paragraph_line, new_paragraph_line],
        page_width=800,
        page_height=1000,
    )

    builder = DocxBuilder()
    builder.add_page(page_result, page_index=0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, "out.docx")
        builder.save(output_path)
        assert os.path.exists(output_path)

    paragraphs = [p.text for p in builder.document.paragraphs if p.text.strip()]
    assert any("Line one" in p and "Line two" in p for p in paragraphs)
    assert any(p.strip() == "Line three" for p in paragraphs)


def test_docx_builder_uses_native_text_when_available():
    builder = DocxBuilder()
    builder.add_page(page_result=None, page_index=0, native_text="Already digital text.")
    paragraphs = [p.text for p in builder.document.paragraphs if p.text.strip()]
    assert "Already digital text." in paragraphs
