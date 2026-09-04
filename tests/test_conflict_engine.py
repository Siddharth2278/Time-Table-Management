import pytest
from pathlib import Path
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Semester, Teacher, Room, Subject, WorkingDay, TimeSlot, TimetableEntry, TeacherAvailability, RoomAvailability
from app.services.conflict_service import ConflictService
from app.services.timetable_service import TimetableService
from app.utils.helpers import do_overlap

@pytest.fixture
def session():
    # In-memory DB for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    # Seed minimal data
    for i in range(1, 7):
        s.add(Semester(name=f"Semester {i}", code=f"SEM{i}", status="Active"))
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for idx, d in enumerate(days, 1):
        s.add(WorkingDay(name=d, is_enabled=True, sort_order=idx))
    s.add(WorkingDay(name="Sunday", is_enabled=False, sort_order=7))
    slots = [("08:00","09:00",False,""),("09:00","10:00",False,""),("10:00","11:00",False,""),("11:00","12:00",False,""),("12:00","13:00",False,""),("13:00","14:00",True,"Lunch Break"),("14:00","15:00",False,"")]
    for st, et, is_break, bname in slots:
        s.add(TimeSlot(start_time=st, end_time=et, label=f"{st}-{et}", is_break=is_break, break_name=bname, is_enabled=True))
    # Teacher
    t1 = Teacher(name="Prof. Amit", email="amit@test.edu", department="CS", designation="Professor", status="Active")
    t2 = Teacher(name="Dr. Neha", email="neha@test.edu", department="CS", designation="Professor", status="Active")
    s.add_all([t1, t2])
    # Rooms
    r1 = Room(name="Room 101", room_number="101", type="Classroom", capacity=60, status="Available")
    r2 = Room(name="Lab 1", room_number="L101", type="Laboratory", capacity=30, status="Available")
    s.add_all([r1, r2])
    s.flush()
    # Subjects
    sem1 = s.query(Semester).filter(Semester.name=="Semester 1").first()
    sem3 = s.query(Semester).filter(Semester.name=="Semester 3").first()
    sub1 = Subject(code="CS101", name="Mathematics", semester_id=sem1.id, subject_type="Theory", required_lectures_per_week=4, lecture_duration=60, teacher_id=t1.id, room_id=r1.id)
    sub2 = Subject(code="CS301", name="Physics", semester_id=sem3.id, subject_type="Theory", required_lectures_per_week=3, lecture_duration=60, teacher_id=t1.id, room_id=r1.id)
    sub3 = Subject(code="CS102", name="Chemistry", semester_id=sem1.id, subject_type="Theory", required_lectures_per_week=3, lecture_duration=60, teacher_id=t2.id, room_id=r2.id)
    s.add_all([sub1, sub2, sub3])
    s.commit()
    yield s
    s.close()

def test_overlap_logic():
    assert do_overlap("10:00", "11:30", "11:00", "12:00") == True  # conflict
    assert do_overlap("10:00", "11:00", "11:00", "12:00") == False  # no conflict (adjacent)
    assert do_overlap("10:00", "12:00", "10:30", "11:00") == True  # nested
    assert do_overlap("10:00", "11:00", "09:30", "10:30") == True  # overlap start
    assert do_overlap("08:00", "09:00", "09:00", "10:00") == False

