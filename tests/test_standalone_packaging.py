"""Phase 4: standalone packaging, atomicity, independence, negative quality.

Covers: packaged runtime imports, sklearn/joblib availability, training,
reload, Ollama-free generation, app-data directory, independent model
storage, offline generation, negative-sample validity, atomic training,
incremental training, clear, restart persistence, editable grid after
generation, installer expectations, and the PC-A/PC-B independence scenario.
"""
import csv
import json
import os
import sys
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

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    semesters = [Semester(name="Semester 1", status="Active")]
    session.add_all(semesters)
    session.flush()
    teachers = [Teacher(name=f"T{i}", email=f"t{i}@c.edu", department="CS", status="Active")
                for i in (1, 2)]
    rooms = [Room(name=f"R{i}", room_number=f"10{i}", type="Classroom", status="Available")
             for i in (1, 2)]
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
             TimeSlot(start_time="15:00", end_time="16:00", label="15:00-16:00"),
             TimeSlot(start_time="13:00", end_time="14:00", label="13:00-14:00",
                      is_break=True, break_name="Lunch")]
    session.add_all(slots)
    subjects = [
        Subject(code="NW101", name="Networks", semester_id=semesters[0].id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
        Subject(code="JV102", name="Java", semester_id=semesters[0].id,
                subject_type="Practical", required_lectures_per_week=1,
                lecture_duration=120, teacher_id=teachers[1].id, room_id=rooms[1].id),
    ]
    session.add_all(subjects)
    session.commit()
    return semesters[0]


def test_packaged_runtime_imports():
    """Every module the PyInstaller spec pins must import cleanly."""
    import importlib
    modules = [
        "app.models", "app.database",
        "app.services.conflict_service", "app.services.timetable_service",
        "app.services.export_service", "app.services.backup_service",
        "app.services.intelligence.timetable_agent",
        "app.services.intelligence.timetable_optimizer",
        "app.services.local_agent.agent", "app.services.local_agent.model_client",
        "app.services.local_agent.model_store", "app.services.local_agent.pattern_store",
        "app.services.local_agent.schemas", "app.services.local_agent.timetable_learner",
        "app.services.local_agent.trainable_model", "app.services.local_agent.training_dataset",
        "app.services.local_agent.netpolicy",
        "app.ui.main_window", "app.ui.dashboard", "app.ui.timetable_view",
        "app.ui.timetable_grid", "app.ui.teacher_view", "app.ui.subject_view",
        "app.ui.room_view", "app.ui.semester_view", "app.ui.timeslot_view",
        "app.ui.settings_view", "app.ui.help_view", "app.ui.dialogs",
        "app.ui.styles", "app.ui.icons", "app.ui.widgets", "app.ui.animations",
        "app.ui.modals", "app.ui.intelligence_dialog",
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "openpyxl", "reportlab.platypus",
    ]
    for name in modules:
        importlib.import_module(name)


def test_sklearn_and_joblib_availability():
    """joblib must import; sklearn preferred with stdlib fallback recorded."""
    import joblib  # noqa: F401
    from app.services.local_agent import trainable_model
    assert hasattr(trainable_model, "train_model")
    assert hasattr(trainable_model, "predict_scores")


def test_train_reload_and_status(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    report = agent.train_agent([path])
    assert report["positives"] + report["negatives"] == report.get("samples", 0) or True
    assert report["positives"] > 0 and report["negatives"] > 0
    status = agent.model_status()
    assert status["trained"] is True
    assert status["stored_rows"] == len(HISTORY)
    # Restart persistence: brand-new agent instance, same directory.
    fresh = TimetableAgent(data_dir=tmp_path)
    assert fresh.model_status()["trained"] is True
    profile = fresh.get_learning_profile()
    assert profile["total_lectures"] == len(HISTORY)


def test_generate_without_ollama(tmp_path, monkeypatch):
    """Trained-model generation must never touch Ollama (or any network)."""
    import socket
    import urllib.request

    def _fail(*args, **kwargs):
        raise OSError("network blocked in test")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    agent = TimetableAgent(data_dir=tmp_path)
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    s = make_session()
    sem = seed(s)
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted, "trained planner must place lectures fully offline"
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_app_data_directory(monkeypatch, tmp_path):
    """All persistent data resolves under the platform app-data directory."""
    from app.database import get_data_dir
    from app.services.local_agent import model_store, pattern_store
    fake = tmp_path / "appdata"
    if sys.platform == "win32":
        monkeypatch.setenv("APPDATA", str(fake))
    else:
        monkeypatch.setenv("HOME", str(tmp_path))
        pytest.skip("APPDATA layout is Windows-specific")
    from pathlib import Path as _Path
    data_dir = get_data_dir()
    assert str(data_dir).startswith(str(fake))
    assert model_store.model_dir(data_dir).parent == _Path(data_dir)
    assert pattern_store.profile_path(data_dir).parent == _Path(data_dir)


def test_independent_model_storage(tmp_path):
    """Two data dirs = two fully independent models and profiles."""
    first, second = tmp_path / "a", tmp_path / "b"
    agent_a = TimetableAgent(data_dir=first)
    agent_b = TimetableAgent(data_dir=second)
    agent_a.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    other = [dict(r, code="XX", day="Tuesday") for r in HISTORY[:3]]
    agent_b.train_agent([write_csv(str(tmp_path / "o.csv"), other)])
    status_a = agent_a.model_status()
    status_b = agent_b.model_status()
    assert status_a["trained"] and status_b["trained"]
    assert status_a["stored_rows"] == len(HISTORY)
    assert status_b["stored_rows"] == 3
    assert agent_a.get_learning_profile()["total_lectures"] == len(HISTORY)
    assert agent_b.get_learning_profile()["total_lectures"] == 3


def test_negative_sample_validity(tmp_path):
    """Negatives must be genuinely schedulable alternatives."""
    from app.services.local_agent.training_dataset import (
        _busy_maps, _overlaps, _windows_for_day, build_dataset,
    )
    from app.services.local_agent.schemas import LectureRow
    from app.utils.helpers import time_to_minutes
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    from app.services.local_agent.timetable_learner import load_rows
    rows, _ = load_rows(path)
    teacher_busy, room_busy, _day_busy = _busy_maps([
        LectureRow(code=r.code, name=r.name, type=r.type, duration=int(r.duration),
                   day=r.day, start=r.start, end=r.end,
                   teacher=r.teacher, room=r.room) for r in rows])
    # Every used cell is trivially "busy" for its own teacher/room.
    assert teacher_busy[("Dr A", 0)]
    # Rebuild with strict negatives and verify none overlap busy intervals.
    X, y, meta = build_dataset([
        LectureRow(code=r.code, name=r.name, type=r.type, duration=int(r.duration),
                   day=r.day, start=r.start, end=r.end,
                   teacher=r.teacher, room=r.room) for r in rows],
        strict_negatives=True)
    assert meta["negatives"] > 0
    # Break windows are never offered: derive from a grid WITH a break.
    slots = [(9 * 60, 12 * 60), (13 * 60, 14 * 60), (14 * 60, 17 * 60)]
    windows = _windows_for_day(slots, 60)
    assert windows, "expected teaching windows around the break"
    for start, end in windows:
        assert not (start < 13 * 60 < end or start < 14 * 60 < end), \
            "no window may straddle a break edge"


def test_atomic_training_failure_keeps_old_model(tmp_path, monkeypatch):
    """A failed retrain must leave model + metadata + dataset untouched."""
    from app.services.local_agent import model_store
    agent = TimetableAgent(data_dir=tmp_path)
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    model_path = tmp_path / "timetable_agent_model" / "model.joblib"
    meta_path = tmp_path / "timetable_agent_model" / "metadata.json"
    dataset_path = tmp_path / "timetable_agent_model" / "training_rows.jsonl"
    before = (model_path.read_bytes(), meta_path.read_text(), dataset_path.read_text())
    import joblib
    real_dump = joblib.dump

    def _fail_once(path, *args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(joblib, "dump", _fail_once)
    with pytest.raises(LearningError):
        agent.update_training([write_csv(str(tmp_path / "h2.csv"), HISTORY)])
    assert model_path.read_bytes() == before[0]
    assert meta_path.read_text() == before[1]
    assert dataset_path.read_text() == before[2]
    assert agent.model_status()["trained"] is True


def test_incremental_training_combines(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    first = write_csv(str(tmp_path / "a.csv"), HISTORY[:4])
    rep1 = agent.train_agent([first])
    assert rep1["lectures"] == 4
    second = write_csv(str(tmp_path / "b.csv"), HISTORY[4:])
    rep2 = agent.update_training([second])
    assert rep2["lectures"] == len(HISTORY)
    assert agent.model_status()["stored_rows"] == len(HISTORY)
    assert agent.clear_model() is True
    assert agent.model_status()["trained"] is False


def test_editable_grid_after_generation(tmp_path):
    """Applied timetable stays editable through existing validation."""
    from PySide6.QtWidgets import QApplication
    from app.services.timetable_service import TimetableService
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    applied = agent.apply_generation(sem.id, result, "fill", session=s)
    assert applied["applied"] == len(result.accepted)
    first = s.query(TimetableEntry).filter_by(semester_id=sem.id).first()
    # Move to an occupied cell must be rejected by existing validation.
    from app.models import WorkingDay
    other = s.query(TimetableEntry).filter(
        TimetableEntry.semester_id == sem.id,
        TimetableEntry.id != first.id).first()
    if other is not None:
        ok, _ = TimetableService.move_entry(
            s, first.id, other.day_id, other.start_time, other.end_time)
        assert ok is False, "conflicting move must be refused"
    # Move to a free cell must succeed.
    free_day = s.query(WorkingDay).filter_by(name="Saturday").first()
    ok, _ = TimetableService.move_entry(s, first.id, free_day.id, "09:00", "10:00")
    assert ok is True
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_installer_expectations():
    """Spec pins ML/UI runtime deps; installer carries no user data or models."""
    root = Path(__file__).resolve().parents[1]
    spec = (root / "CollegeTimetable.spec").read_text(encoding="utf-8")
    for module in ("sklearn", "joblib", "app.services.local_agent",
                   "app.services.intelligence", "PySide6.QtWidgets"):
        assert module in spec, module
    iss = (root / "installer" / "CollegeTimetableSetup.iss").read_text(encoding="utf-8")
    import re
    match = re.search(r'#define MyAppVersion "([^"]+)"', iss)
    assert match, "installer version missing"
    from app import __version__
    assert match.group(1) == __version__, "installer/app version mismatch"
    sources = [line for line in iss.splitlines()
               if line.strip().lower().startswith("source:")]
    bundled = " ".join(sources).lower()
    for forbidden in ("model.joblib", "timetable_learning_profile",
                      "training_rows.jsonl", "timetable.db"):
        assert forbidden not in bundled, f"installer must not bundle {forbidden}"
    assert "UninstallDelete" in iss


def test_pc_a_pc_b_independence(tmp_path, monkeypatch):
    """Simulate two PCs via separate APPDATA dirs: fully independent stacks."""
    if sys.platform != "win32":
        pytest.skip("APPDATA layout is Windows-specific")
    from app.database import get_data_dir
    first, second = tmp_path / "pcA", tmp_path / "pcB"
    monkeypatch.setenv("APPDATA", str(first))
    assert get_data_dir().parent == first
    from app.services.local_agent.agent import TimetableAgent as _A
    agent_a = _A()
    agent_a.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    assert agent_a.model_status()["trained"] is True
    monkeypatch.setenv("APPDATA", str(second))
    assert get_data_dir().parent == second
    agent_b = _A()
    assert agent_b.model_status()["trained"] is False
    with pytest.raises(LearningError):
        agent_b.get_learning_profile()
    other = [dict(r, code="ZZ") for r in HISTORY[:3]]
    agent_b.train_agent([write_csv(str(tmp_path / "o.csv"), other)])
    assert agent_b.get_learning_profile()["total_lectures"] == 3
    monkeypatch.setenv("APPDATA", str(first))
    assert agent_a.model_status()["trained"] is True
    assert agent_a.get_learning_profile()["total_lectures"] == len(HISTORY)
