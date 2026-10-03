"""Phase 3 tests: actually-fitted local timetable model. Fully offline."""
import csv
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Room, Semester, Subject, Teacher, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.conflict_service import ConflictService
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.model_store import (
    clear_model, load_model, model_status, train_from_rows,
)
from app.services.local_agent.schemas import LearningError, LectureRow
from app.services.local_agent.trainable_model import (
    FEATURES_V1, predict_scores, train_model,
)
from app.services.local_agent.training_dataset import (
    build_dataset, extract_features, load_files_as_dicts,
)

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


def test_dataset_creation_and_schema(tmp_path):
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    rows, skipped, per_file = load_files_as_dicts([path])
    assert len(rows) == 7 and skipped == 0
    X, y, meta = build_dataset([
        LectureRow(
            **{k: r[k] for k in ("code", "name", "type", "day", "start",
                                 "end", "teacher", "room")} |
            {"duration": int(r["duration"])}) for r in rows])
    assert meta["positives"] == 7
    assert meta["negatives"] == 7 * 3
    assert len(X) == len(y) == 28
    assert all(len(row) == len(FEATURES_V1) for row in X)


def test_examples_valid_and_structural(tmp_path):
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    rows, _, _ = load_files_as_dicts([path])
    X, y, _ = build_dataset([
        LectureRow(
            code=r["code"], name=r["name"], type=r["type"], duration=int(r["duration"]),
            day=r["day"], start=r["start"], end=r["end"],
            teacher=r["teacher"], room=r["room"]) for r in rows])
    for row in X:
        assert all(isinstance(v, float) for v in row)
        assert all(0.0 <= v <= 1.5 for v in row)
    # Positive rows sit on real history cells; negatives never do.
    assert sum(y) == 7


def test_fitting_and_prediction(tmp_path):
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    rows, _, _ = load_files_as_dicts([path])
    from app.services.local_agent.schemas import LectureRow
    X, y, _ = build_dataset([LectureRow(
        code=r["code"], name=r["name"], type=r["type"], duration=int(r["duration"]),
        day=r["day"], start=r["start"], end=r["end"],
        teacher=r["teacher"], room=r["room"]) for r in rows])
    model, metrics = train_model(X, y)
    assert metrics["separation"] > 0.01
    assert 0.0 <= metrics["train_accuracy"] <= 1.0
    scores = predict_scores(model, X[:3])
    assert len(scores) == 3
    assert all(0.0 <= s <= 1.0 and s == s for s in scores)


