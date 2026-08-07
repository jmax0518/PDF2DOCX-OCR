"""PP-StructureV3 wrapper for structural document parsing."""

from __future__ import annotations

import os
from typing import Any, List, Optional

from PIL import Image

from ..utils.language_utils import to_paddleocr_code


class StructureEngine:
    """Lazy PPStructureV3 pipeline for layout + tables + figures."""

    def __init__(self, lang: str = "en", use_table_recognition: bool = True):
        self.lang = to_paddleocr_code(lang) if lang else "en"
        self.use_table_recognition = use_table_recognition
        self._pipeline = None

    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        # Avoid oneDNN/PIR crash on Windows CPU (PaddlePaddle 3.3.x).
        os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        # Limit native thread blow-ups that often accompany ACCESS_VIOLATION on Windows.
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")

        try:
            from paddleocr import PPStructureV3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "PPStructureV3 requires paddleocr. "
                "Run `pip install paddlepaddle paddleocr \"paddlex[ocr]\"` "
                "(Python 3.10–3.12)."
            ) from exc

        # Prefer mobile OCR + disabled heavy modules for Windows CPU stability.
        # Full server OCR + region detection has been observed to crash (0xC0000005).
        self._pipeline = PPStructureV3(
            lang=self.lang,
            ocr_version="PP-OCRv4",
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            use_seal_recognition=False,
            use_chart_recognition=False,
            use_formula_recognition=False,
            use_region_detection=False,
            use_table_recognition=self.use_table_recognition,
            enable_mkldnn=False,
        )
        return self._pipeline

    def recognize_page(self, image: Image.Image) -> Any:
        """Run structural parsing on one page image; return the first result object."""
        if image.mode != "RGB":
            image = image.convert("RGB")

        import numpy as np

        pipeline = self._ensure_pipeline()
        results = pipeline.predict(np.array(image))
        if not results:
            raise RuntimeError("PPStructureV3 returned no results for the page image.")
        return results[0]


def get_structure_engine(
    languages: Optional[List[str]] = None,
    use_table_recognition: bool = True,
) -> StructureEngine:
    lang = "en"
    if languages:
        lang = to_paddleocr_code(languages[0])
    return StructureEngine(lang=lang, use_table_recognition=use_table_recognition)
