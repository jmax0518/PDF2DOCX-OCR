# Windows Offline Setup & Run Guide

Complete guide for installing **all dependencies** and running this project on **another Windows PC** (with or without internet).

**Current offline bundle targets:**

| Item | Required |
|---|---|
| OS | Windows 10/11 **64-bit** |
| Python | **3.12.x amd64** (wheels are `cp312`) |
| Disk | ~**2 GB** free (wheels + models + venv) |

> Python **3.14 is not supported** for PaddleOCR. Use **3.12**.

---

## Documentation map

| File | What it covers |
|---|---|
| **Doc.md** (this file) | Install + run on other Windows PCs |
| [README.md](README.md) | Project overview, CLI/GUI |
| [offline_models/INSTALL_OFFLINE.txt](offline_models/INSTALL_OFFLINE.txt) | Short offline checklist |
| [wheels/README.md](wheels/README.md) | Core wheels |
| [wheels/paddleocr/README.md](wheels/paddleocr/README.md) | PaddleOCR wheels |

---

## What this project needs

| Component | Purpose | Offline location |
|---|---|---|
| Python 3.12 installer | Runtime | Copy `.exe` separately (not a wheel) |
| Core Python packages | PDF/DOCX/images | `wheels\` (~87 MB, 17 `.whl`) |
| PaddleOCR + PaddleX | OCR + layout structure | `wheels\paddleocr\` (~257 MB, 91 `.whl`) |
| PaddleX models | Exact/structure modes | `offline_models\official_models\` (~1.18 GB) |
| Tesseract (optional) | Only if `--engine tesseract` | Separate `.exe` installer |

**Recommended path for this project:** PaddleOCR + models (supports `exact` / `structure` modes).  
Tesseract alone cannot run PP-Structure / exact layout modes.

---

## Conversion modes (quick)

| Mode | Meaning | Default |
|---|---|---|
| `exact` | Visual layout: positioned textboxes + figures | **Yes** |
| `structure` | Reading-order blocks / tables via PP-StructureV3 | |
| `layout` | Heuristic reading-order layout | |
| `text` | Flowing paragraphs only (legacy) | |

---

# Path 1 — Online PC (internet available)

Use this when the target Windows PC has internet.

### 1. Install Python 3.12

1. Download: https://www.python.org/downloads/windows/ → **Windows installer (64-bit)** for **3.12.x**
2. Run installer → check **`Add python.exe to PATH`**
3. Verify:

```cmd
py -3.12 --version
```

### 2. Copy / clone project

```cmd
cd D:\Apps
git clone <your-repo-url> PDF2DOCX-OCR
cd PDF2DOCX-OCR
```

Or copy the project folder from USB.

### 3. Create venv and install everything

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install "paddlex[ocr]>=3.7.0"
```

`requirements.txt` already includes `paddlepaddle`, `paddleocr`, and `paddlex[ocr]`.

### 4. First-run models

Models download automatically on first `exact` / `structure` conversion into:

```
%USERPROFILE%\.paddlex\official_models\
```

### 5. Run

```cmd
.venv\Scripts\activate.bat
python gui_app.py
```

CLI:

```cmd
python main.py samples\resnet_scanned.pdf samples\out.docx --mode exact --lang en --dpi 150
```

---

# Path 2 — Offline PC (no internet) — recommended USB flow

## Part A — Prepare USB (on a PC WITH internet)

### A.1 Download Python 3.12 installer

- https://www.python.org/downloads/windows/
- File example: `python-3.12.10-amd64.exe`

Save to USB:

```
E:\OfflineSetup\python-3.12.10-amd64.exe
```

### A.2 Build / refresh the offline bundle

On the internet PC, in the project folder (with `.venv` already working):

```powershell
cd "D:\My Workspace\Python\OCR\PDF2DOCX-OCR"
powershell -ExecutionPolicy Bypass -File .\scripts\download_offline_bundle.ps1
```

This fills:

