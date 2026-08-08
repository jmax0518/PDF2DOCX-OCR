"""Image pre-processing helpers to improve OCR accuracy on noisy scans."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def pil_to_cv(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def cv_to_pil(mat: np.ndarray) -> Image.Image:
    if len(mat.shape) == 2:
        return Image.fromarray(mat)
    return Image.fromarray(cv2.cvtColor(mat, cv2.COLOR_BGR2RGB))


def deskew(gray: np.ndarray) -> np.ndarray:
    """Estimate and correct small rotation angles using minAreaRect on text pixels."""
    coords = np.column_stack(np.where(gray < 200))
    if coords.size == 0:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    # Skip correction for negligible or clearly-wrong (near-90deg) estimates.
    if abs(angle) < 0.1 or abs(angle) > 15:
        return gray
    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def preprocess_for_ocr(image: Image.Image, deskew_enabled: bool = True) -> Image.Image:
    """Grayscale -> denoise -> (optional) deskew -> adaptive threshold.

    Returns a new PIL image; the original is left untouched.
    """
    mat = pil_to_cv(image)
    gray = cv2.cvtColor(mat, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    if deskew_enabled:
        gray = deskew(gray)

    binarized = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )
    return cv_to_pil(binarized)
