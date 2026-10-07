#!/usr/bin/env python3
"""Build a genuinely fitted baseline agent into assets/baseline_agent/.

Trains on the bundled sample history (or CSVs passed on the command line),
validates the fitted model, and exports the verified package that the
installer may bundle. Never writes placeholders: export fails unless the
model reloads and scores.
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
    from app.services.local_agent.baseline import export_baseline
    files = [a for a in sys.argv[1:] if not a.startswith("-")]
    tmp = Path(tempfile.mkdtemp(prefix="ctm-baseline-"))
    if files:
        from app.services.local_agent.training_dataset import load_files_as_dicts
        rows, skipped, _ = load_files_as_dicts(files)
        print(f"Loaded {len(rows)} rows ({skipped} skipped) from {files}.")
    else:
        rows = SAMPLE
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
    # Fresh export: remove stale package first.
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    info = export_baseline(tmp, dest)
    manifest = info["manifest"]
    print(f"Baseline exported to {dest}: {manifest.get('lectures', '?')} "
          f"lectures, backend {manifest.get('backend', '?')}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
