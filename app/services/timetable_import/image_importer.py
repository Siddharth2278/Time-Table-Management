"""Image extractor: fully offline OCR (Pillow/cv2 + local Tesseract).

Never trains on pixels: the image is preprocessed, OCR produces words with
bounding boxes, and the shared table reconstruction maps them into canonical
records. OCR failures raise understandable errors, never tracebacks.
"""
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List

from app.services.timetable_import.exceptions import TimetableImportError
from app.services.timetable_import.models import FileExtraction
from app.services.timetable_import.registry import MAX_IMAGE_DIM
from app.services.timetable_import import table_normalizer as norm

OCR_UNAVAILABLE = (
    "Local OCR is not available. Install Tesseract OCR on this PC "
    "(https://github.com/UB-Mannheim/tesseract/wiki) or install the "
    "packaged OCR runtime, then retry. Structured files (.csv/.xlsx) "
    "keep working without it.")


def find_tesseract_cmd() -> str | None:
    """Locate the Tesseract binary: env, bundled ocr/, then PATH."""
    candidates = []
    env_cmd = (os.environ.get("TESSERACT_CMD", "") or "").strip()
    if env_cmd:
        candidates.append(Path(env_cmd))
    try:
        base = getattr(sys, "_MEIPASS", None)
        if base:
            candidates.append(Path(base) / "ocr" / "tesseract.exe")
            candidates.append(Path(base) / "ocr" / "tesseract")
    except Exception:
        pass
    here = Path(__file__).resolve()
    candidates.append(here.parents[4] / "ocr" / "tesseract.exe")
    candidates.append(here.parents[4] / "ocr" / "tesseract")
    for path in candidates:
        try:
            if path.is_file():
                return str(path)
        except Exception:
            continue
    return shutil.which("tesseract")


def check_ocr_available() -> Dict[str, object]:
    """Report OCR readiness without raising. Used by UI and tests."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "pytesseract is not installed"}
    cmd = find_tesseract_cmd()
    if not cmd:
        return {"available": False, "reason": "tesseract-binary-missing"}
    return {"available": True, "command": cmd}


def preprocess_image(path: str):
    """Grayscale + upscale + contrast (+cv2 denoise/threshold when present).

    Returns a Pillow image ready for Tesseract. Pure Pillow fallback when
    OpenCV is absent, so the pipeline never hard-requires cv2.
    """
    from PIL import Image, ImageOps
    try:
        image = Image.open(path)
    except Exception as e:
        raise TimetableImportError(f"Could not read this image: {e}")
    if image.mode != "RGB":
        try:
            image = image.convert("RGB")
        except Exception as e:
            raise TimetableImportError(f"Could not read this image: {e}")
    width, height = image.size
    if max(width, height) > MAX_IMAGE_DIM:
        raise TimetableImportError(
            f"Image is too large ({width}x{height}); "
            f"the limit is {MAX_IMAGE_DIM}px per side.")
    if max(width, height) < 1:
        raise TimetableImportError("Could not read this image.")
    # Upscale small images: Tesseract needs ~300 DPI equivalent.
    target = 2200
    scale = max(1.0, target / max(width, height))
    if scale > 1.0:
        image = image.resize((int(width * scale), int(height * scale)))
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    try:
        import cv2
        import numpy as np
        data = np.array(gray)
        data = cv2.fastNlMeansDenoising(data, None, 9, 7, 21)
        _, data = cv2.threshold(data, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        from PIL import Image as _Image
        return _Image.fromarray(data)
    except ImportError:
        return gray
    except Exception:
        return gray


def ocr_words(image) -> List[Dict[str, object]]:
    """Run local Tesseract; return words with boxes + confidence."""
    status = check_ocr_available()
    if not status["available"]:
        raise TimetableImportError(OCR_UNAVAILABLE)
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        raise TimetableImportError(OCR_UNAVAILABLE)
    cmd = status.get("command")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = str(cmd)
    try:
        data = pytesseract.image_to_data(image, output_type=Output.DICT)
    except Exception:
        raise TimetableImportError(
            "Could not confidently detect a timetable structure. "
            "Try a clearer image.")
    words = []
    count = len(data.get("text", []))
    for i in range(count):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        words.append({"text": text,
                      "x0": data["left"][i], "y0": data["top"][i],
                      "x1": data["left"][i] + data["width"][i],
                      "y1": data["top"][i] + data["height"][i],
                      "conf": conf})
    return words


def extract(path: str, label: str) -> FileExtraction:
    image = preprocess_image(path)
    words = ocr_words(image)
    records, warnings = norm.words_to_records(words, label)
    if not records:
        raise TimetableImportError(
            "No timetable data was detected in this file. "
            + (" ".join(warnings) if warnings else ""))
    return FileExtraction(file=label,
                          file_type="." + path.lower().rsplit(".", 1)[-1],
                          method="ocr", records=records, warnings=warnings)
