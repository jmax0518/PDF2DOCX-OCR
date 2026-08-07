"""Central configuration for the PDF -> OCR -> DOCX pipeline."""

from dataclasses import dataclass, field
from typing import List, Literal


@dataclass
class OCRConfig:
    """User-tunable settings for a single conversion run."""

    # Input / output
    input_pdf: str
    output_docx: str

    # Languages to recognize. Interpreted differently per engine:
    #   - tesseract: Tesseract language codes, e.g. ["eng", "fra", "deu"]
    #   - paddleocr: a single PaddleOCR language code, e.g. "en", "ch", "fr"
    languages: List[str] = field(default_factory=lambda: ["en"])

    # Which OCR backend to use: "tesseract" or "paddleocr"
    engine: str = "paddleocr"

    # Conversion mode:
    #   - exact: absolute textboxes/images at page coordinates (best visual match)
    #   - structure: PP-StructureV3 reading-order blocks, figures, tables
    #   - layout: approximate reading-order layout (heuristic)
    #   - text: legacy flowing-paragraph text-only output
    mode: Literal["exact", "structure", "layout", "text"] = "exact"

    # Rendering DPI when rasterizing PDF pages to images (higher = more accurate, slower)
    dpi: int = 300

    # If True, always OCR every page even if the PDF already has an extractable text layer.
    force_ocr: bool = False

    # If True, run image pre-processing (grayscale, deskew, denoise, binarize) before OCR.
    preprocess: bool = True

    # Minimum OCR confidence (0-100) below which a text block is flagged / skipped.
    min_confidence: float = 40.0

    # If True, try to auto-detect the language of the extracted text (metadata only).
    detect_language: bool = False

    # If True, print progress information to stdout.
    verbose: bool = True

    @property
    def tesseract_lang_string(self) -> str:
        """Tesseract expects languages joined with '+', e.g. 'eng+fra+deu'."""
        return "+".join(self.languages)
