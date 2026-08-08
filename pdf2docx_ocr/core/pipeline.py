"""Orchestrates the full PDF -> (pre-process) -> OCR/layout/structure -> DOCX pipeline."""

from __future__ import annotations

from typing import Callable, Optional

from tqdm import tqdm

from ..config import OCRConfig
from ..utils.image_utils import preprocess_for_ocr
from ..utils.language_utils import detect_language
from .digital_layout import extract_digital_layout
from .docx_builder import DocxBuilder
from .layout_docx_builder import LayoutDocxBuilder
from .ocr_engine import get_engine
from .ocr_layout import extract_ocr_layout
from .pdf_processor import PDFProcessor
from .exact_docx_builder import ExactDocxBuilder
from .structure_docx_builder import StructureDocxBuilder
from .structure_engine import get_structure_engine

# Called as on_progress(current_page_index, total_pages, message) after each page.
ProgressCallback = Callable[[int, int, str], None]


def convert_pdf_to_docx(
    config: OCRConfig, on_progress: Optional[ProgressCallback] = None
) -> str:
    """Run the pipeline for the given config and return the output docx path.

    ``on_progress``, if given, is invoked after each page is processed with
    ``(page_index, total_pages, message)`` -- handy for driving a GUI progress
    bar without depending on stdout/tqdm.
    """
    if config.mode == "exact":
        return _convert_exact(config, on_progress)
    if config.mode == "structure":
        return _convert_structure(config, on_progress)
    if config.mode == "layout":
        return _convert_layout(config, on_progress)
    return _convert_text(config, on_progress)


def _convert_exact(
    config: OCRConfig, on_progress: Optional[ProgressCallback] = None
) -> str:
    """Rasterize pages, parse layout, place editable textboxes/images by bbox."""
    # Tables as visual crops are more faithful than HTML tables for exact mode.
    engine = get_structure_engine(config.languages, use_table_recognition=False)
    builder = ExactDocxBuilder(dpi=config.dpi)

    with PDFProcessor(config.input_pdf, dpi=config.dpi) as pdf:
        total_pages = pdf.page_count
        iterator = tqdm(
            range(total_pages),
            total=total_pages,
            desc="Exact layout pages",
            disable=not config.verbose,
        )

        for index in iterator:
            image = pdf.render_page(index)
            page_result = engine.recognize_page(image)
            builder.add_page(page_result, page_image=image)
            message = (
                f"Page {index + 1}/{total_pages}: exact layout (textboxes + figures)"
            )
            if on_progress:
                on_progress(index + 1, total_pages, message)

    builder.save(config.output_docx)
    return config.output_docx


def _convert_structure(
    config: OCRConfig, on_progress: Optional[ProgressCallback] = None
) -> str:
    """Rasterize every page and run PP-StructureV3 for structural DOCX export."""
    engine = get_structure_engine(config.languages)
    builder = StructureDocxBuilder()

    with PDFProcessor(config.input_pdf, dpi=config.dpi) as pdf:
        total_pages = pdf.page_count
        iterator = tqdm(
            range(total_pages),
            total=total_pages,
            desc="Structure pages",
            disable=not config.verbose,
        )

        for index in iterator:
            image = pdf.render_page(index)
            # Structure models expect a natural page image, not binarized OCR preproc.
            page_result = engine.recognize_page(image)
            builder.add_page(page_result)
            message = (
                f"Page {index + 1}/{total_pages}: PP-StructureV3 layout/tables/figures"
            )
            if on_progress:
                on_progress(index + 1, total_pages, message)

    builder.save(config.output_docx)
    return config.output_docx


def _convert_text(
    config: OCRConfig, on_progress: Optional[ProgressCallback] = None
) -> str:
    engine = get_engine(config.engine, min_confidence=config.min_confidence)
    builder = DocxBuilder()

    with PDFProcessor(config.input_pdf, dpi=config.dpi) as pdf:
        total_pages = pdf.page_count
        iterator = tqdm(
            pdf.iter_pages(),
            total=total_pages,
            desc="Converting pages",
            disable=not config.verbose,
        )

        for page in iterator:
            use_native = page.has_native_text and not config.force_ocr

            page_result = None
            detected_lang = None

            if use_native:
                text_for_detection = page.native_text
                message = f"Page {page.index + 1}/{total_pages}: used existing text layer"
            else:
                image = page.image
                if config.preprocess:
                    image = preprocess_for_ocr(image)
                page_result = engine.recognize(image, config.languages)
                text_for_detection = page_result.text
                message = f"Page {page.index + 1}/{total_pages}: OCR'd with {config.engine}"

            if config.detect_language:
                detected_lang = detect_language(text_for_detection)

            builder.add_page(
                page_result=page_result,
                page_index=page.index,
                native_text=page.native_text if use_native else None,
                detected_language=detected_lang,
            )

            if on_progress:
                on_progress(page.index + 1, total_pages, message)

    builder.save(config.output_docx)
    return config.output_docx


def _convert_layout(
    config: OCRConfig, on_progress: Optional[ProgressCallback] = None
) -> str:
    engine = get_engine(config.engine, min_confidence=config.min_confidence)
    builder = LayoutDocxBuilder(dpi=config.dpi)

    with PDFProcessor(config.input_pdf, dpi=config.dpi) as pdf:
        total_pages = pdf.page_count
        page_indexes = range(total_pages)
        iterator = tqdm(
            page_indexes,
            total=total_pages,
            desc="Converting pages",
            disable=not config.verbose,
        )

        for index in iterator:
            use_native = pdf.has_native_text(index) and not config.force_ocr

            if use_native:
                fitz_page = pdf.get_fitz_page(index)
                layout = extract_digital_layout(fitz_page, dpi=config.dpi, page_index=index)
                message = (
                    f"Page {index + 1}/{total_pages}: layout from digital text/images/tables"
                )
            else:
                image = pdf.render_page(index)
                ocr_image = preprocess_for_ocr(image) if config.preprocess else image
                page_result = engine.recognize(ocr_image, config.languages)
                # Figure crops should come from the original (non-binarized) page image.
                layout = extract_ocr_layout(image, page_result, page_index=index)
                message = (
                    f"Page {index + 1}/{total_pages}: layout OCR ({config.engine}) + figures"
                )

            builder.add_page(layout)

            if on_progress:
                on_progress(index + 1, total_pages, message)

    builder.save(config.output_docx)
    return config.output_docx