| Folder | Contents | Approx size |
|---|---|---|
| `wheels\` | Core `.whl` | ~87 MB |
| `wheels\paddleocr\` | PaddleOCR / PaddleX `.whl` | ~257 MB |
| `offline_models\official_models\` | Neural models | ~1.18 GB |

> Tip: run one `exact` conversion first so models exist under `%USERPROFILE%\.paddlex\official_models\`, then run the download script.

### A.3 Copy to USB

```
E:\OfflineSetup\
├── python-3.12.10-amd64.exe
└── PDF2DOCX-OCR\                 ← entire project
    ├── Doc.md
    ├── requirements.txt
    ├── requirements-wheels.txt
    ├── requirements-paddleocr-wheels.txt
    ├── wheels\                   ← core .whl
    ├── wheels\paddleocr\         ← paddle .whl
    ├── offline_models\
    │   ├── INSTALL_OFFLINE.txt
    │   └── official_models\      ← required for exact/structure
    ├── scripts\
    ├── samples\
    ├── gui_app.py
    ├── main.py
    └── pdf2docx_ocr\
```

### A.4 (Optional) Tesseract installer

Only if you also want `--engine tesseract`:

- https://github.com/UB-Mannheim/tesseract/wiki  
- Save e.g. `E:\OfflineSetup\tesseract-ocr-w64-setup-....exe`

Not required for default **exact / structure + PaddleOCR**.

---

## Part B — Install on the OFFLINE Windows PC

### Step 1 — Install Python 3.12

1. Run `python-3.12.10-amd64.exe` from USB  
2. Check **`[x] Add python.exe to PATH`**  
3. Install → Close  
4. Open a **new** Command Prompt:

```cmd
python --version
```

Must show **Python 3.12.x**.

---

### Step 2 — Copy project to local disk

Example:

```
USB:  E:\OfflineSetup\PDF2DOCX-OCR
PC:   D:\Apps\PDF2DOCX-OCR
```

Verify:

```cmd
dir D:\Apps\PDF2DOCX-OCR\wheels\*.whl
dir D:\Apps\PDF2DOCX-OCR\wheels\paddleocr\*.whl
dir D:\Apps\PDF2DOCX-OCR\offline_models\official_models
```

Expect roughly:

- Core: **~17** `.whl`
- Paddle: **~91** `.whl`
- Models folder present (many subfolders)

---

### Step 3 — Create virtual environment

```cmd
cd D:\Apps\PDF2DOCX-OCR
python -m venv .venv
.venv\Scripts\activate.bat
```

Prompt should show `(.venv)`.

> Do **not** run `pip install --upgrade pip` offline.

---

### Step 4 — Install core packages (offline)

```cmd
pip install --no-index --find-links=wheels -r requirements-wheels.txt
```

Or:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_from_wheels.ps1
```

Verify:

```cmd
python -c "import fitz, docx, cv2, pytesseract; print('Core OK')"
```

---

### Step 5 — Install PaddleOCR + PaddleX (offline)

```cmd
pip install --no-index --find-links=wheels --find-links=wheels\paddleocr -r requirements-paddleocr-wheels.txt
```

