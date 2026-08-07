"""Tests for layout reading-order helpers."""

from pdf2docx_ocr.core.layout_model import BBox, TextBlock, sort_reading_order


def _text(label: str, x0: float, y0: float, x1: float, y1: float) -> TextBlock:
    return TextBlock(text=label, bbox=BBox(x0, y0, x1, y1))


def test_sort_reading_order_simple_top_then_left():
    elements = [
        _text("b", 200, 10, 300, 30),
        _text("a", 10, 10, 100, 30),
        _text("c", 10, 50, 100, 70),
    ]
    ordered = sort_reading_order(elements, page_width=400)
    assert [e.text for e in ordered] == ["a", "b", "c"]


def test_sort_reading_order_two_columns():
    # Narrow left/right columns: left column should be fully read before right.
    elements = [
        _text("R1", 220, 10, 300, 30),
        _text("L1", 10, 10, 120, 30),
        _text("R2", 220, 50, 300, 70),
        _text("L2", 10, 50, 120, 70),
        _text("L3", 10, 90, 120, 110),
        _text("R3", 220, 90, 300, 110),
    ]
    ordered = sort_reading_order(elements, page_width=400)
    assert [e.text for e in ordered] == ["L1", "L2", "L3", "R1", "R2", "R3"]


def test_bbox_overlaps_fraction():
    a = BBox(0, 0, 100, 100)
    b = BBox(50, 0, 150, 100)
    assert abs(a.overlaps_fraction(b) - 0.5) < 1e-6