def test_persistence_reload_and_corrupt(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    agent.train_agent([path])
    model, metadata = load_model(tmp_path)
    assert metadata["model_version"] == 1
    again, metadata2 = load_model(tmp_path)
    assert metadata2["trained_at"] == metadata["trained_at"]
    from app.services.local_agent import model_store
    model_path = tmp_path / "timetable_agent_model" / "model.joblib"
    model_path.write_bytes(b"corrupt-bytes-not-a-model")
    with pytest.raises(LearningError):
        load_model(tmp_path)
    leftovers = [p.name for p in (tmp_path / "timetable_agent_model").iterdir()]
    assert not any(n == "model.joblib" for n in leftovers), "corrupt file quarantined"
    assert any("corrupt" in n for n in leftovers)


def test_incremental_and_clear(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    first = write_csv(str(tmp_path / "a.csv"), HISTORY[:4])
    rep1 = agent.train_agent([first])
    assert rep1["positives"] + rep1["negatives"] == 4 + 12
    second = write_csv(str(tmp_path / "b.csv"), HISTORY[4:])
    rep2 = agent.update_training([second])
    assert rep2["lectures"] == 7, "combined old + new rows"
    status = agent.model_status()
    assert status["trained"] is True
    assert status["stored_rows"] == 7
    assert agent.clear_model() is True
    assert agent.model_status()["trained"] is False
    assert agent.clear_model() is False


def test_no_subject_name_dependency(tmp_path):
    """Train on Maths/Physics/Programming; score Networks/Java/Software Eng."""
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    agent.train_agent([path])
    from app.services.local_agent import model_store
    model, _ = load_model(tmp_path)
    role_theory = {"type_practical": 0, "duration": 60, "frequency": 3,
                   "avg_gap": 2.0, "morning_share": 1.0, "day_count": 3,
                   "day_names": ["Monday", "Wednesday", "Friday"],
                   "times": ["09:00"],
                   "day_counts": {"Monday": 1, "Wednesday": 1, "Friday": 1},
                   "time_counts": {"09:00": 3}}
    context = {"day_load": {}, "teacher_share": 0.0, "room_share": 0.0,
               "placed_days": [], "day_order": {}, "position_in_day": 0.5,
               "gap_from_break": 1.0}
    good = extract_features(role_theory, 0, 9 * 60, context,
                            day_name="Monday", start_str="09:00")
    bad = extract_features(role_theory, 5, 17 * 60, context,
                           day_name="Saturday", start_str="17:00")
    scores = model_store.score_candidates(model, [good, bad])
    assert scores[0] > scores[1], "learned morning-theory pattern must transfer"
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_generation_uses_trained_model(tmp_path, monkeypatch):
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    agent.train_agent([path])

    def _no_network(*args, **kwargs):
        raise AssertionError("generation must not touch Ollama")

    monkeypatch.setattr(OllamaClient, "generate", _no_network)
    monkeypatch.setattr(OllamaClient, "ensure_ready", _no_network)
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert "trained-local-model" in result.profile_info["planner"]
    assert len(result.accepted) > 0
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_model_score_cannot_bypass_conflicts(tmp_path):
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    agent.train_agent([path])
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    sub = s.query(Subject).filter_by(code="NW101").first()
    tea = s.query(Teacher).filter_by(name="T1").first()
    roo = s.query(Room).filter_by(name="R1").first()
    for start, end in (("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00"),
                       ("14:00", "15:00"), ("15:00", "16:00")):
        s.add(TimetableEntry(semester_id=sem.id, subject_id=sub.id,
                             teacher_id=tea.id, room_id=roo.id, day_id=mon.id,
                             start_time=start, end_time=end, lecture_type="Theory"))
    s.commit()
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert all(e["day_id"] != mon.id for e in result.accepted), \
        "a fully blocked day must stay empty no matter the model scores"
    s.close()


def test_regeneration_dryrun_apply_rollback(tmp_path):
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    agent.train_agent([path])
    first = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert first.accepted
    before = s.query(TimetableEntry).filter_by(semester_id=sem.id).count()
    second = agent.regenerate(sem.id, first, planner="trained", session=s)
    key = lambda e: (e["subject_id"], e["day_id"], e["start_time"])
    assert {key(e) for e in second.accepted} != {key(e) for e in first.accepted}
    assert s.query(TimetableEntry).filter_by(semester_id=sem.id).count() == before
    applied = agent.apply_generation(sem.id, first, "fill", session=s)
    assert applied["applied"] == len(first.accepted)
    assert ConflictService.detect_all_conflicts(s) == []
    evil = dict(first.accepted[0])
    from app.services.local_agent.schemas import GenerationResult
    poisoned = GenerationResult(accepted=first.accepted + [evil])
    applied = agent.apply_generation(sem.id, poisoned, "fill", session=s)
    assert applied["applied"] == 0
    assert s.query(TimetableEntry).filter_by(semester_id=sem.id).count() == \
        before + len(first.accepted)
    s.close()


def test_offline_guarantee(tmp_path, monkeypatch):
    import socket
    import urllib.request

    def _fail(*args, **kwargs):
        raise OSError("network blocked in test")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    agent = TimetableAgent(data_dir=tmp_path)
    path = write_csv(str(tmp_path / "h.csv"), HISTORY)
    agent.train_agent([path])
    assert agent.model_status()["trained"] is True
    s = make_session()
    sem = seed(s)
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    s.close()
