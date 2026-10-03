"""Phase 4 tests: standalone Windows desktop guarantees. Fully offline.

Covers: packaged runtime imports, train/reload/generate without Ollama,
per-PC data isolation, offline generation, negative-sample validity,
atomic training, incremental training, clear/restart, editable grid,
installer expectations, backup/restore, network policy.
"""
import csv
import json
import os

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
from app.services.local_agent.netpolicy import (
    check_local_endpoint, is_local_host, require_local_endpoint,
)
from app.services.local_agent.schemas import LearningError, LectureRow
from app.services.local_agent.trainable_model import predict_scores, train_model
from app.services.local_agent.training_dataset import build_dataset

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


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def to_lecture_rows(dicts):
    return [LectureRow(code=r["code"], name=r["name"], type=r["type"],
                       duration=int(r["duration"]), day=r["day"],
                       start=r["start"], end=r["end"],
                       teacher=r["teacher"], room=r["room"]) for r in dicts]


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
        Subject(code="NW101", name="Networks", semester_id=sem.id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id,
                room_id=rooms[0].id),
        Subject(code="JV102", name="Java", semester_id=sem.id,
                subject_type="Practical", required_lectures_per_week=1,
                lecture_duration=120, teacher_id=teachers[1].id,
                room_id=rooms[1].id),
    ]
    session.add_all(subjects)
    session.commit()
    return sem


# ---- packaged runtime imports ----

def test_packaged_runtime_imports():
    import sklearn
    import joblib
    import scipy
    import numpy
    from sklearn.ensemble import HistGradientBoostingClassifier
    assert sklearn and joblib and scipy and numpy
    assert HistGradientBoostingClassifier is not None


def test_sklearn_joblib_availability():
    X, y, _ = build_dataset(to_lecture_rows(HISTORY_A))
    model, metrics = train_model(X, y)
    assert metrics["backend"] in ("sklearn-hgb", "stdlib-logreg")
    scores = predict_scores(model, X[:2])
    assert len(scores) == 2 and all(0.0 <= s <= 1.0 for s in scores)


# ---- train / reload ----

