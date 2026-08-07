#!/usr/bin/env python3
"""CLI entry point: convert a (scanned) PDF into an editable, OCR'd .docx file.

Examples
--------
Basic (English, Tesseract):
    python main.py input.pdf output.docx

Multiple languages with Tesseract (French + English):
    python main.py input.pdf output.docx --engine tesseract --lang fra eng

Use PaddleOCR (higher accuracy, requires `pip install paddlepaddle paddleocr`):
    python main.py input.pdf output.docx --engine paddleocr --lang ch

Force OCR even on pages that already contain a text layer, and skip pre-processing:
    python main.py input.pdf output.docx --force-ocr --no-preprocess
"""

from __future__ import annotations

import argparse
import sys

from pdf2docx_ocr.config import OCRConfig
from pdf2docx_ocr.core.pipeline import convert_pdf_to_docx


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a scanned/image PDF into an editable, multilingual, OCR'd .docx file."
    )
    parser.add_argument("input_pdf", help="Path to the source PDF file.")
    parser.add_argument("output_docx", help="Path to write the resulting .docx file.")
    parser.add_argument(
        "--engine",
        choices=["tesseract", "paddleocr"],
        default="paddleocr",
        help="OCR backend to use (default: paddleocr).",
    )
    parser.add_argument(
        "--mode",
        choices=["exact", "structure", "layout", "text"],
        default="exact",
        help=(
            "Conversion mode: 'exact' places editable textboxes/images at page coordinates "
            "(best visual match, default); 'structure' is reading-order blocks; "
            "'layout' is heuristic; 'text' is flowing paragraphs only."
        ),
    )
    parser.add_argument(
        "--lang",
        nargs="+",
        default=None,
        help=(
            "Language code(s). For --engine tesseract, pass one or more Tesseract "
            "codes (e.g. --lang eng fra deu). For --engine paddleocr, pass a single "
            "PaddleOCR code (e.g. --lang en, or --lang ch). "
            "Defaults to 'en' for paddleocr and 'eng' for tesseract."
        ),
    )
    parser.add_argument("--dpi", type=int, default=300, help="Rendering DPI (default: 300).")
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="OCR every page even if the PDF already has an extractable text layer.",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Disable image pre-processing (grayscale/denoise/deskew/threshold) before OCR.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=40.0,
        help="Minimum OCR confidence (0-100) used for downstream filtering (default: 40).",
    )
    parser.add_argument(
        "--detect-language",
        action="store_true",
        help="Auto-detect and annotate the language of each page's text (requires langdetect).",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.lang is None:
        languages = ["en"] if args.engine == "paddleocr" else ["eng"]
    else:
        languages = args.lang

    config = OCRConfig(
        input_pdf=args.input_pdf,
        output_docx=args.output_docx,
        languages=languages,
        engine=args.engine,
        mode=args.mode,
        dpi=args.dpi,
        force_ocr=args.force_ocr,
        preprocess=not args.no_preprocess,
        min_confidence=args.min_confidence,
        detect_language=args.detect_language,
        verbose=not args.quiet,
    )

    try:
        output_path = convert_pdf_to_docx(config)
    except Exception as exc:  # surface a clean error message to CLI users
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Done. Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
