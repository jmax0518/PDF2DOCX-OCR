"""OCR engine abstraction.

Two backends are provided out of the box:

- ``TesseractEngine``: wraps `pytesseract`. Lightweight, CPU-only, 100+ languages.
  Requires the Tesseract binary + language packs to be installed on the system.
- ``PaddleOCREngine``: wraps `paddleocr`. Heavier install, benefits from a GPU,
  but generally more accurate on noisy scans and CJK / mixed-script documents.

Both return a common ``OCRPageResult`` made of ``OCRLine`` objects so the rest
of the pipeline (docx building) never needs to know which engine produced them.

Add new engines by subclassing ``OCREngine`` and registering them in
``get_engine()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from PIL import Image


@dataclass
class OCRWord:
    text: str
    confidence: float
    bbox: tuple  # (left, top, width, height) in pixels


@dataclass
class OCRLine:
    words: List[OCRWord]
    bbox: tuple  # bounding box enclosing the whole line

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words if w.text.strip())

    @property
    def confidence(self) -> float:
        confidences = [w.confidence for w in self.words if w.confidence >= 0]
        return sum(confidences) / len(confidences) if confidences else 0.0


@dataclass
class OCRPageResult:
    lines: List[OCRLine]
    page_width: int
    page_height: int

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class OCREngine(ABC):
    """Common interface every OCR backend must implement."""

    name = "base"

    @abstractmethod
    def recognize(self, image: Image.Image, languages: List[str]) -> OCRPageResult:
        """Run OCR on a single page image and return structured line/word results."""
        raise NotImplementedError


class TesseractEngine(OCREngine):
    """OCR backend based on Google's Tesseract (via pytesseract)."""

    name = "tesseract"

    def __init__(self, min_confidence: float = 40.0):
        self.min_confidence = min_confidence

    def recognize(self, image: Image.Image, languages: List[str]) -> OCRPageResult:
        try:
            import pytesseract
        except ImportError as exc:  # pragma: no cover - dependency hint
            raise RuntimeError(
                "pytesseract is not installed. Run `pip install pytesseract` and "
                "install the Tesseract binary (see README.md)."
            ) from exc

        lang_string = "+".join(languages)
        data = pytesseract.image_to_data(
            image, lang=lang_string, output_type=pytesseract.Output.DICT
        )

        lines_by_key = {}
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = float(data["conf"][i]) if data["conf"][i] != "-1" else -1.0
            if not text:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            word = OCRWord(
                text=text,
                confidence=conf,
                bbox=(data["left"][i], data["top"][i], data["width"][i], data["height"][i]),
            )
            lines_by_key.setdefault(key, []).append(word)

        lines: List[OCRLine] = []
        for key in sorted(lines_by_key.keys()):
            words = lines_by_key[key]
            xs = [w.bbox[0] for w in words]
            ys = [w.bbox[1] for w in words]
            rights = [w.bbox[0] + w.bbox[2] for w in words]
            bottoms = [w.bbox[1] + w.bbox[3] for w in words]
            bbox = (min(xs), min(ys), max(rights) - min(xs), max(bottoms) - min(ys))
            lines.append(OCRLine(words=words, bbox=bbox))

        return OCRPageResult(lines=lines, page_width=image.width, page_height=image.height)


class PaddleOCREngine(OCREngine):
    """OCR backend based on Baidu's PaddleOCR. Higher accuracy, especially for
    multilingual / CJK / noisy documents, at the cost of a heavier install."""

    name = "paddleocr"

    def __init__(self, min_confidence: float = 40.0):
        self.min_confidence = min_confidence
        self._readers = {}  # cache one PaddleOCR instance per language code

    def _get_reader(self, lang: str):
        import os

        # Avoid oneDNN/PIR crash on Windows CPU (PaddlePaddle 3.3.x).
        os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:  # pragma: no cover - dependency hint
            raise RuntimeError(
                "paddleocr is not installed. Run `pip install paddlepaddle paddleocr` "
                "to use this engine (requires Python 3.10–3.12; see requirements.txt)."
            ) from exc

        if lang not in self._readers:
            # PaddleOCR 3.x API. enable_mkldnn=False bypasses known oneDNN bugs.
            self._readers[lang] = PaddleOCR(
                lang=lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
        return self._readers[lang]

    def recognize(self, image: Image.Image, languages: List[str]) -> OCRPageResult:
        import numpy as np

        # PaddleOCR expects HxWxC; preprocessing may produce grayscale (mode L).
        if image.mode != "RGB":
            image = image.convert("RGB")

        # PaddleOCR takes a single language code per instance (e.g. "en", "ch", "fr").
        lang = languages[0] if languages else "en"
        reader = self._get_reader(lang)

        pages = reader.predict(np.array(image))
        lines: List[OCRLine] = []
        for page in pages or []:
            payload = page.json.get("res", page.json) if hasattr(page, "json") else page
            texts = payload.get("rec_texts") or []
            scores = payload.get("rec_scores") or []
            boxes = payload.get("rec_boxes")
            polys = payload.get("rec_polys") or payload.get("dt_polys") or []

            for i, text in enumerate(texts):
                if not str(text).strip():
                    continue
                conf = float(scores[i]) if i < len(scores) else 0.0
                if conf * 100 < self.min_confidence:
                    continue

                if boxes is not None and i < len(boxes):
                    x0, y0, x1, y1 = [float(v) for v in boxes[i]]
                    bbox = (x0, y0, max(0.0, x1 - x0), max(0.0, y1 - y0))
                elif i < len(polys):
                    poly = polys[i]
                    xs = [float(p[0]) for p in poly]
                    ys = [float(p[1]) for p in poly]
                    bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
                else:
                    bbox = (0.0, float(i * 20), float(image.width), 20.0)

                word = OCRWord(text=str(text), confidence=conf * 100, bbox=bbox)
                lines.append(OCRLine(words=[word], bbox=bbox))

        lines.sort(key=lambda l: (round(l.bbox[1] / 10), l.bbox[0]))
        return OCRPageResult(lines=lines, page_width=image.width, page_height=image.height)


def get_engine(name: str, min_confidence: float = 40.0) -> OCREngine:
    """Factory: instantiate an OCR engine by name."""
    engines = {
        "tesseract": TesseractEngine,
        "paddleocr": PaddleOCREngine,
    }
    try:
        return engines[name](min_confidence=min_confidence)
    except KeyError as exc:
        raise ValueError(
            f"Unknown OCR engine '{name}'. Available engines: {list(engines)}"
        ) from exc
