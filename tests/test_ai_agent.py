"""AI pipeline tests: mocked provider, in-memory DB, no real API calls."""
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Room, Semester, Subject, Teacher, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.ai import ai_client
from app.services.ai.ai_client import AIConfig, AIError
from app.services.ai.prompt_builder import build_messages, build_payload, build_reference_profile
from app.services.ai.timetable_agent import apply_proposal, run as run_agent
from app.services.ai.timetable_parser import extract_json, parse_proposal
from app.services.conflict_service import ConflictService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
    semesters = [Semester(name=f"Semester {i}", status="Active") for i in (1, 2, 3)]
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
             TimeSlot(start_time="13:00", end_time="14:00", label="13:00-14:00",
                      is_break=True, break_name="Lunch")]
    session.add_all(slots)
    subjects = [
        Subject(code="CS101", name="Sub1", semester_id=semesters[0].id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
        Subject(code="CS102", name="Sub2", semester_id=semesters[0].id,
                subject_type="Practical", required_lectures_per_week=1,
                lecture_duration=60, teacher_id=teachers[1].id, room_id=rooms[1].id),
        Subject(code="CS201", name="Ref", semester_id=semesters[2].id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
    ]
    session.add_all(subjects)
    session.commit()
    # Reference timetable: Semester 3, two lectures incl. a practical pair pattern.
    mon = session.query(WorkingDay).filter_by(name="Monday").first()
    tue = session.query(WorkingDay).filter_by(name="Tuesday").first()
    ref = subjects[2]
    session.add_all([
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[0].id, room_id=rooms[0].id,
                       day_id=mon.id, start_time="09:00", end_time="10:00",
                       lecture_type="Theory"),
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[0].id, room_id=rooms[0].id,
                       day_id=tue.id, start_time="10:00", end_time="11:00",
                       lecture_type="Theory"),
    ])
    session.commit()
    return semesters


def fake_config(payload_fn):
    def post_impl(endpoint, model, messages):
        return {"choices": [{"message": {"content": json.dumps(payload_fn())}}]}
    return AIConfig(provider="test", endpoint="https://ai.test",
                    model="test-model", api_key="secret", post_impl=post_impl)


def test_reference_analysis_counts():
    s = make_session()
    sems = seed(s)
    profile = build_reference_profile(s, sems[2].id)
    assert profile["has_data"] is True
    assert profile["total_lectures"] == 2
    assert profile["subjects"][0]["code"] == "CS201"
    assert profile["subjects"][0]["count"] == 2
    assert profile["day_distribution"] == {"Monday": 1, "Tuesday": 1}
    assert profile["breaks"][0]["name"] == "Lunch"
    assert profile["average_daily_load"] == 1.0
    s.close()


def test_reference_empty_profile():
    s = make_session()
    sems = seed(s)
    profile = build_reference_profile(s, sems[1].id)
    assert profile["has_data"] is False
    assert profile["total_lectures"] == 0
    s.close()


def test_payload_is_scoped():
    s = make_session()
    sems = seed(s)
    payload = build_payload(s, sems[0].id, sems[2].id, "fill")
    assert payload["semester"]["id"] == sems[0].id
    assert {x["code"] for x in payload["subjects"]} == {"CS101", "CS102"}
    assert len(payload["teachers"]) == 2
    assert len(payload["rooms"]) == 2
    assert payload["reference_profile"]["total_lectures"] == 2
    assert "password" not in json.dumps(payload).lower()
    messages = build_messages(payload)
    assert messages[0]["role"] == "system"
    s.close()


def test_parser_accepts_strict_json():
    body = {"semester_id": 1, "entries": [{
        "subject_id": 1, "teacher_id": 1, "room_id": 1, "day_id": 1,
        "start_time": "09:00", "end_time": "10:00", "lecture_type": "Theory"}],
        "unplaced": [], "explanation": "ok"}
    parsed = parse_proposal(
        {"choices": [{"message": {"content": "```json\n" + json.dumps(body) + "\n```"}}]},
        1, {"subjects": {1}, "teachers": {1}, "rooms": {1}, "days": {1}})
    assert len(parsed["entries"]) == 1
    assert parsed["explanation"] == "ok"


def test_parser_drops_bad_rows():
    body = {"semester_id": 1, "entries": [
        {"subject_id": 0, "teacher_id": 1, "room_id": 1, "day_id": 1,
         "start_time": "09:00", "end_time": "10:00"},
        {"subject_id": 1, "teacher_id": 1, "room_id": 1, "day_id": 1,
         "start_time": "10:00", "end_time": "09:00"},
        {"subject_id": 1, "teacher_id": 1, "room_id": 1, "day_id": 1,
         "start_time": "09:00", "end_time": "10:00", "lecture_type": "Theory"},
    ], "unplaced": [], "explanation": ""}
    parsed = parse_proposal({"choices": [{"message": {"content": json.dumps(body)}}]},
                            1, {"subjects": {1}, "teachers": {1}, "rooms": {1}, "days": {1}})
    assert len(parsed["entries"]) == 1
    assert len(parsed["dropped"]) == 2