Or:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_from_paddleocr_wheels.ps1
```

Verify:

```cmd
python -c "import paddleocr, paddlex; print('PaddleOCR OK')"
```

---

### Step 6 — Install models (required for exact/structure)

Copy bundled models into the user cache PaddleX expects:

```cmd
xcopy /E /I /Y offline_models\official_models %USERPROFILE%\.paddlex\official_models
```

Verify:

```cmd
dir %USERPROFILE%\.paddlex\official_models
```

You should see folders such as `PP-DocLayout_plus-L`, `PP-OCRv4_mobile_det`, `en_PP-OCRv4_mobile_rec`.

---

### Step 7 — Run the application

```cmd
cd D:\Apps\PDF2DOCX-OCR
.venv\Scripts\activate.bat
python gui_app.py
```

#### GUI settings (recommended)

| Setting | Value |
|---|---|
| Conversion Mode | **Exact** (visual layout) |
| OCR Engine | **PaddleOCR** |
| Language | English (`en`) or your language |
| DPI | **150** (stable/faster) or 200 |

#### CLI examples

**Exact layout (recommended):**

```cmd
python main.py "C:\path\input.pdf" "C:\path\output.docx" --mode exact --engine paddleocr --lang en --dpi 150
```

**Structure (reading-order blocks/tables):**

```cmd
python main.py "C:\path\input.pdf" "C:\path\output.docx" --mode structure --lang en --dpi 150
```

**Legacy text-only:**

```cmd
python main.py "C:\path\input.pdf" "C:\path\output.docx" --mode text --engine paddleocr --lang en
```

**Tesseract (only if installed):**

```cmd
python main.py "C:\path\input.pdf" "C:\path\output.docx" --mode text --engine tesseract --lang eng
```

---

## Quick copy/paste — full offline install

```cmd
cd D:\Apps\PDF2DOCX-OCR
python -m venv .venv
.venv\Scripts\activate.bat
pip install --no-index --find-links=wheels -r requirements-wheels.txt
pip install --no-index --find-links=wheels --find-links=wheels\paddleocr -r requirements-paddleocr-wheels.txt
xcopy /E /I /Y offline_models\official_models %USERPROFILE%\.paddlex\official_models
python -c "import paddleocr, paddlex, fitz; print('Install OK')"
python gui_app.py
```

Install **Python 3.12** from USB before these commands.

---

## Refreshing the offline bundle (internet PC)

```powershell
cd "D:\path\to\PDF2DOCX-OCR"
.\.venv\Scripts\Activate.ps1
# Optional: warm model cache
python main.py samples\resnet_scanned_p1.pdf samples\_warm.docx --mode exact --dpi 150
# Download wheels + copy models
powershell -ExecutionPolicy Bypass -File .\scripts\download_offline_bundle.ps1
```

Then recopy `wheels\`, `wheels\paddleocr\`, and `offline_models\` to USB.

---

## Troubleshooting

### `python` is not recognized

Reinstall Python **3.12** with **Add to PATH**. Open a new Command Prompt.

### Wrong Python version / `cp312` wheel errors

```cmd
python --version
```

Must be **3.12.x**. If you see 3.14 or 3.11, install 3.12 and recreate `.venv`:

```cmd
rmdir /s /q .venv
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
```

### `Could not find a version that satisfies the requirement`

Wheels missing or wrong find-links path:

```cmd
dir wheels\*.whl
dir wheels\paddleocr\*.whl
```

### PaddleOCR / PP-Structure fails looking for models

Models not copied:

```cmd
dir %USERPROFILE%\.paddlex\official_models
xcopy /E /I /Y offline_models\official_models %USERPROFILE%\.paddlex\official_models
```

### Access violation / crash on Windows CPU

Already mitigated in code (`enable_mkldnn=False`, PP-OCRv4 mobile). Prefer `--dpi 150`.

### `tesseract is not installed`

You selected Tesseract engine without installing the binary. Switch GUI/CLI to **PaddleOCR**, or install Tesseract from USB.

### PowerShell scripts blocked

Use `cmd` + `.venv\Scripts\activate.bat` and the `pip install --no-index ...` commands above.

---

## Package reference (current offline bundle)

### Core (`wheels/` — ~17 files, ~87 MB)

PyMuPDF, python-docx, Pillow, opencv-python-headless, numpy, pytesseract, langdetect, tqdm, pytest, …

### Paddle (`wheels/paddleocr/` — ~91 files, ~257 MB)

paddlepaddle, paddleocr, paddlex\[ocr\] and dependencies (pandas, opencv-contrib-python, scikit-learn, …)

### Models (`offline_models/official_models/` — ~1.18 GB)

Includes layout + OCR models used by `exact` / `structure` (e.g. `PP-DocLayout_plus-L`, `PP-OCRv4_mobile_det`, `en_PP-OCRv4_mobile_rec`, table models, …)

### Not in the wheel/model bundle

| Item | Notes |
|---|---|
| Python 3.12 installer | Copy `python-3.12.x-amd64.exe` separately |
| Tesseract binary | Optional; only for `--engine tesseract` |

---

## Summary

| Step | Action | Internet? |
|---|---|---|
| A | Prepare USB (Python 3.12 + project + wheels + models) | Once, on a connected PC |
| 1 | Install Python **3.12** | No |
| 2 | Copy project to disk | No |
| 3 | Create `.venv` | No |
| 4 | Install core wheels | No |
| 5 | Install PaddleOCR wheels | No |
| 6 | Copy `offline_models` → `%USERPROFILE%\.paddlex\official_models` | No |
| 7 | `python gui_app.py` or `python main.py ... --mode exact` | No |

After Part A, the offline PC does not need internet.
