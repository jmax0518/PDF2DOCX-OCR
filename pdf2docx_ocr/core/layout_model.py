"""Unified page-layout model for hybrid digital + OCR conversion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from PIL import Image


@dataclass(frozen=True)
class BBox:
    """Axis-aligned box in page-pixel space (origin top-left)."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def mid_x(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def mid_y(self) -> float:
        return (self.y0 + self.y1) / 2.0

    def area(self) -> float:
        return self.width * self.height

    def iou(self, other: "BBox") -> float:
        ix0 = max(self.x0, other.x0)
        iy0 = max(self.y0, other.y0)
        ix1 = min(self.x1, other.x1)
        iy1 = min(self.y1, other.y1)
        iw = max(0.0, ix1 - ix0)
        ih = max(0.0, iy1 - iy0)
        inter = iw * ih
        if inter <= 0:
            return 0.0
        union = self.area() + other.area() - inter
        return inter / union if union > 0 else 0.0

    def overlaps_fraction(self, other: "BBox") -> float:
        """Fraction of this box covered by intersection with other."""
        area = self.area()
        if area <= 0:
            return 0.0
        ix0 = max(self.x0, other.x0)
        iy0 = max(self.y0, other.y0)
        ix1 = min(self.x1, other.x1)
        iy1 = min(self.y1, other.y1)
        inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
        return inter / area


@dataclass
class TextBlock:
    text: str
    bbox: BBox
    font_size_hint: Optional[float] = None


@dataclass
class ImageBlock:
    image: Image.Image
    bbox: BBox


@dataclass
class TableBlock:
    rows: List[List[str]]
    bbox: BBox


LayoutElement = Union[TextBlock, ImageBlock, TableBlock]


@dataclass
class PageLayout:
    page_index: int
    width: float
    height: float
    elements: List[LayoutElement] = field(default_factory=list)

    def sorted_elements(self) -> List[LayoutElement]:
        return sort_reading_order(self.elements, self.width)


def sort_reading_order(
    elements: List[LayoutElement], page_width: float
) -> List[LayoutElement]:
    """Sort layout elements into approximate reading order.

    Uses a light two-column heuristic: when enough narrow left/right blocks
    exist, read left column top-to-bottom, then right column. Otherwise sort
    by top then left.
    """
    if not elements:
        return []

    if page_width <= 0:
        return sorted(elements, key=lambda e: (e.bbox.y0, e.bbox.x0))

    mid = page_width * 0.5
    left = [e for e in elements if e.bbox.mid_x < mid]
    right = [e for e in elements if e.bbox.mid_x >= mid]

    if len(left) >= 2 and len(right) >= 2:
        left_narrow = sum(1 for e in left if e.bbox.x1 < page_width * 0.62) >= len(left) * 0.7
        right_narrow = sum(1 for e in right if e.bbox.x0 > page_width * 0.38) >= len(right) * 0.7
        if left_narrow and right_narrow:
            return sorted(left, key=lambda e: (e.bbox.y0, e.bbox.x0)) + sorted(
                right, key=lambda e: (e.bbox.y0, e.bbox.x0)
            )

    return sorted(elements, key=lambda e: (e.bbox.y0, e.bbox.x0))


def merge_overlapping_boxes(boxes: List[BBox], iou_threshold: float = 0.15) -> List[BBox]:
    """Greedily merge boxes that overlap above ``iou_threshold``."""
    if not boxes:
        return []

    remaining = sorted(boxes, key=lambda b: b.area(), reverse=True)
    merged: List[BBox] = []

    while remaining:
        current = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            next_remaining: List[BBox] = []
            for other in remaining:
                if current.iou(other) >= iou_threshold or current.overlaps_fraction(other) >= 0.5:
                    current = BBox(
                        min(current.x0, other.x0),
                        min(current.y0, other.y0),
                        max(current.x1, other.x1),
                        max(current.y1, other.y1),
                    )
                    changed = True
                else:
                    next_remaining.append(other)
            remaining = next_remaining
        merged.append(current)

    return merged
