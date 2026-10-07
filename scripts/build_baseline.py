#!/usr/bin/env python3
"""Build a genuinely fitted baseline agent into assets/baseline_agent/.

Usage:
    python scripts/build_baseline.py file1.csv file2.xlsx timetable.jpg scanned.pdf

Mixed file types are accepted (.csv/.xlsx/.xls/.pdf/.jpg/.jpeg/.png/
.webp/.bmp): each file is detected, extracted offline into normalized
records, validated, combined, and trained through the existing ML
pipeline. With real historical files this produces a PRODUCTION baseline.
With no files it trains on built-in development data and marks the package
as a SAMPLE baseline (never ship a sample as a production model).

The script loads + validates every file, trains the real local timetable
model, rebuilds the learned profile, validates the persisted model, and
writes metadata, checksums and manifest. It never claims success unless
validation passes.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLE = [
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": 60,
     "day": "Monday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101", "source": "baseline-sample"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": 60,
     "day": "Wednesday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101", "source": "baseline-sample"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": 60,
     "day": "Friday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101", "source": "baseline-sample"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": 120,
     "day": "Tuesday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1", "source": "baseline-sample"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": 120,
     "day": "Thursday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1", "source": "baseline-sample"},
    {"code": "CS103", "name": "Programming", "type": "Theory", "duration": 60,
     "day": "Monday", "start": "10:00", "end": "11:00",
     "teacher": "Dr C", "room": "102", "source": "baseline-sample"},
    {"code": "CS103", "name": "Programming", "type": "Theory", "duration": 60,
     "day": "Thursday", "start": "10:00", "end": "11:00",
     "teacher": "Dr C", "room": "102", "source": "baseline-sample"},
]


def main() -> int:
    from app.services.local_agent import model_store
    from app.services.local_agent.baseline import (
        export_baseline, validate_baseline_dir,
    )
    files = [a for a in sys.argv[1:] if not a.startswith("-")]
    tmp = Path(tempfile.mkdtemp(prefix="ctm-baseline-"))
    kind = "production" if files else "sample"
    if files:
        from app.services.local_agent.training_dataset import load_files_as_dicts
        rows, skipped, per_file = load_files_as_dicts(files)
        print(f"Loaded {len(rows)} rows ({skipped} skipped) from {files}.")
        for entry in per_file:
            print(f"  {entry.get('file')}: {entry.get('rows')} rows, "
                  f"{entry.get('skipped')} skipped.")
        if not rows:
            print("ERROR: no usable lecture rows found for training.")
            return 1
    else:
        rows = SAMPLE
        print("No files supplied: training a SAMPLE baseline on "
              "development data (not for production release).")
    report = model_store.train_from_rows(rows, source_label="baseline",
                                         data_dir=tmp, replace=True)
    print(f"Trained: {report['positives']}+{report['negatives']} samples, "
          f"backend={report['backend']}, "
          f"separation={report.get('separation', '?')}.")
    from app.services.local_agent.agent import TimetableAgent
    agent = TimetableAgent(data_dir=tmp)
    agent._verify_persisted_model(report)
    agent._rebuild_profile_from_dataset()
    dest = ROOT / "assets" / "baseline_agent"
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    info = export_baseline(tmp, dest, kind=kind)
    # Independent validation of exactly what was written.
    manifest = validate_baseline_dir(dest)
    model_bytes = (dest / "model.joblib").stat().st_size
    print("")
    print(f"Files: {manifest.get('source_files', len(files) if files else 1)}")
    print(f"Lectures: {manifest.get('lectures', '?')}")
    print(f"Positive samples: {manifest.get('positives', '?')}")
    print(f"Negative samples: {manifest.get('negatives', '?')}")
    print(f"Backend: {manifest.get('backend', '?')}")
    print(f"Training time: {report.get('train_seconds', '?')} seconds")
    print(f"Model size: {model_bytes} bytes")
    print(f"Separation: {manifest.get('separation', '?')}")
    print(f"Feature schema: {manifest.get('feature_schema', '?')}")
    print(f"Model version: {manifest.get('model_version', '?')}")
    print(f"Baseline kind: {manifest.get('baseline_kind', '?')}")
    print(f"Baseline status: VALID ({dest})")
    _ = info
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
