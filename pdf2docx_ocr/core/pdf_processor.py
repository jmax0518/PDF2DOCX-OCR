"""PDF loading, page rasterization, and native-text-layer detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import fitz  # PyMuPDF
from PIL import Image


@dataclass
class PDFPage:
    index: int
    image: Image.Image
    native_text: str  # text already embedded in the PDF (empty for scanned pages)

    @property
    def has_native_text(self) -> bool:
        return len(self.native_text.strip()) > 20  # heuristic threshold


class PDFProcessor:
    """Opens a PDF and yields page images (+ any extractable native text)."""

    def __init__(self, pdf_path: str, dpi: int = 300):
        self.pdf_path = pdf_path
        self.dpi = dpi
        self._doc = fitz.open(pdf_path)

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def document(self) -> "fitz.Document":
        return self._doc

    def get_fitz_page(self, index: int) -> "fitz.Page":
        return self._doc.load_page(index)

    def get_native_text(self, index: int) -> str:
        return self.get_fitz_page(index).get_text("text") or ""

    def has_native_text(self, index: int) -> bool:
        return len(self.get_native_text(index).strip()) > 20

    def render_page(self, index: int) -> Image.Image:
        return self._render_page(self.get_fitz_page(index))

    def _render_page(self, page: "fitz.Page") -> Image.Image:
        zoom = self.dpi / 72  # PDF default is 72 DPI
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def iter_pages(self):
        for i in range(self.page_count):
            page = self._doc.load_page(i)
            native_text = page.get_text("text") or ""
            image = self._render_page(page)
            yield PDFPage(index=i, image=image, native_text=native_text)

    def get_pages(self) -> List[PDFPage]:
        return list(self.iter_pages())

    def close(self):
        self._doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