@pytest.mark.parametrize("body", [
    "just some prose, no json",
    {"semester_id": 2, "entries": [], "unplaced": [], "explanation": ""},
    {"semester_id": 1, "entries": "nope", "unplaced": [], "explanation": ""},
])
def test_parser_rejects_invalid(body):
    text = body if isinstance(body, str) else json.dumps(body)
    with pytest.raises(AIError):
        parse_proposal({"choices": [{"message": {"content": text}}]},
                       1, {"subjects": {1}, "teachers": {1}, "rooms": {1}, "days": {1}})


def test_offline_disables_flow(monkeypatch):
    monkeypatch.setattr(ai_client, "check_internet", lambda *a, **k: False)
    s = make_session()
    sems = seed(s)
    cfg = AIConfig(provider="test", endpoint="https://ai.test",
                   model="m", api_key="k")
    with pytest.raises(AIError):
        run_agent(s, sems[0].id, sems[2].id, "fill", cfg)
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 0
    s.close()


def _proposal_for(s, sem_id, entries):
    return {"mode": "fill", "reference": {}, "accepted": entries,
            "rejected": [], "model_unplaced": [],
            "explanation": "t", "diff": {}}


def test_dry_run_writes_nothing_and_cancel_safe(monkeypatch):
    monkeypatch.setattr(ai_client, "check_internet", lambda *a, **k: True)
    monkeypatch.setattr(ai_client, "provider_status",
                        lambda cfg: {"state": "ready", "message": "Connected."})
    s = make_session()
    sems = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    tue = s.query(WorkingDay).filter_by(name="Tuesday").first()
    wed = s.query(WorkingDay).filter_by(name="Wednesday").first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    sub2 = s.query(Subject).filter_by(code="CS102").first()
    t1 = s.query(Teacher).filter_by(name="T1").first()
    t2 = s.query(Teacher).filter_by(name="T2").first()
    r1 = s.query(Room).filter_by(name="R1").first()
    r2 = s.query(Room).filter_by(name="R2").first()

    def payload():
        # Free cells: reference uses Mon 09:00 + Tue 10:00 (T1/R1).
        return {"semester_id": sems[0].id, "entries": [
            {"subject_id": sub1.id, "teacher_id": t1.id, "room_id": r1.id,
             "day_id": tue.id, "start_time": "09:00", "end_time": "10:00",
             "lecture_type": "Theory"},
            {"subject_id": sub2.id, "teacher_id": t2.id, "room_id": r2.id,
             "day_id": wed.id, "start_time": "10:00", "end_time": "11:00",
             "lecture_type": "Practical"},
        ], "unplaced": [], "explanation": "balanced"}

    cfg = fake_config(payload)
    stages = []
    out = run_agent(s, sems[0].id, sems[2].id, "fill", cfg,
                    progress=stages.append)
    assert stages == ["internet", "reference", "requirements", "teachers",
                      "rooms", "breaks", "generated", "validated"]
    assert len(out["accepted"]) == 2
    assert out["rejected"] == []
    # Dry run rolled back: database untouched (Cancel path).
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 0
    s.close()


def test_invalid_entries_never_saved(monkeypatch):
    monkeypatch.setattr(ai_client, "check_internet", lambda *a, **k: True)
    monkeypatch.setattr(ai_client, "provider_status",
                        lambda cfg: {"state": "ready", "message": "Connected."})
    s = make_session()
    sems = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    tue = s.query(WorkingDay).filter_by(name="Tuesday").first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    t1 = s.query(Teacher).filter_by(name="T1").first()
    r1 = s.query(Room).filter_by(name="R1").first()

    def payload():
        return {"semester_id": sems[0].id, "entries": [
            {"subject_id": sub1.id, "teacher_id": t1.id, "room_id": r1.id,
             "day_id": tue.id, "start_time": "09:00", "end_time": "10:00",
             "lecture_type": "Theory"},
            {"subject_id": sub1.id, "teacher_id": t1.id, "room_id": r1.id,
             "day_id": tue.id, "start_time": "09:00", "end_time": "10:00",
             "lecture_type": "Theory"},
        ], "unplaced": [], "explanation": "dup"}
    cfg = fake_config(payload)
    out = run_agent(s, sems[0].id, sems[2].id, "fill", cfg, _retries=0)
    assert len(out["accepted"]) == 1
    assert len(out["rejected"]) == 1
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_apply_ok_and_rollback(monkeypatch):
    s = make_session()
    sems = seed(s)
    tue = s.query(WorkingDay).filter_by(name="Tuesday").first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    t1 = s.query(Teacher).filter_by(name="T1").first()
    r1 = s.query(Room).filter_by(name="R1").first()
    good = {"subject_id": sub1.id, "teacher_id": t1.id, "room_id": r1.id,
            "day_id": tue.id, "start_time": "09:00", "end_time": "10:00",
            "lecture_type": "Theory"}
    result = apply_proposal(s, sems[0].id, _proposal_for(s, sems[0].id, [good]), "fill")
    assert result == {"applied": 1, "rejected": 0}
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 1
    # Proposal containing a clash: nothing is applied (atomic).
    bad = dict(good)
    result = apply_proposal(s, sems[0].id, _proposal_for(s, sems[0].id, [good, bad]), "fill")
    assert result["applied"] == 0
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 1
    s.close()
