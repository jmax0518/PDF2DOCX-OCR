# PDF to Editable Word (DOCX) via Multilanguage OCR

Converts scanned / image-only PDFs (or PDFs mixed with real text) into editable, multilanguage `.docx` files. Pages that already contain a real text layer are copied directly; image-only pages are rasterized and run through an OCR engine, then reassembled into paragraphs in reading order.

## Documentation

| Document | Purpose |
|---|---|
| **[Doc.md](Doc.md)** | **Windows 10 offline setup** — full step-by-step guide for PCs with **no internet** (USB install, local wheels) |
| **[wheels/README.md](wheels/README.md)** | Core offline Python wheels (~87 MB, 19 files) |
| **[wheels/paddleocr/README.md](wheels/paddleocr/README.md)** | Optional PaddleOCR wheels (~206 MB, 69 files) |

---

## Which OCR engine should I use?

| Engine | Best for | Install | Offline? |
|---|---|---|---|
| **Tesseract** (default) | Simple setup, CPU-only, 100+ languages | Python wrapper + separate `.exe` | Yes — wheels + Tesseract installer on USB |
| **PaddleOCR** (optional) | Higher accuracy, strong CJK / noisy scans | Python packages only (`paddlepaddle` + `paddleocr`) | Yes — `wheels/paddleocr/` bundle |
| **No OCR** | Digital PDFs that already have text | Core packages only | Yes — skip Tesseract if `--force-ocr` is off |

**Recommendation:** use **Tesseract** for the smallest offline setup. Use **PaddleOCR** if you cannot install Tesseract or need better accuracy on scanned / CJK documents.

---

## Project structure

```
OCR-python-example/
├── main.py                          # CLI entry point
├── gui_app.py                       # Desktop GUI (Tkinter)
├── Doc.md                           # Windows 10 offline setup guide
├── requirements.txt                 # Online install (pip)
├── requirements-wheels.txt          # Core offline wheels (pinned)
├── requirements-paddleocr-wheels.txt # Optional PaddleOCR offline wheels
├── wheels/
│   ├── *.whl                        # Core packages (19 files, ~87 MB)
│   ├── README.md
│   └── paddleocr/
│       ├── *.whl                    # PaddleOCR stack (69 files, ~206 MB)
│       └── README.md
├── scripts/
│   ├── download_wheels.ps1          # Download wheels (needs internet)
│   ├── install_from_wheels.ps1      # Install core wheels (offline)
│   └── install_from_paddleocr_wheels.ps1
├── pdf2docx_ocr/
│   ├── config.py
│   ├── core/
│   │   ├── pdf_processor.py
│   │   ├── ocr_engine.py          # Tesseract + PaddleOCR backends
│   │   ├── docx_builder.py
│   │   └── pipeline.py
│   └── utils/
│       ├── image_utils.py
│       └── language_utils.py
└── tests/
    └── test_docx_builder.py
```

---

## Quick start (online — Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
python gui_app.py
```

---

## Quick start (offline — Windows 10, no internet)

See **[Doc.md](Doc.md)** for the full guide. Short version:

1. Copy from USB: Python installer, project folder (with `wheels/`), and Tesseract installer **or** `wheels/paddleocr/`
2. Install Python (check **Add to PATH**)
3. Create venv and install core wheels:

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate.bat
   pip install --no-index --find-links=wheels -r requirements-wheels.txt
   ```

4. Install OCR backend:
   - **Tesseract:** run `tesseract-ocr-w64-setup-....exe` from USB, add to PATH
   - **PaddleOCR:** `pip install --no-index --find-links=wheels --find-links=wheels/paddleocr -r requirements-paddleocr-wheels.txt`

5. Run: `python gui_app.py`

---

## Usage

### CLI

```bash
# English, Tesseract (default)
python main.py input.pdf output.docx

# Multilanguage Tesseract (French + English)
python main.py input.pdf output.docx --engine tesseract --lang fra eng

# PaddleOCR (e.g. Chinese) — no Tesseract binary needed
python main.py input.pdf output.docx --engine paddleocr --lang ch

# Digital PDF — copy text layer only, no OCR (Tesseract not required)
python main.py input.pdf output.docx
# Do NOT use --force-ocr

# Force OCR on every page
python main.py input.pdf output.docx --force-ocr
```

Run `python main.py --help` for all options.

### GUI

```bash
python gui_app.py
```

- Browse input PDF and output DOCX
- Choose **Tesseract** or **PaddleOCR**
- Select languages (Tesseract: multiple; PaddleOCR: first checked language only)
- Options: DPI, force OCR, pre-processing, language detection
- Live progress log and open output folder when done

---

## Offline wheel bundles

| Bundle | Folder | Files | Size | Install |
|---|---|---|---|---|
| Core (required) | `wheels/` | 19 | ~87 MB | `pip install --no-index --find-links=wheels -r requirements-wheels.txt` |
| PaddleOCR (optional) | `wheels/paddleocr/` | 69 | ~206 MB | After core — see `requirements-paddleocr-wheels.txt` |

Refresh wheels on a connected PC:

```powershell
.\scripts\download_wheels.ps1                  # core only
.\scripts\download_wheels.ps1 -IncludePaddleOCR # core + PaddleOCR
```

Wheels are **Windows 64-bit, Python 3.10+** only. Regenerate on other platforms.

**Not included in any wheel bundle:**

- Python installer (`python-3.10.x-amd64.exe`)
- Tesseract OCR binary (`tesseract-ocr-w64-setup-....exe`) — only needed for `--engine tesseract`

---

## How it works

1. **PDFProcessor** (PyMuPDF) rasterizes pages and extracts any existing text layer.
2. Pages with enough embedded text skip OCR unless `--force-ocr` is set.
3. Image pages are optionally pre-processed (grayscale, denoise, deskew, threshold).
4. **OCREngine** (Tesseract or PaddleOCR) returns structured lines/words with bounding boxes.
5. **DocxBuilder** groups lines into paragraphs and writes an editable `.docx`.

---

## Running tests

```bash
pytest
```

Tests cover `docx_builder` logic only — no Tesseract or PaddleOCR required.

---

## Extending

- **New OCR engine:** subclass `OCREngine` in `pdf2docx_ocr/core/ocr_engine.py`, register in `get_engine()`.
- **Tables/layout:** extend `DocxBuilder` using bounding boxes from `OCRPageResult`.
- **Batch processing:** loop `convert_pdf_to_docx()` over a folder of PDFs.