def test_same_teacher_same_time_reject(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    sem3 = session.query(Semester).filter(Semester.name=="Semester 3").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    r2 = session.query(Room).filter(Room.room_number=="L101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    sub2 = session.query(Subject).filter(Subject.code=="CS301").first()
    # Add first lecture Sem1 Monday 10:00-11:30
    ok, res = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:30", "Theory")
    assert ok, f"First entry should succeed: {res}"
    # Try overlapping same teacher different semester same time 11:00-12:00 -> should reject
    ok2, res2 = TimetableService.create_entry(session, sem3.id, sub2.id, t1.id, r2.id, monday.id, "11:00", "12:00", "Theory")
    assert not ok2
    assert any("Teacher" in c.message for c in res2)

def test_same_teacher_non_overlapping_allow(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    sem3 = session.query(Semester).filter(Semester.name=="Semester 3").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    r2 = session.query(Room).filter(Room.room_number=="L101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    sub2 = session.query(Subject).filter(Subject.code=="CS301").first()
    ok, _ = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok
    ok2, _ = TimetableService.create_entry(session, sem3.id, sub2.id, t1.id, r2.id, monday.id, "11:00", "12:00", "Theory")
    assert ok2, "Adjacent time should be allowed"

def test_same_semester_overlapping_reject(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    t2 = session.query(Teacher).filter(Teacher.name=="Dr. Neha").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    r2 = session.query(Room).filter(Room.room_number=="L101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    sub3 = session.query(Subject).filter(Subject.code=="CS102").first()
    ok, _ = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok
    ok2, res2 = TimetableService.create_entry(session, sem1.id, sub3.id, t2.id, r2.id, monday.id, "10:30", "11:30", "Theory")
    assert not ok2
    assert any("Semester" in c.message for c in res2)

def test_same_room_overlapping_reject(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    sem3 = session.query(Semester).filter(Semester.name=="Semester 3").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    t2 = session.query(Teacher).filter(Teacher.name=="Dr. Neha").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    sub3 = session.query(Subject).filter(Subject.code=="CS102").first()
    ok, _ = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:30", "Theory")
    assert ok
    ok2, res2 = TimetableService.create_entry(session, sem3.id, sub3.id, t2.id, r1.id, monday.id, "11:00", "12:00", "Theory")
    assert not ok2
    assert any("Room" in c.message for c in res2)

def test_lab_conflict_same_as_room(session):
    # Lab is just a Room with type Laboratory, same logic
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    sem3 = session.query(Semester).filter(Semester.name=="Semester 3").first()
    tues = session.query(WorkingDay).filter(WorkingDay.name=="Tuesday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    t2 = session.query(Teacher).filter(Teacher.name=="Dr. Neha").first()
    lab = session.query(Room).filter(Room.room_number=="L101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    sub3 = session.query(Subject).filter(Subject.code=="CS102").first()
    ok, _ = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, lab.id, tues.id, "10:00", "12:00", "Lab")
    assert ok
    ok2, res2 = TimetableService.create_entry(session, sem3.id, sub3.id, t2.id, lab.id, tues.id, "11:00", "12:30", "Lab")
    assert not ok2

def test_teacher_unavailable_reject(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    # Make Amit unavailable Monday 09:00-11:00
    av = TeacherAvailability(teacher_id=t1.id, day_id=monday.id, start_time="09:00", end_time="11:00", is_unavailable=True, reason="Meeting")
    session.add(av)
    session.commit()
    ok, res = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert not ok
    assert any("unavailable" in c.message.lower() for c in res)

def test_room_unavailable_reject(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    wed = session.query(WorkingDay).filter(WorkingDay.name=="Wednesday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    lab = session.query(Room).filter(Room.room_number=="L101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    av = RoomAvailability(room_id=lab.id, day_id=wed.id, start_time="14:00", end_time="16:00", is_unavailable=True, reason="Maintenance")
    session.add(av)
    session.commit()
    ok, res = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, lab.id, wed.id, "14:30", "15:30", "Lab")
    assert not ok
    assert any("Room" in c.message or "unavailable" in c.message.lower() for c in res)

def test_end_before_start_reject(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    ok, res = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "11:00", "10:00", "Theory")
    assert not ok
    assert any("End time" in c.message for c in res)

def test_editing_no_self_conflict(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    ok, entry = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok
    # Edit same entry without changing time should succeed (no self-conflict)
    ok2, _ = TimetableService.update_entry(session, entry.id, start_time="10:00", end_time="11:00")
    assert ok2

def test_move_revalidate(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    tues = session.query(WorkingDay).filter(WorkingDay.name=="Tuesday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    t2 = session.query(Teacher).filter(Teacher.name=="Dr. Neha").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    sub3 = session.query(Subject).filter(Subject.code=="CS102").first()
    # Create two entries: one Monday 10-11 for Amit, another Tuesday 10-11 for Amit
    ok, e1 = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok
    # Create entry for same teacher Tuesday - then try to move first entry to Tuesday same time -> should conflict
    ok2, e2 = TimetableService.create_entry(session, sem1.id, sub3.id, t1.id, r1.id, tues.id, "10:00", "11:00", "Theory")
    # This will actually conflict on room too? Use different room? Wait same room and teacher on different day should be fine
    # But we used same room - different day is okay, so ok2 should be True
    # Let's ensure: same teacher different day same time is allowed
    assert ok2, f"Should allow different day: {e2}"
    # Now try to move e1 to Tuesday 10:00-11:00 -> should conflict with e2 (teacher and room)
    ok3, res3 = TimetableService.move_entry(session, e1.id, tues.id, "10:00", "11:00")
    assert not ok3
    assert len(res3) > 0

def test_delete_frees_resources(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    ok, e1 = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok
    # Delete
    assert TimetableService.delete_entry(session, e1.id)
    # Now same slot should be free
    sub3 = session.query(Subject).filter(Subject.code=="CS102").first()
    ok2, _ = TimetableService.create_entry(session, sem1.id, sub3.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok2

def test_find_available_slots_returns_only_valid(session):
    sem1 = session.query(Semester).filter(Semester.name=="Semester 1").first()
    monday = session.query(WorkingDay).filter(WorkingDay.name=="Monday").first()
    t1 = session.query(Teacher).filter(Teacher.name=="Prof. Amit").first()
    r1 = session.query(Room).filter(Room.room_number=="101").first()
    sub1 = session.query(Subject).filter(Subject.code=="CS101").first()
    # Occupy Monday 10-11
    ok, _ = TimetableService.create_entry(session, sem1.id, sub1.id, t1.id, r1.id, monday.id, "10:00", "11:00", "Theory")
    assert ok
    slots = ConflictService.find_available_slots(session, sem1.id, t1.id, r1.id, 60)
    # None of returned slots should be Monday 10-11
    for s in slots:
        if s["day_id"] == monday.id and s["start_time"] == "10:00":
            assert False, "Found occupied slot as available"
    # At least some slots should be found
    assert len(slots) > 0
