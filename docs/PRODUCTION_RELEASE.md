# Production release workflow (real college baseline)

This is the exact workflow for shipping an already-trained model to
another PC. The 7-lecture sample in `assets/baseline_agent/` is development
data only and is rejected for production releases (`REQUIRE_BASELINE=1`).

## 1. Build the production baseline (admin PC)

Put your historical timetable files in a local folder (CSV, XLSX or JSON
in the usual timetable format), then:

```powershell
python scripts/build_baseline.py <file1> <file2> ...
```

Mixed formats are accepted (`.csv` / `.xlsx` / `.xls` / `.pdf` / `.jpg` /
`.jpeg` / `.png` / `.webp` / `.bmp`):

```powershell
python scripts/build_baseline.py timetable.jpg timetable.pdf timetable.xlsx
```

Each file is detected, extracted offline into normalized records,
validated and combined before training. In the application, image/PDF
imports open a review table where you edit, delete, add and approve rows;
only approved rows train the model. Image/PDF OCR runs on this PC only
(Tesseract); structured files work without it.

The script prints a report (`Files / Lectures / Positive / Negative /
Backend / Training time / Model size / Separation / Feature schema /
Model version / Baseline kind / Baseline status`). It exits non-zero
unless validation passes. Only `production`-kind baselines built from
your files are accepted for release; release metadata records file
basenames and counts only (no local paths).

## 2. Verify the baseline

```powershell
python -c "from app.services.local_agent.baseline import validate_baseline_dir; print(validate_baseline_dir('assets/baseline_agent'))"
python -m pytest tests/test_phase7_production_baseline.py -q
```

## 3. Build the production EXE and installer

```powershell
$env:REQUIRE_BASELINE = "1"
python build.py
```

This validates the baseline, runs all tests, builds with PyInstaller
(baseline packed inside the EXE), smoke-tests, and builds
`dist/CollegeTimetableSetup.exe` with Inno Setup. With
`REQUIRE_BASELINE=1` the build fails if the baseline is missing,
invalid, or a sample.

## 4. Install on the other Windows PC

1. Run `CollegeTimetableSetup.exe` (no Python or Ollama required).
2. Launch the app — first launch copies the baseline to
   `%APPDATA%\CollegeTimetableManager\` as the active model plus a
   read-only recovery copy. Existing data is never overwritten.
3. Confirm `Trained Timetable Agent Ready — current model is the bundled
   production baseline` in Timetable Intelligence.
4. Choose `Trained Local Model` and generate a timetable immediately
   (no retraining needed).
5. Edit/save the timetable; edits are conflict-validated.
6. Import new timetable data or accept more schedules to collect
   feedback (`Update Agent` retrains past the threshold; see Settings →
   Adaptive Learning).
7. Restart and confirm the trained state persists.

## Notes

- The trained model only suggests preferences; the existing constraint
  solver enforces conflicts, availability, rooms and breaks.
- Training metrics (rows, separation) describe fit to your history, not
  real-world accuracy. Compare generated output on conflicts, workload,
  room usage, daily distribution and pattern similarity before trusting it.
