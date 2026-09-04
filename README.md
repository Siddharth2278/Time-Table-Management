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
- **Settings** — college, department, year, hours, backup location
- **Offline** — SQLite local storage, no internet required
- **Persistent Storage** — `%APPDATA%\CollegeTimetableManager\timetable.db` survives reinstalls

## Technology

- Python 3.10+
- PySide6 (Qt6) for GUI
- SQLAlchemy + SQLite
- openpyxl (Excel), reportlab (PDF)
- PyInstaller + Inno Setup

## Quick Start (Development)

```bash
pip install -r requirements.txt
python run.py
```

Database is created at `%APPDATA%\CollegeTimetableManager\timetable.db` on first launch with sample data:
- 12 teachers, 14 rooms/labs, 19 subjects, 15 timetable entries

## Testing

```bash
pytest tests/test_conflict_engine.py -v
```

13 automated tests for the conflict engine.

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
