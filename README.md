# College Timetable Manager

Offline Windows desktop application for managing college timetables across 6 semesters.

## Features

- **6 Semesters** (no divisions) — each with one timetable
- **Teacher, Subject, Room/Lab management**
- **Working Days** (Mon-Sat) enable/disable
- **Custom Time Slots** with break support (30/45/60/90/120 min)
- **Timetable Builder** with semester selector grid
- **Conflict Detection** — teacher / semester / room-lab / availability / break
  - Overlap rule: `existingStart < newEnd AND existingEnd > newStart`
- **Availability** — per-teacher and per-room unavailable periods
- **Find Available Slot** — suggests valid slots
- **Drag & Drop** — move lectures with re-validation
- **Completion Tracking** — required vs scheduled per semester
- **Teacher / Room Timetables** — cross-semester views
- **Dashboard** — stats, completion, conflicts
- **Export** — PDF (printable), Excel, CSV
- **Backup & Restore** — SQLite file + JSON import/export
- **Trained Timetable Model** — learns scheduling patterns from historical
  timetables and suggests placements; the constraint solver always validates
- **Settings** — college, department, year, hours, backup location
- **Offline** — SQLite local storage, no internet required
- **Persistent Storage** — `%APPDATA%\CollegeTimetableManager\timetable.db` survives reinstalls

## Training Data Formats

Historical timetables can be imported as training data in these formats
(fully offline, no cloud or API key):

- CSV (row layouts and day/time grid layouts)
- Excel `.xlsx` / `.xls` (merged cells unfolded, grids supported)
- PDF (text/table pages read directly; scanned pages use local OCR)
- Images `.jpg` / `.jpeg` / `.png` / `.webp` / `.bmp` (local Tesseract OCR)

Image/PDF OCR runs on this PC only. Tesseract OCR is used when installed
(see `ocr/` next to the app or `TESSERACT_CMD`); structured files work
without it. Every import shows an extraction report with confidence, and
only rows you approve enter the training dataset:

```bash
python scripts/build_baseline.py timetable.jpg timetable.pdf timetable.xlsx
```

The 7-lecture sample in `assets/baseline_agent/` is development data only
and is rejected for production releases (`REQUIRE_BASELINE=1`). The real
production model exists only after training on your actual college histories.

## Technology

- Python 3.10+
- PySide6 (Qt6) for GUI
- SQLAlchemy + SQLite
- openpyxl (Excel), reportlab (PDF), PyMuPDF (PDF import), Pillow/OpenCV (image import)
- scikit-learn (local timetable model), Tesseract OCR via pytesseract (optional local runtime)
- PyInstaller + Inno Setup

## Quick Start (Development)

```bash
pip install -r requirements.txt
python run.py
```

Database is created at `%APPDATA%\CollegeTimetableManager\timetable.db` on first launch with sample data:
- 4 teachers, 4 rooms/labs, 5 subjects, 5 timetable entries (short demo; full 12/14/19/15 set via in-app sample loader)

## Testing

```bash
pytest tests/test_conflict_engine.py -v
```

14 automated tests for the conflict engine and timetable validation.

## Building Installer

```bash
python build.py
```

- Builds `dist/CollegeTimetable.exe` via PyInstaller (`CollegeTimetable.spec`)
- Builds `CollegeTimetableSetup.exe` via Inno Setup if `ISCC.exe` is on PATH

Manual:

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean CollegeTimetable.spec
# Then with Inno Setup installed:
ISCC installer/CollegeTimetableSetup.iss
```

Installer (`CollegeTimetableSetup.exe`):
- Installs to `{pf}\CollegeTimetableManager`
- Creates Start Menu shortcut
- Optional Desktop shortcut
- Preserves user data on uninstall (prompts to delete)

## Data Location

- DB: `%APPDATA%\CollegeTimetableManager\timetable.db` (Windows) or `~/.local/share/CollegeTimetableManager/timetable.db` (Linux)
- Uninstall does NOT delete data unless user confirms.

## License

MIT
