"""Build a multi-page DOCX from PP-StructureV3 page results."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, List


class StructureDocxBuilder:
    """Accumulate PP-Structure page results and export one structured DOCX."""

    def __init__(self):
        self._page_results: List[Any] = []

    def add_page(self, page_result: Any) -> None:
        self._page_results.append(page_result)

    def save(self, output_path: str) -> None:
        if not self._page_results:
            raise RuntimeError("No structure pages to save.")

        try:
            from paddlex.inference.common.result.converter import WordConverter, save_images
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "PaddleX WordConverter is required for structure mode. "
                "Ensure paddleocr/paddlex are installed."
            ) from exc

        tmp_dir = Path(tempfile.mkdtemp(prefix="pdf2docx_structure_"))
        try:
            all_blocks: List[dict] = []
            all_images: List[dict] = []
            page_width = 500
            page_height = 0

            for page_index, result in enumerate(self._page_results):
                word_data = result.word
                path_map: dict[str, str] = {}

                for item in word_data.get("images") or []:
                    item = dict(item)
                    orig = item.get("path") or f"img_{page_index}.png"
                    stem = Path(orig).stem
                    suffix = Path(orig).suffix or ".png"
                    new_path = f"page{page_index}_{stem}{suffix}"
                    path_map[orig] = new_path
                    item["path"] = new_path
                    all_images.append(item)

                for block in word_data.get("word_blocks") or []:
                    block = dict(block)
                    block["page_index"] = page_index
                    content = block.get("content")
                    if isinstance(content, str) and content in path_map:
                        block["content"] = path_map[content]
                    all_blocks.append(block)

                try:
                    img = result["doc_preprocessor_res"]["output_img"]
                    page_height = int(img.shape[0])
                    page_width = int(img.shape[1])
                except Exception:
                    page_width = int(word_data.get("original_image_width") or page_width)

            abs_image_paths = save_images(all_images, tmp_dir) if all_images else {}
            doc = WordConverter.convert(
                all_blocks,
                abs_image_paths=abs_image_paths,
                original_image_width=page_width,
                original_image_height=page_height,
            )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
