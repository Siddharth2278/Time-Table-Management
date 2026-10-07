"""Phase 7 tests: production baseline workflow (real-data ready).

Uses synthetic fixtures as stand-ins for real college histories; the
workflow (train -> export -> validate -> seed -> generate -> adapt) is what
is proven. Never asserts model quality beyond structural training metrics.
"""
import csv
import json
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Room, Semester, Subject, Teacher, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.conflict_service import ConflictService
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.schemas import LearningError

HISTORY = [
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


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
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
            for i, n in enumerate(["Monday", "Tuesday", "Wednesday",
                                   "Thursday", "Friday", "Saturday",
                                   "Sunday"])]
    session.add_all(days)
    slots = [TimeSlot(start_time="09:00", end_time="10:00", label="09:00-10:00"),
             TimeSlot(start_time="10:00", end_time="11:00", label="10:00-11:00"),
             TimeSlot(start_time="11:00", end_time="12:00", label="11:00-12:00"),
             TimeSlot(start_time="14:00", end_time="15:00", label="14:00-15:00"),
             TimeSlot(start_time="15:00", end_time="16:00", label="15:00-16:00")]
    session.add_all(slots)
    subjects = [Subject(code="NW101", name="Networks", semester_id=sem.id,
                        subject_type="Theory",
                        required_lectures_per_week=2, lecture_duration=60,
                        teacher_id=teachers[0].id, room_id=rooms[0].id)]
    session.add_all(subjects)
    session.commit()
    return sem


# ---- real baseline build workflow ----

def test_production_export_from_real_files(tmp_path):
    """build_baseline.py path: files -> production baseline with report data."""
    from app.services.local_agent.baseline import (
        export_baseline, validate_baseline_dir,
    )
    first = write_csv(str(tmp_path / "sem1.csv"), HISTORY[:4])
    second = write_csv(str(tmp_path / "sem2.csv"), HISTORY[4:])
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([first, second])
    out = export_baseline(tmp_path / "admin", tmp_path / "prod",
                          kind="production")
    manifest = validate_baseline_dir(tmp_path / "prod")
    assert manifest["baseline_kind"] == "production"
    assert manifest["lectures"] == len(HISTORY)
    assert manifest["positives"] > 0 and manifest["negatives"] > 0
    assert manifest["backend"] in ("sklearn-hgb", "stdlib-logreg")
    assert manifest["source_files"] == 2
    assert manifest["separation"] is not None


