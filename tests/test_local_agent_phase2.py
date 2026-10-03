"""Phase 2 tests: local-model planning + validated generation. No daemon needed.

The model is faked at the client boundary (FakeOllama); everything
downstream — strict validation, solver, ConflictService, atomic apply —
runs for real against in-memory databases.
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from types import SimpleNamespace

from app.models import (
    Base, Room, Semester, Subject, Teacher, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.conflict_service import ConflictService
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.planner import parse_plan
from app.services.local_agent.schemas import LearningError
from app.services.local_agent.timetable_learner import learn


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
    semesters = [Semester(name=f"Semester {i}", status="Active") for i in (1, 2)]
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
             TimeSlot(start_time="13:00", end_time="14:00", label="13:00-14:00",
                      is_break=True, break_name="Lunch")]
    session.add_all(slots)
    subjects = [
        Subject(code="CS101", name="Sub1", semester_id=semesters[0].id,
                subject_type="Theory", required_lectures_per_week=3,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
        Subject(code="CS102", name="Sub2", semester_id=semesters[0].id,
                subject_type="Practical", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[1].id, room_id=rooms[1].id),
    ]
    session.add_all(subjects)
    session.commit()
    return semesters, subjects, teachers, rooms


HISTORY_ROWS = [
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": 60,
     "day": "Monday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": 60,
     "day": "Wednesday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": 60,
     "day": "Friday", "start": "09:00", "end_time": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": 120,
     "day": "Tuesday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": 120,
     "day": "Thursday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1"},
]


class FakeOllama:
    """Deterministic stand-in for the localhost model."""

    def __init__(self, payload, endpoint="http://127.0.0.1:11434",
                 model="test-model"):
        self._payload = payload
        self.endpoint = endpoint
        self.model = model
        self.calls = []

    def ensure_ready(self, model=None):
        return model or self.model

    def generate(self, prompt, model=None, options=None):
        self.calls.append(prompt)
        return self._payload

    def is_running(self):
        return True


def learn_profile(agent, label="hist"):
    from app.services.local_agent.timetable_learner import learn as do_learn
    from app.services.local_agent.schemas import LectureRow
    rows = [LectureRow(code=r["code"], name=r["name"], type=r["type"],
                       duration=r["duration"], day=r["day"],
                       start=r["start"], end=r.get("end", r.get("end_time", "")),
                       teacher=r["teacher"], room=r["room"]) for r in HISTORY_ROWS]
    profile = do_learn(rows, source_label=label)
    from app.services.local_agent import pattern_store
    pattern_store.save_profile(profile, agent._data_dir)
    return profile


def plan_for(session, semesters, subjects, day="Wednesday", start="09:00"):
    return json.dumps({
        "placements": [
            {"subject_id": subjects[0].id, "day": day, "start_time": start, "rank": 1},
            {"subject_id": subjects[1].id, "day": "Tuesday", "start_time": "10:00", "rank": 1},
        ],
        "notes": "test plan",
    })


def test_1_profile_loaded(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    learn_profile(agent)
    profile = agent.get_learning_profile()
    assert profile["version"] == 1
    assert profile["total_lectures"] == 5
    assert set(profile["roles"]) == {"theory|60|3", "practical|120|2"}


def test_2_model_call_steers_solver(tmp_path):
    s = make_session()
    sems, subjects, _, _ = seed(s)
    agent = TimetableAgent(data_dir=tmp_path,
                           ollama=FakeOllama(plan_for(s, sems, subjects)))
    learn_profile(agent)
    result = agent.generate_dry_run(s, sems[0].id, "fill")
    assert agent._ollama.calls, "model was never consulted"
    assert len(result.accepted) > 0
    assert ("Wednesday", subjects[0].id) in [
        (e["day_id"] and s.query(WorkingDay).filter_by(id=e["day_id"]).first().name,
         e["subject_id"]) for e in result.accepted]
    s.close()


def test_3_malformed_output_rejected(tmp_path):
    s = make_session()
    sems, _, _, _ = seed(s)
    agent = TimetableAgent(data_dir=tmp_path, ollama=FakeOllama("not json at all"))
    learn_profile(agent)
    with pytest.raises(LearningError):
        agent.generate_dry_run(s, sems[0].id, "fill")
    agent2 = TimetableAgent(data_dir=tmp_path,
                            ollama=FakeOllama(json.dumps({"nope": []})))
    # profile persists across agents sharing the dir
    with pytest.raises(LearningError):
        agent2.generate_dry_run(s, sems[0].id, "fill")
    s.close()


def test_4_schema_validation_drops_bad_rows(tmp_path):
    s = make_session()
    sems, subjects, _, _ = seed(s)
    from app.services.local_agent.requirements import collect_requirements
    req = collect_requirements(s, sems[0].id)
    good = {"subject_id": subjects[0].id, "day": "Monday",
            "start_time": "09:00", "rank": 1}
    body = {"placements": [
        good,
        {"subject_id": 9999, "day": "Monday", "start_time": "09:00", "rank": 1},
        {"subject_id": subjects[0].id, "day": "Noday", "start_time": "09:00", "rank": 1},
        {"subject_id": subjects[0].id, "day": "Monday", "start_time": "25:00", "rank": 1},
        {"subject_id": subjects[0].id, "day": "Monday", "start_time": "09:00", "rank": 1},
        {"day": "Monday", "start_time": "09:00", "rank": 1},
    ], "notes": ""}
    placements, dropped, _ = parse_plan(json.dumps(body), req)
    assert placements == [{**good}]
    assert len(dropped) == 5
    s.close()


def _genesis(tmp_path, payload_text):
    s = make_session()
    sems, subjects, _, _ = seed(s)
    agent = TimetableAgent(data_dir=tmp_path, ollama=FakeOllama(payload_text))
    learn_profile(agent)
    return s, sems, subjects, agent


def test_5_required_fields_and_6_invalid_ids(tmp_path):
    text = json.dumps({"placements": [
        {"subject_id": 1, "day": "Monday", "start_time": "09:00", "rank": 2},
        {"subject_id": 4242, "day": "Monday", "start_time": "10:00", "rank": 1},
    ], "notes": ""})
    s, sems, subjects, agent = _genesis(tmp_path, text)
    result = agent.generate_dry_run(s, sems[0].id, "fill")
    assert result.accepted, "valid row must reach the solver"
    for entry in result.accepted:
        for key in ("subject_id", "teacher_id", "room_id", "day_id",
                    "start_time", "end_time", "lecture_type"):
            assert key in entry, key
    assert any("unknown subject_id 4242" in d.get("reason", "") for d in result.rejected)
    s.close()


def test_7_conflict_service_catches_clashes(tmp_path):
    s = make_session()
    sems, subjects, teachers, rooms = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    s.add(TimetableEntry(semester_id=sems[0].id, subject_id=subjects[0].id,
                         teacher_id=teachers[0].id, room_id=rooms[0].id,
                         day_id=mon.id, start_time="09:00", end_time="10:00",
                         lecture_type="Theory"))
    s.commit()
    text = json.dumps({"placements": [
        {"subject_id": subjects[0].id, "day": "Monday",
         "start_time": "09:00", "rank": 1},
    ], "notes": ""})
    s2, sems2, subjects2, agent = _genesis(tmp_path, text)
    # NOTE: _genesis seeds a fresh DB; replicate the fixed clash there.
    mon2 = s2.query(WorkingDay).filter_by(name="Monday").first()
    t2 = s2.query(Teacher).filter_by(name="T1").first()
    r2 = s2.query(Room).filter_by(name="R1").first()
    s2.add(TimetableEntry(semester_id=sems2[0].id, subject_id=subjects2[0].id,
                          teacher_id=t2.id, room_id=r2.id, day_id=mon2.id,
                          start_time="09:00", end_time="10:00",
                          lecture_type="Theory"))
    s2.commit()
    result = agent.generate_dry_run(s2, sems2[0].id, "fill")
    placed_cells = [(e["day_id"], e["start_time"]) for e in result.accepted
                    if e["subject_id"] == subjects2[0].id]
    assert (mon2.id, "09:00") not in placed_cells, \
        "engine must refuse the clashing cell even though the model asked for it"
    assert len(result.accepted) == 4, result.rejected
    assert ConflictService.detect_all_conflicts(s2) == []
    s.close()
    s2.close()


def test_9_dry_run_clean_and_10_apply_atomic(tmp_path):
    s = make_session()
    sems, subjects, _, _ = seed(s)
    before = s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count()
    agent = TimetableAgent(data_dir=tmp_path,
                           ollama=FakeOllama(plan_for(s, sems, subjects)))
    learn_profile(agent)
    result = agent.generate_dry_run(s, sems[0].id, "fill")
    assert result.accepted
    mid = s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count()
    assert mid == before, "dry run must not modify the database"
    applied = agent.apply_generation(sems[0].id, result, "fill", session=s)
    assert applied["applied"] == len(result.accepted)
    after = s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count()
    assert after == before + len(result.accepted)
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_11_failed_apply_rolls_back(tmp_path):
    s = make_session()
    sems, subjects, _, _ = seed(s)
    agent = TimetableAgent(data_dir=tmp_path,
                           ollama=FakeOllama(plan_for(s, sems, subjects)))
    learn_profile(agent)
    result = agent.generate_dry_run(s, sems[0].id, "fill")
    assert result.accepted
    before = s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count()
    evil = dict(result.accepted[0])
    poisoned = type(result)(accepted=result.accepted + [evil],
                            rejected=result.rejected, unplaced=result.unplaced,
                            hard_conflicts=0, structural_similarity=0.0,
                            profile_info={}, stats={})
    applied = agent.apply_generation(sems[0].id, poisoned, "fill", session=s)
    assert applied["applied"] == 0
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == before
    s.close()


def test_12_multifile_update(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    import csv
    first = tmp_path / "a.csv"
    with open(first, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["code", "day", "start", "end"])
        writer.writeheader()
        writer.writerows([
            {"code": "MA101", "day": "Monday", "start": "09:00", "end": "10:00"},
            {"code": "MA101", "day": "Wednesday", "start": "09:00", "end": "10:00"},
            {"code": "MA101", "day": "Friday", "start": "09:00", "end": "10:00"},
        ])
    second = tmp_path / "b.csv"
    with open(second, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["code", "day", "start", "end"])
        writer.writeheader()
        writer.writerows([
            {"code": "PH102", "day": "Tuesday", "start": "14:00", "end": "16:00"},
            {"code": "PH102", "day": "Thursday", "start": "14:00", "end": "16:00"},
            {"code": "CH103", "day": "Monday", "start": "11:00", "end": "12:00"},
        ])
    summary = agent.learn_files([str(first)])
    assert summary["lectures"] == 3
    summary = agent.learn_files([str(second)])
    assert summary["lectures"] == 6, summary
    profile = agent.get_learning_profile()
    assert set(profile["sources"]) == {str(first), str(second)}
    assert profile["total_lectures"] == 6


def test_13_remote_endpoint_rejected(monkeypatch):
    with pytest.raises(LearningError):
        OllamaClient(endpoint="http://evil.example.com:11434")
    with pytest.raises(LearningError):
        OllamaClient(endpoint="http://192.168.1.50:11434")
    monkeypatch.setenv("LOCAL_AGENT_OLLAMA_URL", "https://cloud.example.com")
    with pytest.raises(LearningError):
        OllamaClient()
    monkeypatch.delenv("LOCAL_AGENT_OLLAMA_URL")
    assert OllamaClient(endpoint="http://localhost:11434").endpoint == \
        "http://localhost:11434"
    assert OllamaClient().endpoint == "http://127.0.0.1:11434"


def test_14_regenerate_differs(tmp_path):
    s = make_session()
    sems, subjects, _, _ = seed(s)
    agent = TimetableAgent(data_dir=tmp_path,
                           ollama=FakeOllama(plan_for(s, sems, subjects)))
    learn_profile(agent)
    first = agent.generate_dry_run(s, sems[0].id, "fill")
    assert first.accepted
    second = agent.regenerate(sems[0].id, first)
    key = lambda e: (e["subject_id"], e["day_id"], e["start_time"])
    assert {key(e) for e in second.accepted} != {key(e) for e in first.accepted}
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_15_grid_loads_result():
    from PySide6.QtWidgets import QApplication
    from app.ui.timetable_grid import TimetableGridWidget
    app = QApplication.instance() or QApplication([])
    grid = TimetableGridWidget()
    mon = SimpleNamespace(id=1, name="Monday")
    entry = SimpleNamespace(
        id=101, day_id=1, start_time="09:00", end_time="10:00",
        lecture_type="Theory",
        subject=SimpleNamespace(code="CS101", name="Sub1"),
        teacher=SimpleNamespace(name="T1"),
        room=SimpleNamespace(name="R1", room_number="101"))
    grid.populate([mon], [("09:00", "10:00")], [entry], breaks={})
    assert len(grid.cards) == 1
    seen = []
    grid.card_double_clicked.connect(lambda eid: seen.append(eid))
    grid.card_selected(entry.id)
    assert grid.selected_entry_id == entry.id
    grid.emit_card_double_click(entry.id)
    assert seen == [entry.id]
