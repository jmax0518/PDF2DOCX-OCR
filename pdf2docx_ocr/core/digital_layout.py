"""Extract structured layout from digital (text-layer) PDF pages via PyMuPDF."""

from __future__ import annotations

import io
from typing import List, Optional, Set

import fitz  # PyMuPDF
from PIL import Image

from .layout_model import (
    BBox,
    ImageBlock,
    PageLayout,
    TableBlock,
    TextBlock,
)


def extract_digital_layout(
    page: "fitz.Page",
    dpi: int,
    page_index: int,
) -> PageLayout:
    """Build a PageLayout from a PDF page that already has a text layer."""
    scale = dpi / 72.0
    page_width = page.rect.width * scale
    page_height = page.rect.height * scale

    table_boxes: List[BBox] = []
    tables = _extract_tables(page, scale)
    for table in tables:
        table_boxes.append(table.bbox)

    text_blocks = _extract_text_blocks(page, scale, table_boxes)
    image_blocks = _extract_images(page, scale)

    elements = [*text_blocks, *image_blocks, *tables]
    return PageLayout(
        page_index=page_index,
        width=page_width,
        height=page_height,
        elements=elements,
    )


def _scale_bbox(bbox, scale: float) -> BBox:
    x0, y0, x1, y1 = bbox
    return BBox(x0 * scale, y0 * scale, x1 * scale, y1 * scale)


def _extract_tables(page: "fitz.Page", scale: float) -> List[TableBlock]:
    tables: List[TableBlock] = []
    try:
        finder = page.find_tables()
    except Exception:
        return tables

    raw_tables = getattr(finder, "tables", None) or []
    for table in raw_tables:
        try:
            rows = table.extract() or []
        except Exception:
            continue
        cleaned: List[List[str]] = []
        for row in rows:
            cleaned.append([("" if cell is None else str(cell)).strip() for cell in row])
        if not any(any(cell for cell in row) for row in cleaned):
            continue
        bbox = _scale_bbox(table.bbox, scale)
        tables.append(TableBlock(rows=cleaned, bbox=bbox))
    return tables


def _extract_text_blocks(
    page: "fitz.Page",
    scale: float,
    table_boxes: List[BBox],
) -> List[TextBlock]:
    blocks: List[TextBlock] = []
    try:
        data = page.get_text("dict")
    except Exception:
        return blocks

    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines_out: List[str] = []
        pt_sizes: List[float] = []
        for line in block.get("lines", []):
            parts = [span.get("text", "") for span in line.get("spans", [])]
            line_text = "".join(parts).strip()
            if line_text:
                lines_out.append(line_text)
            for span in line.get("spans", []):
                size = span.get("size")
                if size:
                    pt_sizes.append(float(size))
        text = "\n".join(lines_out).strip()
        if not text:
            continue
        bbox = _scale_bbox(block["bbox"], scale)
        if any(bbox.overlaps_fraction(tb) >= 0.5 for tb in table_boxes):
            continue
        font_hint_pt = sum(pt_sizes) / len(pt_sizes) if pt_sizes else None
        blocks.append(TextBlock(text=text, bbox=bbox, font_size_hint=font_hint_pt))
    return blocks


def _extract_images(page: "fitz.Page", scale: float) -> List[ImageBlock]:
    images: List[ImageBlock] = []
    seen_rects: Set[tuple] = set()
    doc = page.parent

    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if not rects:
            continue

        pil_image = _pixmap_to_pil(doc, xref)
        if pil_image is None:
            continue

        for rect in rects:
            key = (round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2))
            if key in seen_rects:
                continue
            seen_rects.add(key)
            bbox = _scale_bbox((rect.x0, rect.y0, rect.x1, rect.y1), scale)
            if bbox.width < 8 or bbox.height < 8:
                continue
            images.append(ImageBlock(image=pil_image.copy(), bbox=bbox))

    # Also pick up image blocks reported by the text dict (covers some forms).
    try:
        data = page.get_text("dict")
    except Exception:
        data = {}
    for block in data.get("blocks", []):
        if block.get("type") != 1:
            continue
        bbox = _scale_bbox(block["bbox"], scale)
        key = (
            round(bbox.x0 / scale, 2),
            round(bbox.y0 / scale, 2),
            round(bbox.x1 / scale, 2),
            round(bbox.y1 / scale, 2),
        )
        if key in seen_rects:
            continue
        # No separate bitmap here; skip if already covered by xref extraction.
        # If nothing was extracted for this rect, try clipping the page region.
        if any(bbox.iou(img.bbox) > 0.4 for img in images):
            continue
        clipped = _clip_page_region(page, block["bbox"])
        if clipped is not None:
            seen_rects.add(key)
            images.append(ImageBlock(image=clipped, bbox=bbox))

    return images


def _pixmap_to_pil(doc: "fitz.Document", xref: int) -> Optional[Image.Image]:
    try:
        pix = fitz.Pixmap(doc, xref)
        if pix.n >= 5:  # CMYK or with alpha weirdness
            pix = fitz.Pixmap(fitz.csRGB, pix)
        if pix.alpha:
            pix = fitz.Pixmap(pix, 0)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return img
    except Exception:
        try:
            # Fallback via image bytes extract
            base = doc.extract_image(xref)
            return Image.open(io.BytesIO(base["image"])).convert("RGB")
        except Exception:
            return None


def _clip_page_region(page: "fitz.Page", bbox_pts) -> Optional[Image.Image]:
    try:
        clip = fitz.Rect(bbox_pts)
        if clip.width < 2 or clip.height < 2:
            return None
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except Exception:
        return None