def test_sample_kind_marked(tmp_path):
    from app.services.local_agent.baseline import (
        export_baseline, validate_baseline_dir,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    out = export_baseline(tmp_path / "admin", tmp_path / "dev", kind="sample")
    assert validate_baseline_dir(tmp_path / "dev")["baseline_kind"] == "sample"
    with pytest.raises(LearningError):
        export_baseline(tmp_path / "admin", tmp_path / "bad", kind="demo")


def test_sanitized_metadata_has_no_local_paths(tmp_path):
    from app.services.local_agent.baseline import export_baseline
    deep = tmp_path / "Users" / "someone" / "college"
    deep.mkdir(parents=True)
    path = write_csv(str(deep / "history.csv"), HISTORY)
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([path])
    out = export_baseline(tmp_path / "admin", tmp_path / "prod",
                          kind="production")
    manifest = out["manifest"]
    blob = json.dumps(manifest)
    assert str(tmp_path) not in blob
    assert "someone" not in blob
    assert manifest["sources"] == ["history.csv"]
    assert manifest["source_files"] == 1


def test_require_baseline_release_gate(monkeypatch):
    """REQUIRE_BASELINE=1 fails on the sample baseline in this repo."""
    import build
    monkeypatch.setenv("REQUIRE_BASELINE", "1")
    with pytest.raises(SystemExit):
        build.verify_baseline_package()
    monkeypatch.delenv("REQUIRE_BASELINE")
    build.verify_baseline_package()  # sample validates for dev builds.


# ---- fresh install: seed + immediate generation ----

def test_fresh_install_immediate_generation(tmp_path, monkeypatch):
    import socket
    import urllib.request
    from app.services.local_agent.baseline import (
        active_origin, export_baseline, seed_active_from_baseline,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    export_baseline(tmp_path / "admin", tmp_path / "prod", kind="production")

    fresh = tmp_path / "pcB"
    assert TimetableAgent(data_dir=fresh).model_status()["trained"] is False
    info = seed_active_from_baseline(fresh, bundled=tmp_path / "prod")
    assert info and info["seeded"] is True
    agent_b = TimetableAgent(data_dir=fresh)
    assert agent_b.model_status()["trained"] is True
    assert active_origin(fresh)["origin"] == "bundled-production-baseline"

    def _fail(*a, **k):
        raise OSError("network blocked")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    monkeypatch.setattr(OllamaClient, "generate", _fail)
    monkeypatch.setattr(OllamaClient, "ensure_ready", _fail)
    s = make_session()
    sem = seed(s)
    # No train_agent call on PC B: generate straight from the seeded model.
    result = agent_b.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_local_training_marks_origin_local(tmp_path):
    from app.services.local_agent.baseline import (
        active_origin, export_baseline, seed_active_from_baseline,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    export_baseline(tmp_path / "admin", tmp_path / "prod", kind="production")
    fresh = tmp_path / "pcB"
    seed_active_from_baseline(fresh, bundled=tmp_path / "prod")
    assert active_origin(fresh)["origin"] == "bundled-production-baseline"
    TimetableAgent(data_dir=fresh).update_training(
        [write_csv(str(tmp_path / "more.csv"), HISTORY[:5])])
    assert active_origin(fresh)["origin"] == "local"


# ---- adaptive preserves baseline + rollback ----

def test_adaptive_preserves_baseline_and_rolls_back(tmp_path):
    from app.services.local_agent import adaptive
    from app.services.local_agent.baseline import (
        export_baseline, seed_active_from_baseline,
    )
    from app.services.local_agent import model_versions
    old_min = adaptive.get_setting("adaptive_min_examples")
    adaptive.set_setting("adaptive_min_examples", "1")
    try:
        agent = TimetableAgent(data_dir=tmp_path / "admin")
        agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
        export_baseline(tmp_path / "admin", tmp_path / "prod",
                        kind="production")
        fresh = tmp_path / "pcB"
        seed_active_from_baseline(fresh, bundled=tmp_path / "prod")
        recovery = (fresh / "timetable_agent_model" / "baseline"
                    / "model.joblib").read_bytes()
        good = dict(HISTORY[0])
        good["source"] = "manual-edit"
        adaptive.record_feedback([good], fresh)
        report = adaptive.maybe_retrain(fresh)
        assert report and report["feedback_consumed"] == 1
        # Baseline recovery copy untouched; active model usable.
        assert (fresh / "timetable_agent_model" / "baseline"
                / "model.joblib").read_bytes() == recovery
        assert TimetableAgent(data_dir=fresh).model_status()["trained"] is True
        versions = model_versions.list_versions(fresh)
        assert len(versions) >= 2  # baseline-seed + pre-adaptive
        model_versions.rollback_to_version(fresh, versions[0]["version"])
        assert TimetableAgent(data_dir=fresh).model_status()["trained"] is True
    finally:
        adaptive.set_setting("adaptive_min_examples", old_min)


# ---- PC isolation with baselines ----

def test_pc_isolation_baselines(tmp_path):
    from app.services.local_agent.baseline import (
        active_origin, export_baseline, seed_active_from_baseline,
    )
    from app.services.local_agent import adaptive
    a_admin, b_admin = tmp_path / "a-admin", tmp_path / "b-admin"
    TimetableAgent(data_dir=a_admin).train_agent(
        [write_csv(str(tmp_path / "ha.csv"), HISTORY)])
    other = [dict(r, code="ZZ") for r in HISTORY[:5]]
    TimetableAgent(data_dir=b_admin).train_agent(
        [write_csv(str(tmp_path / "hb.csv"), other)])
    export_baseline(a_admin, tmp_path / "prodA", kind="production")
    export_baseline(b_admin, tmp_path / "prodB", kind="production")
    a_pc, b_pc = tmp_path / "a-pc", tmp_path / "b-pc"
    seed_active_from_baseline(a_pc, bundled=tmp_path / "prodA")
    seed_active_from_baseline(b_pc, bundled=tmp_path / "prodB")
    a_status = TimetableAgent(data_dir=a_pc).model_status()
    b_status = TimetableAgent(data_dir=b_pc).model_status()
    assert a_status["stored_rows"] == len(HISTORY)
    assert b_status["stored_rows"] == 5
    adaptive.record_feedback([dict(HISTORY[0], source="manual-edit")], a_pc)
    assert len(adaptive.pending_feedback(a_pc)) == 1
    assert adaptive.pending_feedback(b_pc) == []
    assert active_origin(a_pc)["origin"] == "bundled-production-baseline"
    assert active_origin(b_pc)["origin"] == "bundled-production-baseline"


# ---- installer / spec production safety ----

def test_production_safety_no_user_data_bundled():
    root = Path(__file__).resolve().parents[1]
    iss = (root / "installer" / "CollegeTimetableSetup.iss").read_text(
        encoding="utf-8")
    sources = [l for l in iss.splitlines()
               if l.strip().lower().startswith("source:")]
    bundled = " ".join(sources).lower()
    for forbidden in ("timetable.db", "training_rows.jsonl",
                      "timetable_learning_profile", "feedback",
                      "pre-restore"):
        assert forbidden not in bundled
    spec = (root / "CollegeTimetable.spec").read_text(encoding="utf-8")
    assert "baseline_agent" in spec
    baseline = root / "assets" / "baseline_agent"
    names = sorted(p.name for p in baseline.iterdir())
    assert names == ["manifest.json", "metadata.json", "model.joblib",
                     "timetable_learning_profile.json", "training_rows.jsonl"]
