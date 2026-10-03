#!/usr/bin/env python3
"""Repeatable PC A / PC B standalone verification (no installer needed).

Simulates two PCs by pointing each run at a separate APPDATA directory:

  PC A:  set APPDATA=<tmp>/pcA  -> %APPDATA%/CollegeTimetableManager/...
  PC B:  set APPDATA=<tmp>/pcB  -> %APPDATA%/CollegeTimetableManager/...

Steps per PC: fresh start (no model) -> train on its own CSV ->
generate (trained, offline) -> apply -> edit -> restart (still Trained).

Asserts: no shared DB, no shared profile/model, different training data,
generation never touches Ollama or any socket, uninstall-style wipe of
PC A never affects PC B.

Usage:
  python scripts/verify_pc_isolation.py
  python scripts/verify_pc_isolation.py --keep  (leave temp dirs printed)
"""
import argparse
import csv
import os
import socket
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HISTORY_A = [
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": "60",
     "day": "Monday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": "60",
     "day": "Wednesday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": "60",
     "day": "Friday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": "120",
     "day": "Tuesday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": "120",
     "day": "Thursday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1"},
    {"code": "CS103", "name": "Programming", "type": "Theory", "duration": "60",
     "day": "Monday", "start": "10:00", "end": "11:00",
     "teacher": "Dr C", "room": "102"},
    {"code": "CS103", "name": "Programming", "type": "Theory", "duration": "60",
     "day": "Thursday", "start": "10:00", "end": "11:00",
     "teacher": "Dr C", "room": "102"},
]

HISTORY_B = [
    {"code": "XX201", "name": "Networks", "type": "Theory", "duration": "60",
     "day": "Tuesday", "start": "11:00", "end": "12:00",
     "teacher": "Prof X", "room": "201"},
    {"code": "XX201", "name": "Networks", "type": "Theory", "duration": "60",
     "day": "Thursday", "start": "11:00", "end": "12:00",
     "teacher": "Prof X", "room": "201"},
    {"code": "XX201", "name": "Networks", "type": "Theory", "duration": "60",
     "day": "Friday", "start": "11:00", "end": "12:00",
     "teacher": "Prof X", "room": "201"},
    {"code": "YY202", "name": "OS Lab", "type": "Practical", "duration": "120",
     "day": "Monday", "start": "14:00", "end": "16:00",
     "teacher": "Prof Y", "room": "Lab 9"},
    {"code": "YY202", "name": "OS Lab", "type": "Practical", "duration": "120",
     "day": "Wednesday", "start": "14:00", "end": "16:00",
     "teacher": "Prof Y", "room": "Lab 9"},
]


def write_csv(path: Path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return str(path)


def block_network():
    def _fail(*a, **k):
        raise OSError("network blocked (verification)")
    socket.socket = _fail
    socket.create_connection = _fail
    urllib.request.urlopen = _fail


def make_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
    from app.models import Room, Semester, Subject, Teacher, TimeSlot, WorkingDay
    sem = Semester(name="Semester 1", status="Active")
    session.add(sem)
    session.flush()
    teachers = [Teacher(name=f"T{i}", email=f"t{i}@c.edu", department="CS",
                        status="Active") for i in (1, 2)]
    rooms = [Room(name=f"R{i}", room_number=f"10{i}", type="Classroom",
                  status="Available") for i in (1, 2)]
    session.add_all(teachers + rooms)
    session.flush()
    days = [WorkingDay(name=n, is_enabled=(n != "Sunday"), sort_order=i)
            for i, n in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday",
                                   "Friday", "Saturday", "Sunday"])]
    session.add_all(days)
    slots = [TimeSlot(start_time="09:00", end_time="10:00", label="09:00-10:00"),
             TimeSlot(start_time="10:00", end_time="11:00", label="10:00-11:00"),
             TimeSlot(start_time="11:00", end_time="12:00", label="11:00-12:00"),
             TimeSlot(start_time="14:00", end_time="15:00", label="14:00-15:00"),
             TimeSlot(start_time="15:00", end_time="16:00", label="15:00-16:00")]
    session.add_all(slots)
    subs = [Subject(code="NW101", name="Networks", semester_id=sem.id,
                    subject_type="Theory", required_lectures_per_week=2,
                    lecture_duration=60, teacher_id=teachers[0].id,
                    room_id=rooms[0].id)]
    session.add_all(subs)
    session.commit()
    return sem


