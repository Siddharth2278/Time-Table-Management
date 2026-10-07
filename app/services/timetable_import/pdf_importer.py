"""PDF extractor: text/table pages via local PyMuPDF; scanned pages via OCR.

Case A (text/table PDF): word positions are read directly with PyMuPDF —
no rendering, no network. Case B (scanned/image PDF): the page is rendered
locally to PNG bytes and run through the same offline OCR pipeline as
JPG/PNG. Every record tracks its page number, method and confidence.
"""
from typing import List

from app.services.timetable_import.exceptions import TimetableImportError
from app.services.timetable_import.models import FileExtraction, TimetableRecord
from app.services.timetable_import.registry import MAX_PDF_PAGES
from app.services.timetable_import import table_normalizer as norm


def _open(path: str):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            raise TimetableImportError(
                "PDF support needs the PyMuPDF package.")
    try:
        doc = pymupdf.open(path)
    except Exception:
        raise TimetableImportError("Could not read this PDF.")
    return doc


def _words_from_text_page(page) -> List[dict]:
    words = []
    try:
        for x0, y0, x1, y1, text, *_ in page.get_text("words"):
            text = (text or "").strip()
            if text:
                words.append({"text": text, "x0": x0, "y0": y0,
                              "x1": x1, "y1": y1, "conf": 100.0})
    except Exception:
        pass
    return words


def _words_from_scanned_page(page) -> List[dict]:
    from app.services.timetable_import import image_importer
    from PIL import Image
    import io
    try:
        pixmap = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    except Exception:
        raise TimetableImportError("Could not read this PDF.")
    words = image_importer.ocr_words(image)
    return words


def extract(path: str, label: str) -> FileExtraction:
    doc = _open(path)
    try:
        count = len(doc)
    except Exception:
        raise TimetableImportError("Could not read this PDF.")
    if count > MAX_PDF_PAGES:
        raise TimetableImportError(
            f"PDF has {count} pages; the limit is {MAX_PDF_PAGES}.")
    if count == 0:
        raise TimetableImportError("Could not read this PDF.")
    records: List[TimetableRecord] = []
    warnings: List[str] = []
    methods = set()
    for number in range(count):
        try:
            page = doc[number]
        except Exception:
            warnings.append(f"Page {number + 1}: unreadable; skipped.")
            continue
        words = _words_from_text_page(page)
        alpha = sum(1 for w in words if any(c.isalpha() for c in w["text"]))
        if alpha >= 5:
            page_records, page_warnings = norm.words_to_records(
                words, label, source_page=number + 1)
            methods.add("pdf-text")
        else:
            try:
                words = _words_from_scanned_page(page)
            except TimetableImportError as e:
                warnings.append(f"Page {number + 1}: {e}")
                continue
            page_records, page_warnings = norm.words_to_records(
                words, label, source_page=number + 1)
            for record in page_records:
                record.confidence = round(record.confidence * 0.9, 2)
            methods.add("pdf-ocr")
        records.extend(page_records)
        warnings.extend(f"Page {number + 1}: {w}" for w in page_warnings)
    try:
        doc.close()
    except Exception:
        pass
    if not records:
        raise TimetableImportError(
            "No timetable data was detected in this file. "
            + (" ".join(warnings) if warnings else ""))
    return FileExtraction(file=label, file_type=".pdf",
                          method="+".join(sorted(methods)) or "pdf",
                          records=records, warnings=warnings,
                          pages=count)