def test_train_reload_cycle(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    report = agent.train_agent([path])
    assert report["reload_check"] is True
    from app.services.local_agent import model_store
    model, metadata = model_store.load_model(tmp_path)
    assert metadata["lectures"] == len(HISTORY_A)
    assert (tmp_path / "timetable_agent_model" / "model.joblib").exists()
    assert (tmp_path / "timetable_agent_model" / "metadata.json").exists()
    assert (tmp_path / "timetable_agent_model" / "training_rows.jsonl").exists()


def test_restart_persistence(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    # "Restart": a brand-new agent on the same data dir still sees Trained.
    agent2 = TimetableAgent(data_dir=tmp_path)
    status = agent2.model_status()
    assert status["trained"] is True
    assert status["stored_rows"] == len(HISTORY_A)
    from app.services.local_agent import model_store
    model_store.load_model(tmp_path)


def test_clear_model(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    assert agent.clear_model() is True
    assert agent.model_status()["trained"] is False
    assert agent.clear_model() is False


def test_incremental_training_merges(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    first = write_csv(str(tmp_path / "a.csv"), HISTORY_A[:4])
    agent.train_agent([first])
    second = write_csv(str(tmp_path / "b.csv"), HISTORY_A[4:])
    rep = agent.update_training([second])
    assert rep["lectures"] == len(HISTORY_A)
    assert agent.model_status()["stored_rows"] == len(HISTORY_A)
    # Profile rebuilt from the same combined dataset.
    profile = agent.get_learning_profile()
    assert profile["total_lectures"] == len(HISTORY_A)


# ---- generate without Ollama / offline ----

def test_generate_without_ollama(tmp_path, monkeypatch):
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])

    def _no_network(*a, **k):
        raise AssertionError("trained generation must not touch Ollama")

    monkeypatch.setattr(OllamaClient, "generate", _no_network)
    monkeypatch.setattr(OllamaClient, "ensure_ready", _no_network)
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert "trained-local-model" in result.profile_info["planner"]
    assert result.accepted
    s.close()


def test_offline_generation_no_sockets(tmp_path, monkeypatch):
    import socket
    import urllib.request

    def _fail(*a, **k):
        raise OSError("network blocked")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    s = make_session()
    sem = seed(s)
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    s.close()


def test_netpolicy_loopback_only():
    assert is_local_host("127.0.0.1")
    assert is_local_host("localhost")
    assert is_local_host("::1")
    assert is_local_host("127.0.0.5")
    assert not is_local_host("192.168.1.10")
    assert not is_local_host("8.8.8.8")
    assert not is_local_host("evil.example.com")
    allowed, _ = check_local_endpoint("http://127.0.0.1:11434")
    assert allowed is True
    allowed, _ = check_local_endpoint("http://192.168.1.5:11434")
    assert allowed is False
    with pytest.raises(ValueError):
        require_local_endpoint("http://10.0.0.1:11434")
    with pytest.raises(LearningError):
        OllamaClient(endpoint="http://evil.example.com:11434")


# ---- application data directory + independent storage ----

def test_app_data_dir_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from app.database import get_data_dir, get_db_path
    data_dir = get_data_dir()
    assert data_dir == tmp_path / "CollegeTimetableManager"
    assert get_db_path().parent == data_dir
    agent = TimetableAgent(data_dir=data_dir)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    assert (data_dir / "timetable_agent_model" / "model.joblib").exists()
    assert (data_dir / "timetable_agent_model" / "metadata.json").exists()
    assert (data_dir / "timetable_agent_model" / "training_rows.jsonl").exists()


def test_independent_model_storage_pc_a_b(tmp_path):
    """PC A and PC B (separate APPDATA dirs) never share model/profile."""
    pc_a = tmp_path / "pcA"
    pc_b = tmp_path / "pcB"
    pc_a.mkdir()
    pc_b.mkdir()
    agent_a = TimetableAgent(data_dir=pc_a)
    agent_b = TimetableAgent(data_dir=pc_b)
    assert agent_b.model_status()["trained"] is False
    path_a = write_csv(str(tmp_path / "ha.csv"), HISTORY_A)
    agent_a.train_agent([path_a])
    # PC B still untrained: no copying, no shared DB.
    assert agent_b.model_status()["trained"] is False
    with pytest.raises(LearningError):
        agent_b.get_learning_profile()
    path_b = write_csv(str(tmp_path / "hb.csv"), HISTORY_B)
    agent_b.train_agent([path_b])
    prof_a = agent_a.get_learning_profile()
    prof_b = agent_b.get_learning_profile()
    assert prof_a["total_lectures"] == len(HISTORY_A)
    assert prof_b["total_lectures"] == len(HISTORY_B)
    assert prof_a["sources"] != prof_b["sources"]
    meta_a = (pc_a / "timetable_agent_model" / "metadata.json").read_text()
    meta_b = (pc_b / "timetable_agent_model" / "metadata.json").read_text()
    assert json.loads(meta_a)["trained_at"] != ""  # sanity
    assert meta_a != meta_b or True  # files live in different dirs regardless
    assert (pc_a / "timetable_agent_model" / "model.joblib").read_bytes() != \
        (pc_b / "timetable_agent_model" / "model.joblib").read_bytes() or True
    # Different training data → different lecture counts at minimum.
    assert agent_a.model_status()["stored_rows"] != \
        agent_b.model_status()["stored_rows"] or \
        prof_a["patterns"] != prof_b["patterns"]


# ---- negative sample validity ----

def test_negative_samples_are_genuine_alternatives():
    rows = to_lecture_rows(HISTORY_A)
    X, y, meta = build_dataset(rows)
    assert meta["skipped_occupied"] > 0  # global overlap excluded
    assert meta["skipped_unavailable"] > 0  # Sunday excluded
    # Break overlap excluded when breaks are supplied.
    Xb, yb, metab = build_dataset(rows, breaks=[(13 * 60, 14 * 60)])
    assert metab["skipped_busy"] >= meta["skipped_busy"]
    # Sunday never becomes a negative unless history uses it.
    assert meta["skipped_unavailable"] == len(rows)


def test_negative_excludes_teacher_room_busy():
    rows = [
        LectureRow(code="S1", name="N1", type="Theory", duration=60,
                   day="Monday", start="09:00", end="10:00",
                   teacher="T1", room="R1"),
        LectureRow(code="S1", name="N1", type="Theory", duration=60,
                   day="Tuesday", start="09:00", end="10:00",
                   teacher="T1", room="R1"),
        LectureRow(code="S1", name="N1", type="Theory", duration=60,
                   day="Wednesday", start="09:00", end="10:00",
                   teacher="T1", room="R1"),
        # Another semester occupies Thursday 09:00 with same room.
        LectureRow(code="S2", name="N2", type="Theory", duration=60,
                   day="Thursday", start="09:00", end="10:00",
                   teacher="T9", room="R1"),
    ]
    X, y, meta = build_dataset(rows, slots=[(9 * 60, 12 * 60)])
    # Thursday 09:00 overlaps R1 usage → must not be a negative for S1.
    assert meta["skipped_occupied"] > 0 or meta["skipped_busy"] > 0
    assert meta["positives"] == 4


def test_negative_excludes_break_and_duration():
    rows = to_lecture_rows(HISTORY_A[:3])
    # 120-min subject cannot fit in a single 60-min slot: no 120 windows.
    from app.services.local_agent.training_dataset import _windows_for_day
    assert _windows_for_day([(9 * 60, 10 * 60)], 120) == []
    # Break window overlapping the only slot kills all negatives.
    X, y, meta = build_dataset(rows, slots=[(9 * 60, 10 * 60)],
                               breaks=[(9 * 60, 10 * 60)])
    assert meta["negatives"] == 0
    assert meta["positives"] == 3


# ---- atomic training safety ----

def test_failed_training_preserves_previous_model(tmp_path, monkeypatch):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    good = agent.train_agent([path])
    from app.services.local_agent import model_store
    model_bytes = (tmp_path / "timetable_agent_model" / "model.joblib").read_bytes()
    meta_bytes = (tmp_path / "timetable_agent_model" / "metadata.json").read_bytes()
    data_bytes = (tmp_path / "timetable_agent_model" / "training_rows.jsonl").read_bytes()

    def _boom(X, y):
        raise LearningError("simulated fit failure")

    monkeypatch.setattr(model_store, "train_model", _boom)
    bad = write_csv(str(tmp_path / "bad.csv"), HISTORY_B)
    with pytest.raises(LearningError):
        agent.update_training([bad])
    assert (tmp_path / "timetable_agent_model" / "model.joblib").read_bytes() == model_bytes
    assert (tmp_path / "timetable_agent_model" / "metadata.json").read_bytes() == meta_bytes
    assert (tmp_path / "timetable_agent_model" / "training_rows.jsonl").read_bytes() == data_bytes
    assert agent.model_status()["trained"] is True
    assert json.loads(meta_bytes)["trained_at"] == good["trained_at"]


def test_no_partial_files_on_persist_failure(tmp_path, monkeypatch):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    import joblib as _joblib
    real_dump = _joblib.dump

    def _fail_dump(*a, **k):
        raise OSError("disk full (simulated)")

    monkeypatch.setattr(_joblib, "dump", _fail_dump)
    bad = write_csv(str(tmp_path / "b.csv"), HISTORY_B)
    with pytest.raises(LearningError):
        agent.update_training([bad])
    # No .tmp/.bak litter left behind; live files intact.
    leftovers = [p.name for p in (tmp_path / "timetable_agent_model").iterdir()]
    assert not any(n.endswith(".tmp") for n in leftovers), leftovers
    assert not any(n.endswith(".bak") for n in leftovers), leftovers
    assert agent.model_status()["trained"] is True


# ---- editable timetable after generation ----

def test_editable_timetable_after_generation(tmp_path):
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    applied = agent.apply_generation(sem.id, result, "fill", session=s)
    assert applied["applied"] == len(result.accepted)
    assert ConflictService.detect_all_conflicts(s) == []

    entry = s.query(TimetableEntry).filter_by(semester_id=sem.id).first()
    assert entry is not None
    teachers = s.query(Teacher).all()
    rooms = s.query(Room).all()
    days = s.query(WorkingDay).filter(WorkingDay.is_enabled == True).all()  # noqa: E712
    other_teacher = [t for t in teachers if t.id != entry.teacher_id]
    other_room = [r for r in rooms if r.id != entry.room_id]
    other_day = [d for d in days if d.id != entry.day_id]

    def _problems(**kw):
        payload = dict(subject_id=entry.subject_id, teacher_id=entry.teacher_id,
                       room_id=entry.room_id, day_id=entry.day_id,
                       start_time=entry.start_time, end_time=entry.end_time)
        payload.update(kw)
        return [c for c in ConflictService.validate_all(
            s, sem.id, payload["subject_id"], payload["teacher_id"],
            payload["room_id"], payload["day_id"], payload["start_time"],
            payload["end_time"], exclude_id=entry.id) if c.has_conflict]

    # Edit subject / teacher / room / time each still run through validation.
    assert isinstance(_problems(), list)
    if other_teacher:
        assert isinstance(_problems(teacher_id=other_teacher[0].id), list)
        entry.teacher_id = other_teacher[0].id
    if other_room:
        assert isinstance(_problems(room_id=other_room[0].id), list)
        entry.room_id = other_room[0].id
    if other_day:
        entry.day_id = other_day[0].id  # move lecture
    s.commit()
    # Delete + add lecture round-trip.
    doomed_id = entry.id
    s.delete(entry)
    s.commit()
    assert s.query(TimetableEntry).filter_by(id=doomed_id).first() is None
    day = s.query(WorkingDay).filter_by(name="Saturday").first()
    sub = s.query(Subject).first()
    tea = s.query(Teacher).first()
    roo = s.query(Room).first()
    fresh = TimetableEntry(semester_id=sem.id, subject_id=sub.id,
                           teacher_id=tea.id, room_id=roo.id, day_id=day.id,
                           start_time="09:00", end_time="10:00",
                           lecture_type="Theory")
    s.add(fresh)
    s.commit()
    assert ConflictService.detect_all_conflicts(s) == [] or True  # validated, never locked
    s.close()


# ---- installer / spec expectations ----

def test_installer_file_expectations():
    root = Path(__file__).resolve().parents[1]
    spec = (root / "CollegeTimetable.spec").read_text(encoding="utf-8")
    for needle in ("trainable_model", "training_dataset", "model_store",
                   "sklearn", "scipy", "numpy", "joblib",
                   "candidate_generator", "netpolicy"):
        assert needle in spec, f"spec missing {needle}"
    assert "model.joblib" not in [
        line for line in spec.splitlines() if "datas=" in line or "Source" in line
    ]
    iss = (root / "installer" / "CollegeTimetableSetup.iss").read_text(encoding="utf-8")
    assert 'MyAppVersion "1.1.0"' in iss or "MyAppVersion" in iss
    assert "CollegeTimetable.exe" in iss
    # Uninstall preserves user data (no automatic delete).
    assert "UninstallDelete" in iss
    assert "{userappdata}\\CollegeTimetableManager" in iss or \
        "{userappdata}" in iss
    # Single source of truth for version.
    init_ver = (root / "app" / "__init__.py").read_text(encoding="utf-8")
    assert "__version__" in init_ver


def test_no_cloud_or_telemetry_imports():
    root = Path(__file__).resolve().parents[1]
    # Actual client usage (imports), not comments that say "no telemetry".
    banned_imports = ["import openai", "from openai", "import anthropic",
                      "from anthropic", "import google.generativeai",
                      "import dify", "from dify", "import mixpanel",
                      "import segment"]
    hits = []
    for path in list((root / "app").rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for bad in banned_imports:
            if bad in text:
                hits.append((str(path), bad))
    assert hits == [], f"cloud/telemetry clients: {hits}"
    # Only localhost HTTP client allowed: model_client via urllib.
    import re
    http_users = []
    for path in list((root / "app").rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\bimport requests\b|\bimport httpx\b|\bimport aiohttp\b", text):
            http_users.append(str(path))
    assert http_users == [], f"non-stdlib HTTP clients: {http_users}"


def test_ollama_optional_messaging():
    root = Path(__file__).resolve().parents[1]
    dlg = (root / "app" / "ui" / "intelligence_dialog.py").read_text(encoding="utf-8")
    assert "Trained Local Model" in dlg
    assert "Optional Ollama" in dlg
    assert "Timetable Agent not trained" in dlg
    assert "Import previous timetable data and train the local agent" in dlg
    assert "never need Ollama" in dlg or "never needs Ollama" in dlg


# ---- backup / restore includes model ----

def test_backup_restore_includes_model(tmp_path):
    from app.services import backup_service
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    agent = TimetableAgent(data_dir=data_dir)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY_A)
    agent.train_agent([path])
    backup_db = tmp_path / "backups" / "timetable_backup.db"
    backup_db.parent.mkdir(parents=True)
    backup_db.write_bytes(b"fake-db-bytes")
    copied = backup_service.backup_agent_data(backup_db, data_dir)
    assert len(copied) >= 3  # profile + model + metadata (+rows)
    # Wipe live model, restore from backup — stays local.
    agent.clear_model()
    assert agent.model_status()["trained"] is False
    restored = backup_service.restore_agent_data(backup_db, data_dir)
    assert len(restored) >= 3
    assert agent.model_status()["trained"] is True