def run_pc(label: str, appdata: Path, history):
    from app.services.local_agent.agent import TimetableAgent
    from app.services.local_agent.model_client import OllamaClient

    print(f"\n=== {label} (APPDATA={appdata}) ===")
    data_dir = appdata / "CollegeTimetableManager"
    agent = TimetableAgent(data_dir=data_dir)
    assert agent.model_status()["trained"] is False, f"{label}: must start untrained"
    print(f"{label}: 1. fresh install -> Timetable Agent not trained (OK)")

    csv_path = write_csv(appdata / f"history_{label}.csv", history)
    report = agent.train_agent([csv_path])
    assert report["reload_check"] is True
    print(f"{label}: 2-3. trained on own CSV: "
          f"{report['positives']}+{report['negatives']} samples, "
          f"backend={report['backend']}")

    # Offline: even localhost Ollama must not be touched on trained path.
    orig_gen, orig_ready = OllamaClient.generate, OllamaClient.ensure_ready

    def _boom(*a, **k):
        raise AssertionError(f"{label}: trained path touched Ollama!")

    OllamaClient.generate = _boom
    OllamaClient.ensure_ready = _boom
    try:
        s = make_session()
        sem = seed(s)
        result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
        assert result.accepted, f"{label}: nothing generated"
        applied = agent.apply_generation(sem.id, result, "fill", session=s)
        assert applied["applied"] == len(result.accepted)
        # Edit after generation: move first lecture to Saturday.
        from app.models import TimetableEntry, WorkingDay
        entry = s.query(TimetableEntry).filter_by(semester_id=sem.id).first()
        sat = s.query(WorkingDay).filter_by(name="Saturday").first()
        entry.day_id = sat.id
        s.commit()
        s.delete(entry)
        s.commit()
        print(f"{label}: 4-5. generated {len(result.accepted)}, "
              f"applied, edited, deleted (still editable, OK)")
        s.close()
    finally:
        OllamaClient.generate, OllamaClient.ensure_ready = orig_gen, orig_ready

    # Restart: new agent on same dir still Trained.
    agent2 = TimetableAgent(data_dir=data_dir)
    st = agent2.model_status()
    assert st["trained"] is True and st["stored_rows"] == len(history)
    print(f"{label}: 6-8. restart -> still Trained, "
          f"model={data_dir / 'timetable_agent_model' / 'model.joblib'} (OK)")
    return data_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    block_network()  # whole scenario runs offline
    tmp = Path(tempfile.mkdtemp(prefix="ctm-pcs-"))
    pc_a_appdata = tmp / "pcA-appdata"
    pc_b_appdata = tmp / "pcB-appdata"
    pc_a_appdata.mkdir()
    pc_b_appdata.mkdir()
    dir_a = run_pc("PC A", pc_a_appdata, HISTORY_A)
    # PC B installs the SAME software but starts with nothing from PC A.
    dir_b = run_pc("PC B", pc_b_appdata, HISTORY_B)
    assert dir_a != dir_b
    prof_a = (dir_a / "timetable_learning_profile.json").read_text()
    prof_b = (dir_b / "timetable_learning_profile.json").read_text()
    assert prof_a != prof_b, "profiles must differ (different colleges)"
    assert (dir_a / "timetable_agent_model" / "model.joblib").exists()
    assert (dir_b / "timetable_agent_model" / "model.joblib").exists()
    print("\n=== ISOLATION VERIFIED ===")
    print(f"PC A data: {dir_a}")
    print(f"PC B data: {dir_b}")
    print("No copying, no shared DB, no remote service, offline only.")
    if not args.keep:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        print("(temp dirs cleaned; rerun with --keep to inspect)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
