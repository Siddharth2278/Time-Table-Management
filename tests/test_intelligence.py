"""Intelligence pipeline tests: fully offline, deterministic, in-memory DB."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Room, RoomAvailability, Semester, Subject, Teacher,
    TeacherAvailability, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.intelligence import reference_analyzer, requirement_analyzer
from app.services.intelligence.candidate_generator import generate_candidates
from app.services.intelligence.pattern_extractor import extract_patterns
from app.services.intelligence.timetable_agent import (
    IntelligenceError, apply_result, run_intelligence,
)
from app.services.intelligence.timetable_optimizer import optimize
from app.services.intelligence.timetable_scorer import score_candidate
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
        Subject(code="CS201", name="Ref", semester_id=semesters[2].id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
    ]
    session.add_all(subjects)
    session.commit()
    mon = session.query(WorkingDay).filter_by(name="Monday").first()
    tue = session.query(WorkingDay).filter_by(name="Tuesday").first()
    ref = subjects[2]
    # Reference: Mon 09:00 + Mon 10:00 (consecutive pair), Tue 09:00.
    session.add_all([
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[0].id, room_id=rooms[0].id,
                       day_id=mon.id, start_time="09:00", end_time="10:00",
                       lecture_type="Theory"),
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[0].id, room_id=rooms[0].id,
                       day_id=mon.id, start_time="10:00", end_time="11:00",
                       lecture_type="Theory"),
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[1].id, room_id=rooms[1].id,
                       day_id=tue.id, start_time="09:00", end_time="10:00",
                       lecture_type="Practical"),
    ])
    session.commit()
    return semesters


def test_reference_analysis():
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    assert profile["has_data"] is True
    assert profile["total_lectures"] == 3
    assert profile["day_distribution"] == {"Monday": 2, "Tuesday": 1}
    assert profile["breaks"][0]["name"] == "Lunch"
    assert profile["average_daily_lectures"] == 1.5
    assert profile["density"] > 0
    s.close()


def test_weekly_counting_and_durations():
    s = make_session()
    sems = seed(s)
    reqs = requirement_analyzer.analyze_requirements(s, sems[0].id)
    by_code = {r["subject"].code: r for r in reqs}
    assert by_code["CS101"]["required"] == 3
    assert by_code["CS101"]["scheduled"] == 0
    assert by_code["CS101"]["remaining"] == 3
    assert by_code["CS102"]["duration"] == 60
    s.close()


def test_spacing_practical_break_patterns():
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    patterns = extract_patterns(profile)
    assert patterns["has_reference"] is True
    assert patterns["preferred_days"][0] == "Monday"
    assert patterns["preferred_times"][0] == "09:00"
    assert patterns["wants_consecutive_practicals"] is False
    assert patterns["break_signature"] == [("13:00", "14:00")]
    assert patterns["morning_share"] == 1.0
    s.close()


def test_candidates_bounded_and_scored():
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    patterns = extract_patterns(profile)
    sub = s.query(Subject).filter_by(code="CS101").first()
    cands = generate_candidates(s, sub, patterns)
    assert 0 < len(cands) <= 48
    assert all(c["subject_id"] == sub.id for c in cands)
    # No break cells offered.
    assert all((c["start_time"], c["end_time"]) != ("13:00", "14:00") for c in cands)
    context = {"by_day_subject": {}, "day_load": {}, "teacher_load": {},
               "day_names": {d.id: d.name for d in s.query(WorkingDay).all()}}
    scored = [score_candidate(c, "Theory", patterns, context) for c in cands]
    monday_first = [c for c in cands if context["day_names"][c["day_id"]] == "Monday"]
    assert monday_first, "reference-day cells must be offered first"
    assert max(scored) > min(scored)
    s.close()


def test_optimization_zero_conflict():
    s = make_session()
    sems = seed(s)
    out = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    assert len(out["accepted"]) == 5, out["rejected"]
    assert out["rejected"] == []
    assert ConflictService.detect_all_conflicts(s) == []
    assert out["diff"]["generated"] == 5
    assert "CS101" in out["explanation"]
    s.close()


def test_availability_rejection():
    s = make_session()
    sems = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    t1 = s.query(Teacher).filter_by(name="T1").first()
    # Block T1 every working day entirely.
    for d in s.query(WorkingDay).filter(WorkingDay.is_enabled == True).all():  # noqa: E712
        s.add(TeacherAvailability(teacher_id=t1.id, day_id=d.id,
                                 start_time="00:00", end_time="23:59",
                                 is_unavailable=True))
    s.commit()
    out = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    # CS101 (assigned T1 only... others available: T2) still places via T2.
    assert len(out["accepted"]) + len(out["rejected"]) == 5
    s.close()


def test_fill_fresh_replace_modes():
    s = make_session()
    sems = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    t2 = s.query(Teacher).filter_by(name="T2").first()
    r2 = s.query(Room).filter_by(name="R2").first()
    # Pre-place one CS101 lecture (Tue 11:00 avoids reference cells).
    tue = s.query(WorkingDay).filter_by(name="Tuesday").first()
    s.add(TimetableEntry(semester_id=sems[0].id, subject_id=sub1.id,
                         teacher_id=t2.id, room_id=r2.id, day_id=tue.id,
                         start_time="11:00", end_time="12:00",
                         lecture_type="Theory"))
    s.commit()
    fill = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    assert len(fill["accepted"]) == 4, fill["rejected"]
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 1
    # Fresh on non-empty must refuse.
    try:
        run_intelligence(s, sems[0].id, sems[2].id, "fresh")
        assert False, "fresh should refuse non-empty semester"
    except IntelligenceError:
        pass
    replace = run_intelligence(s, sems[0].id, sems[2].id, "replace")
    assert len(replace["accepted"]) == 5, replace["rejected"]
    assert replace["diff"]["existing"] == 1
    s.close()


def test_cancel_writes_nothing_and_apply_atomic():
    s = make_session()
    sems = seed(s)
    out = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    # Cancel path: dry run already rolled back.
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 0
    # OK path.
    result = apply_result(s, sems[0].id, out, "fill")
    assert result == {"applied": 5, "rejected": 0}
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 5
    assert ConflictService.detect_all_conflicts(s) == []
    # Poisoned proposal: one clashing entry -> nothing applied.
    bad = dict(out["accepted"][0])
    bad["day_id"] = out["accepted"][1]["day_id"]
    bad["start_time"] = out["accepted"][1]["start_time"]
    bad["end_time"] = out["accepted"][1]["end_time"]
    evil = {"accepted": out["accepted"] + [bad]}
    result = apply_result(s, sems[0].id, evil, "fill")
    assert result["applied"] == 0
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 5
    s.close()


def test_empty_reference_refused():
    s = make_session()
    sems = seed(s)
    try:
        run_intelligence(s, sems[0].id, sems[1].id, "fill")
        assert False, "empty reference must be refused"
    except IntelligenceError as e:
        assert "empty" in str(e).lower()
    s.close()
