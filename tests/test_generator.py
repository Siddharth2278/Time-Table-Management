"""In-memory checks: odd/even grouping + offline auto-generator."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Semester, Subject, Teacher, Room, WorkingDay, TimeSlot
from app.services.conflict_service import ConflictService
from app.services.timetable_service import TimetableService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
    sem1 = Semester(name="Semester 1", status="Active")
    sem2 = Semester(name="Semester 2", status="Active")
    session.add_all([sem1, sem2])
    session.flush()
    t = Teacher(name="T1", email="t1@c.edu", department="CS", status="Active")
    r = Room(name="R1", room_number="101", type="Classroom", status="Available")
    session.add_all([t, r])
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
    s1 = Subject(code="CS101", name="Sub1", semester_id=sem1.id, subject_type="Theory",
                 required_lectures_per_week=3, lecture_duration=60,
                 teacher_id=t.id, room_id=r.id)
    s2 = Subject(code="CS102", name="Sub2", semester_id=sem1.id, subject_type="Practical",
                 required_lectures_per_week=2, lecture_duration=60,
                 teacher_id=t.id, room_id=r.id)
    session.add_all([s1, s2])
    session.commit()
    return sem1, sem2


def test_group_conflicts_empty():
    s = make_session()
    seed(s)
    groups = ConflictService.detect_group_conflicts(s)
    assert groups == {"odd": [], "even": []}, groups
    s.close()


def test_group_conflicts_parity():
    s = make_session()
    sem1, sem2 = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    t = s.query(Teacher).first()
    r = s.query(Room).first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    sub2 = s.query(Subject).filter_by(code="CS102").first()
    # Same teacher, same time, sem1 vs sem2 (cross-term clash).
    ok1, _ = TimetableService.create_entry(
        s, sem1.id, sub1.id, t.id, r.id, mon.id, "09:00", "10:00",
        check_subject_limit=False)
    # Force the clash past validation via direct insert.
    from app.models import TimetableEntry
    s.add(TimetableEntry(semester_id=sem2.id, subject_id=sub1.id, teacher_id=t.id,
                         room_id=r.id, day_id=mon.id, start_time="09:00",
                         end_time="10:00", lecture_type="Theory"))
    s.commit()
    assert ok1
    groups = ConflictService.detect_group_conflicts(s)
    assert len(groups["odd"]) >= 1, groups
    assert len(groups["even"]) >= 1, groups
    s.close()


def test_generate_fills_week():
    s = make_session()
    sem1, _ = seed(s)
    result = TimetableService.generate_for_semester(s, sem1.id)
    assert "error" not in result, result
    assert result["placed"] == 5, result
    assert result["unplaced"] == [], result
    assert ConflictService.detect_all_conflicts(s) == []
    comp = ConflictService.calculate_timetable_completion(s, sem1.id)
    assert comp["remaining"] == 0, comp
    s.close()


def test_generate_respects_existing():
    s = make_session()
    sem1, _ = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    t = s.query(Teacher).first()
    r = s.query(Room).first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    ok, _ = TimetableService.create_entry(
        s, sem1.id, sub1.id, t.id, r.id, mon.id, "09:00", "10:00")
    assert ok
    result = TimetableService.generate_for_semester(s, sem1.id)
    assert result["placed"] == 4, result
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()
