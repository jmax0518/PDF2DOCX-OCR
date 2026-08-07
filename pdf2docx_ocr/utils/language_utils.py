"""Helpers for language codes and (optional) language detection."""

from __future__ import annotations

from typing import Optional

# Common ISO 639-1 <-> Tesseract (639-2/3-letter) code mapping.
# Extend as needed; Tesseract ships ~100 language packs.
ISO639_1_TO_TESSERACT = {
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "nl": "nld",
    "ru": "rus",
    "zh": "chi_sim",
    "zh-tw": "chi_tra",
    "ja": "jpn",
    "ko": "kor",
    "ar": "ara",
    "hi": "hin",
    "vi": "vie",
    "th": "tha",
    "tr": "tur",
    "pl": "pol",
    "uk": "ukr",
    "id": "ind",
}

# Common ISO 639-1 <-> PaddleOCR language code mapping.
ISO639_1_TO_PADDLEOCR = {
    "en": "en",
    "fr": "fr",
    "de": "german",
    "es": "es",
    "it": "it",
    "pt": "pt",
    "ru": "ru",
    "zh": "ch",
    "zh-tw": "chinese_cht",
    "ja": "japan",
    "ko": "korean",
    "ar": "ar",
    "hi": "hi",
    "vi": "vi",
    "tr": "tr",
    "pl": "pl",
    "uk": "uk",
    "id": "id",
}


def to_tesseract_code(iso_code: str) -> str:
    return ISO639_1_TO_TESSERACT.get(iso_code.lower(), iso_code)


def to_paddleocr_code(iso_code: str) -> str:
    return ISO639_1_TO_PADDLEOCR.get(iso_code.lower(), iso_code)


def detect_language(text: str) -> Optional[str]:
    """Best-effort ISO 639-1 language detection for metadata/logging purposes.

    Returns None if `langdetect` isn't installed or detection fails.
    """
    try:
        from langdetect import detect, LangDetectException
    except ImportError:
        return None

    try:
        if not text or not text.strip():
            return None
        return detect(text)
    except LangDetectException:
        return None
