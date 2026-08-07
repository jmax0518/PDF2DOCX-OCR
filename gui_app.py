#!/usr/bin/env python3
"""Tkinter desktop GUI for the PDF -> OCR -> DOCX pipeline.

Run with:
    python gui_app.py

No extra dependencies beyond the project's requirements.txt -- Tkinter ships
with the standard Python installer on Windows/macOS. On some Linux distros
you may need to install it separately (e.g. `sudo apt install python3-tk`).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pdf2docx_ocr.config import OCRConfig
from pdf2docx_ocr.core.pipeline import convert_pdf_to_docx
from pdf2docx_ocr.utils.language_utils import to_paddleocr_code, to_tesseract_code

# (display name, ISO 639-1 code) shown as checkboxes for quick selection.
LANGUAGE_OPTIONS = [
    ("English", "en"),
    ("French", "fr"),
    ("German", "de"),
    ("Spanish", "es"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Russian", "ru"),
    ("Chinese (Simplified)", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Arabic", "ar"),
]


class PDFOcrApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF to Editable Word (OCR)")
        self.geometry("640x760")
        self.minsize(600, 680)

        self._progress_queue: "queue.Queue" = queue.Queue()
        self._worker_thread: threading.Thread | None = None

        self._build_widgets()
        self.after(150, self._poll_progress_queue)

    # ------------------------------------------------------------------ UI --
    def _build_widgets(self):
        pad = {"padx": 10, "pady": 6}

        # --- Input / output files ---
        file_frame = ttk.LabelFrame(self, text="Files")
        file_frame.pack(fill="x", **pad)

        ttk.Label(file_frame, text="Input PDF:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.input_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.input_var).grid(
            row=0, column=1, sticky="ew", padx=6, pady=4
        )
        ttk.Button(file_frame, text="Browse...", command=self._browse_input).grid(
            row=0, column=2, padx=6, pady=4
        )

        ttk.Label(file_frame, text="Output DOCX:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.output_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.output_var).grid(
            row=1, column=1, sticky="ew", padx=6, pady=4
        )
        ttk.Button(file_frame, text="Browse...", command=self._browse_output).grid(
            row=1, column=2, padx=6, pady=4
        )
        file_frame.columnconfigure(1, weight=1)

        # --- Mode ---
        mode_frame = ttk.LabelFrame(self, text="Conversion Mode")
        mode_frame.pack(fill="x", **pad)

        self.mode_var = tk.StringVar(value="exact")
        ttk.Radiobutton(
            mode_frame,
            text="Exact (visual layout: positioned textboxes + figures) — recommended",
            variable=self.mode_var,
            value="exact",
        ).pack(anchor="w", padx=6, pady=2)
        ttk.Radiobutton(
            mode_frame,
            text="Structure (PP-StructureV3 reading-order blocks/tables)",
            variable=self.mode_var,
            value="structure",
        ).pack(anchor="w", padx=6, pady=2)
        ttk.Radiobutton(
            mode_frame,
            text="Layout (heuristic reading-order + residual figures)",
            variable=self.mode_var,
            value="layout",
        ).pack(anchor="w", padx=6, pady=2)
        ttk.Radiobutton(
            mode_frame,
            text="Text only (flowing paragraphs, legacy)",
            variable=self.mode_var,
            value="text",
        ).pack(anchor="w", padx=6, pady=2)

        # --- Engine ---
        engine_frame = ttk.LabelFrame(self, text="OCR Engine")
        engine_frame.pack(fill="x", **pad)

        self.engine_var = tk.StringVar(value="paddleocr")
        ttk.Radiobutton(
            engine_frame,
            text="Tesseract (fast, lightweight, CPU-only)",
            variable=self.engine_var,
            value="tesseract",
            command=self._on_engine_change,
        ).pack(anchor="w", padx=6, pady=2)
        ttk.Radiobutton(
            engine_frame,
            text="PaddleOCR (higher accuracy, multilingual/CJK, needs `pip install paddlepaddle paddleocr`)",
            variable=self.engine_var,
            value="paddleocr",
            command=self._on_engine_change,
        ).pack(anchor="w", padx=6, pady=2)

        # --- Languages ---
        lang_frame = ttk.LabelFrame(self, text="Languages")
        lang_frame.pack(fill="x", **pad)

        self.lang_vars: dict[str, tk.BooleanVar] = {}
        grid = ttk.Frame(lang_frame)
        grid.pack(fill="x", padx=6, pady=4)
        for i, (label, code) in enumerate(LANGUAGE_OPTIONS):
            var = tk.BooleanVar(value=(code == "en"))
            self.lang_vars[code] = var
            ttk.Checkbutton(grid, text=label, variable=var).grid(
                row=i // 3, column=i % 3, sticky="w", padx=4, pady=2
            )

        self.paddle_hint_var = tk.StringVar(value="")
        self.paddle_hint_label = ttk.Label(
            lang_frame, textvariable=self.paddle_hint_var, foreground="#a06000"
        )
        self.paddle_hint_label.pack(anchor="w", padx=6)

        custom_row = ttk.Frame(lang_frame)
        custom_row.pack(fill="x", padx=6, pady=4)
        ttk.Label(custom_row, text="Custom/extra codes (comma-separated, engine-specific):").pack(
            anchor="w"
        )
        self.custom_lang_var = tk.StringVar()
        ttk.Entry(custom_row, textvariable=self.custom_lang_var).pack(fill="x", pady=2)

        # --- Options ---
        opts_frame = ttk.LabelFrame(self, text="Options")
        opts_frame.pack(fill="x", **pad)

        row1 = ttk.Frame(opts_frame)
        row1.pack(fill="x", padx=6, pady=4)
        ttk.Label(row1, text="DPI:").pack(side="left")
        self.dpi_var = tk.IntVar(value=300)
        ttk.Spinbox(row1, from_=100, to=600, increment=50, textvariable=self.dpi_var, width=6).pack(
            side="left", padx=6
        )

        self.force_ocr_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts_frame, text="Force OCR (ignore existing text layer)", variable=self.force_ocr_var
        ).pack(anchor="w", padx=6, pady=2)

        self.preprocess_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_frame,
            text="Pre-process images (denoise/deskew/threshold) before OCR",
            variable=self.preprocess_var,
        ).pack(anchor="w", padx=6, pady=2)

        self.detect_lang_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts_frame,
            text="Auto-detect & annotate language per page",
            variable=self.detect_lang_var,
        ).pack(anchor="w", padx=6, pady=2)

        # --- Run + progress ---
        run_frame = ttk.Frame(self)
        run_frame.pack(fill="x", **pad)

        self.convert_button = ttk.Button(
            run_frame, text="Convert", command=self._on_convert_clicked
        )
        self.convert_button.pack(side="left")

        self.open_folder_button = ttk.Button(
            run_frame, text="Open Output Folder", command=self._open_output_folder, state="disabled"
        )
        self.open_folder_button.pack(side="left", padx=8)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", **pad)

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        self._on_engine_change()

    # -------------------------------------------------------------- helpers --
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select PDF", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                default_output = os.path.splitext(path)[0] + "_ocr.docx"
                self.output_var.set(default_output)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save DOCX as",
            defaultextension=".docx",
            filetypes=[("Word document", "*.docx")],
        )
        if path:
            self.output_var.set(path)

    def _on_engine_change(self):
        if self.engine_var.get() == "paddleocr":
            self.paddle_hint_var.set(
                "Note: PaddleOCR uses a single language per run - only the first checked language is used."
            )
        else:
            self.paddle_hint_var.set("")

    def _selected_language_codes(self) -> list[str]:
        engine = self.engine_var.get()
        checked = [code for code, var in self.lang_vars.items() if var.get()]
        custom = [c.strip() for c in self.custom_lang_var.get().split(",") if c.strip()]

        if engine == "tesseract":
            codes = [to_tesseract_code(c) for c in checked] + custom
        else:
            codes = [to_paddleocr_code(c) for c in checked] + custom
            codes = codes[:1]  # PaddleOCR only supports one language per engine instance

        return codes or (["eng"] if engine == "tesseract" else ["en"])

    def _log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _open_output_folder(self):
        output_path = self.output_var.get()
        folder = os.path.dirname(os.path.abspath(output_path)) if output_path else "."
        if not os.path.isdir(folder):
            return
        if sys.platform.startswith("win"):
            os.startfile(folder)  # noqa: S606 - trusted, user-selected local path
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)

    # ---------------------------------------------------------------- run --
    def _on_convert_clicked(self):
        input_pdf = self.input_var.get().strip()
        output_docx = self.output_var.get().strip()

        if not input_pdf or not os.path.isfile(input_pdf):
            messagebox.showerror("Missing input", "Please choose a valid input PDF file.")
            return
        if not output_docx:
            messagebox.showerror("Missing output", "Please choose where to save the output DOCX.")
            return

        config = OCRConfig(
            input_pdf=input_pdf,
            output_docx=output_docx,
            languages=self._selected_language_codes(),
            engine=self.engine_var.get(),
            mode=self.mode_var.get(),  # type: ignore[arg-type]
            dpi=self.dpi_var.get(),
            force_ocr=self.force_ocr_var.get(),
            preprocess=self.preprocess_var.get(),
            detect_language=self.detect_lang_var.get(),
            verbose=False,
        )

        self.convert_button.configure(state="disabled")
        self.open_folder_button.configure(state="disabled")
        self.progress.configure(value=0, maximum=100)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._log(
            f"Starting conversion mode={config.mode}, engine={config.engine}, "
            f"languages={config.languages} ..."
        )

        self._worker_thread = threading.Thread(target=self._run_pipeline, args=(config,), daemon=True)
        self._worker_thread.start()

    def _run_pipeline(self, config: OCRConfig):
        def on_progress(current: int, total: int, message: str):
            self._progress_queue.put(("progress", current, total, message))

        try:
            output_path = convert_pdf_to_docx(config, on_progress=on_progress)
            self._progress_queue.put(("done", output_path))
        except Exception as exc:  # surface any failure to the UI thread
            self._progress_queue.put(("error", str(exc)))

    def _poll_progress_queue(self):
        try:
            while True:
                item = self._progress_queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, current, total, message = item
                    self.progress.configure(maximum=max(total, 1), value=current)
                    self._log(message)
                elif kind == "done":
                    _, output_path = item
                    self._log(f"Done. Wrote: {output_path}")
                    self.convert_button.configure(state="normal")
                    self.open_folder_button.configure(state="normal")
                    messagebox.showinfo("Conversion complete", f"Saved to:\n{output_path}")
                elif kind == "error":
                    _, error_message = item
                    self._log(f"Error: {error_message}")
                    self.convert_button.configure(state="normal")
                    messagebox.showerror("Conversion failed", error_message)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._poll_progress_queue)


if __name__ == "__main__":
    app = PDFOcrApp()
    app.mainloop()
