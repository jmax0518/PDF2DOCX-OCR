"""Build PageLayout from OCR results plus residual figure regions."""

from __future__ import annotations

from typing import List

import cv2
import numpy as np
from PIL import Image

from .layout_model import BBox, ImageBlock, PageLayout, TextBlock, merge_overlapping_boxes
from .ocr_engine import OCRPageResult


def extract_ocr_layout(
    image: Image.Image,
    page_result: OCRPageResult,
    page_index: int,
    min_figure_area_ratio: float = 0.01,
) -> PageLayout:
    """Combine OCR text lines with non-text figure crops into a PageLayout."""
    width = float(page_result.page_width or image.width)
    height = float(page_result.page_height or image.height)

    text_blocks = _text_blocks_from_ocr(page_result)
    image_blocks = _extract_figure_regions(
        image,
        page_result,
        min_figure_area_ratio=min_figure_area_ratio,
    )

    return PageLayout(
        page_index=page_index,
        width=width,
        height=height,
        elements=[*text_blocks, *image_blocks],
    )


def _text_blocks_from_ocr(page_result: OCRPageResult) -> List[TextBlock]:
    blocks: List[TextBlock] = []
    for line in page_result.lines:
        text = line.text.strip()
        if not text:
            continue
        left, top, w, h = line.bbox
        bbox = BBox(float(left), float(top), float(left + w), float(top + h))
        # Approximate Word points from line height for typical 200–300 DPI scans.
        font_pt = float(h) * 0.35 if h else 11.0
        font_pt = max(8.0, min(font_pt, 36.0))
        blocks.append(TextBlock(text=text, bbox=bbox, font_size_hint=font_pt))
    return blocks


def _extract_figure_regions(
    image: Image.Image,
    page_result: OCRPageResult,
    min_figure_area_ratio: float,
) -> List[ImageBlock]:
    rgb = np.array(image.convert("RGB"))
    h, w = rgb.shape[:2]
    if h == 0 or w == 0:
        return []

    # Mask out OCR text regions so residual content can be treated as figures.
    text_mask = np.zeros((h, w), dtype=np.uint8)
    pad = max(2, int(min(h, w) * 0.004))
    for line in page_result.lines:
        left, top, bw, bh = line.bbox
        x0 = max(0, int(left) - pad)
        y0 = max(0, int(top) - pad)
        x1 = min(w, int(left + bw) + pad)
        y1 = min(h, int(top + bh) + pad)
        if x1 > x0 and y1 > y0:
            text_mask[y0:y1, x0:x1] = 255

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Content mask: ink / textured areas
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 11
    )
    # Also catch photographic regions via edge energy
    edges = cv2.Canny(gray, 60, 150)
    content = cv2.bitwise_or(binary, edges)
    content[text_mask == 255] = 0

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    content = cv2.morphologyEx(content, cv2.MORPH_CLOSE, kernel, iterations=2)
    content = cv2.dilate(content, kernel, iterations=1)

    contours, _ = cv2.findContours(content, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(h * w)
    min_area = page_area * min_figure_area_ratio
    max_area = page_area * 0.85

    candidate_boxes: List[BBox] = []
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = float(bw * bh)
        if area < min_area or area > max_area:
            continue
        # Skip very thin lines (likely ruled lines / artifacts)
        if bw < 24 or bh < 24:
            continue
        aspect = bw / float(bh)
        if aspect > 20 or aspect < 0.05:
            continue
        candidate_boxes.append(BBox(float(x), float(y), float(x + bw), float(y + bh)))

    merged = merge_overlapping_boxes(candidate_boxes, iou_threshold=0.1)
    images: List[ImageBlock] = []
    for box in merged:
        x0, y0, x1, y1 = int(box.x0), int(box.y0), int(box.x1), int(box.y1)
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(w, x1)
        y1 = min(h, y1)
        if x1 - x0 < 16 or y1 - y0 < 16:
            continue
        crop = Image.fromarray(rgb[y0:y1, x0:x1].copy())
        # Skip nearly blank crops
        arr = np.asarray(crop.convert("L"))
        if arr.std() < 8:
            continue
        images.append(ImageBlock(image=crop, bbox=BBox(float(x0), float(y0), float(x1), float(y1))))

    return images
