import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_data_dir() -> Path:
    """Return user data directory for storing SQLite DB (persistent across reinstalls)."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            p = Path(appdata) / "CollegeTimetableManager"
        else:
            p = Path.home() / "AppData" / "Roaming" / "CollegeTimetableManager"
    else:
        p = Path.home() / ".local" / "share" / "CollegeTimetableManager"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_db_path() -> Path:
    return get_data_dir() / "timetable.db"

def get_engine(db_path: Path | None = None, echo: bool = False):
    if db_path is None:
        db_path = get_db_path()
    # Ensure parent exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=echo, connect_args={"check_same_thread": False})
    # Enable foreign keys
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def _fk_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    return engine

_engine = None
_SessionLocal = None

def init_engine(db_path: Path | None = None, echo: bool = False):
    global _engine, _SessionLocal
    _engine = get_engine(db_path, echo)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine

def get_engine_instance():
    global _engine
    if _engine is None:
        init_engine()
    return _engine

def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal()

def init_db(db_path: Path | None = None, echo: bool = False):
    """Create all tables and seed default data."""
    from app.models import (
        Semester, WorkingDay, TimeSlot, Setting
    )
    engine = init_engine(db_path, echo)
    Base.metadata.create_all(bind=engine)
    session = get_session()
    try:
        # Seed semesters if empty
        if session.query(Semester).count() == 0:
            for i in range(1, 7):
                session.add(Semester(name=f"Semester {i}", code=f"SEM{i}", status="Active"))
        # Seed working days
        if session.query(WorkingDay).count() == 0:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            for idx, d in enumerate(days, 1):
                session.add(WorkingDay(name=d, is_enabled=True, sort_order=idx))
            # Sunday disabled by default (not part of spec but keep record)
            session.add(WorkingDay(name="Sunday", is_enabled=False, sort_order=7))
        # Seed time slots
        if session.query(TimeSlot).count() == 0:
            defaults = [
                ("08:00", "09:00", False, ""),
                ("09:00", "10:00", False, ""),
                ("10:00", "11:00", False, ""),
                ("11:00", "12:00", False, ""),
                ("12:00", "13:00", False, ""),
                ("13:00", "14:00", True, "Lunch Break"),
                ("14:00", "15:00", False, ""),
                ("15:00", "16:00", False, ""),
                ("16:00", "17:00", False, ""),
            ]
            for s, e, is_break, bname in defaults:
                label = f"{s}-{e}" + (f" ({bname})" if is_break else "")
                session.add(TimeSlot(start_time=s, end_time=e, label=label, is_break=is_break, break_name=bname, is_enabled=True))
        # Seed settings
        if session.query(Setting).count() == 0:
            defaults = {
                "college_name": "My College",
                "department": "Computer Science",
                "academic_year": "2026-27",
                "default_start_time": "08:00",
                "default_end_time": "17:00",
                "backup_location": str(get_data_dir() / "backups"),
                "theme": "dark",
            }
            for k, v in defaults.items():
                session.add(Setting(key=k, value=v))
            session.flush()
        # Ensure theme exists for existing DBs (when settings already existed)
        if session.query(Setting).filter(Setting.key=="theme").first() is None:
            session.add(Setting(key="theme", value="dark"))
            session.flush()
        # Short demo data for one department — simple but effective
        from app.models import Teacher as _Teacher
        if session.query(_Teacher).count() == 0:
            _seed_short_data(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return engine

def _seed_short_data(session):
    """Short, simple demo for one department — 4 teachers / 4 rooms / 5 subjects / 5 lectures."""
    from app.models import Teacher, Room, Subject, WorkingDay, Semester, TimetableEntry
    teachers_data = [
        ("Prof. Amit Sharma", "amit@college.edu", "Computer Science", "Professor", "Active"),
        ("Dr. Priya Singh", "priya@college.edu", "Mathematics", "Associate Professor", "Active"),
        ("Prof. Rajesh Kumar", "rajesh@college.edu", "Physics", "Professor", "Active"),
        ("Dr. Neha Patel", "neha@college.edu", "Computer Science", "Assistant Professor", "Active"),
    ]
    teachers = []
    for name, email, dept, desig, status in teachers_data:
        t = Teacher(name=name, email=email, department=dept, designation=desig, status=status)
        session.add(t)
        teachers.append(t)
    session.flush()
    rooms_data = [
        ("Room 101", "101", "Classroom", 60, "Available"),
        ("Room 102", "102", "Classroom", 60, "Available"),
        ("Computer Lab 1", "L101", "Laboratory", 30, "Available"),
        ("Seminar Hall", "SH01", "Seminar Hall", 100, "Available"),
    ]
    rooms = []
    for name, num, typ, cap, status in rooms_data:
        r = Room(name=name, room_number=num, type=typ, capacity=cap, status=status)
        session.add(r)
        rooms.append(r)
    session.flush()
    semesters = {s.name: s for s in session.query(Semester).all()}
    days = {d.name: d for d in session.query(WorkingDay).all()}
    subjects_data = [
        ("CS101", "Programming Fundamentals", "Semester 1", "Theory", 4, 60, 0, 0),
        ("MA101", "Mathematics-I", "Semester 1", "Theory", 3, 60, 1, 1),
        ("CS201", "Data Structures", "Semester 2", "Theory", 4, 60, 0, 0),
        ("CS301", "DBMS", "Semester 3", "Theory", 3, 60, 3, 1),
        ("CS303", "DBMS Lab", "Semester 3", "Lab", 2, 120, 3, 2),
    ]
    subjects = []
    for code, name, sem_name, typ, req, dur, t_idx, r_idx in subjects_data:
        subj = Subject(code=code, name=name, semester_id=semesters[sem_name].id, subject_type=typ, required_lectures_per_week=req, lecture_duration=dur, teacher_id=teachers[t_idx].id, room_id=rooms[r_idx].id, room_requirement=rooms[r_idx].type)
        session.add(subj)
        subjects.append(subj)
    session.flush()
    subj_map = {s.code: s for s in subjects}
    samples = [
        ("Semester 1", "CS101", 0, 0, "Monday", "09:00", "10:00", "Theory"),
        ("Semester 1", "MA101", 1, 1, "Tuesday", "09:00", "10:00", "Theory"),
        ("Semester 2", "CS201", 0, 0, "Monday", "10:00", "11:00", "Theory"),
        ("Semester 3", "CS301", 3, 1, "Wednesday", "10:00", "11:00", "Theory"),
        ("Semester 3", "CS303", 3, 2, "Thursday", "10:00", "12:00", "Lab"),
    ]
    for sem_name, code, t_idx, r_idx, day, st, et, lt in samples:
        entry = TimetableEntry(semester_id=semesters[sem_name].id, subject_id=subj_map[code].id, teacher_id=teachers[t_idx].id, room_id=rooms[r_idx].id, day_id=days[day].id, start_time=st, end_time=et, lecture_type=lt, academic_year="2026-27")
        session.add(entry)
    session.flush()

def _seed_sample_data(session):
    from app.models import Teacher, Room, Subject, WorkingDay, Semester, TimetableEntry
    # Teachers - 12
    teachers_data = [
        ("Prof. Amit Sharma", "amit.sharma@college.edu", "Computer Science", "Professor", "Active"),
        ("Dr. Priya Singh", "priya.singh@college.edu", "Mathematics", "Associate Professor", "Active"),
        ("Prof. Rajesh Kumar", "rajesh.kumar@college.edu", "Physics", "Professor", "Active"),
        ("Dr. Neha Patel", "neha.patel@college.edu", "Computer Science", "Assistant Professor", "Active"),
        ("Prof. Vikram Desai", "vikram.desai@college.edu", "Electronics", "Professor", "Active"),
        ("Dr. Anjali Mehta", "anjali.mehta@college.edu", "Mathematics", "Assistant Professor", "Active"),
        ("Prof. Suresh Reddy", "suresh.reddy@college.edu", "Chemistry", "Professor", "Active"),
        ("Dr. Kavita Joshi", "kavita.joshi@college.edu", "Computer Science", "Associate Professor", "Active"),
        ("Prof. Manoj Verma", "manoj.verma@college.edu", "Mechanical", "Professor", "Active"),
        ("Dr. Sunita Rao", "sunita.rao@college.edu", "English", "Assistant Professor", "Active"),
        ("Prof. Arjun Nair", "arjun.nair@college.edu", "Computer Science", "Professor", "Active"),
        ("Dr. Pooja Gupta", "pooja.gupta@college.edu", "Mathematics", "Associate Professor", "Active"),
    ]
    teachers = []
    for name, email, dept, desig, status in teachers_data:
        t = Teacher(name=name, email=email, department=dept, designation=desig, status=status)
        session.add(t)
        teachers.append(t)
    session.flush()

    # Rooms - 10 classrooms + 3 labs + 1 seminar hall = 14
    rooms_data = [
        ("Room 101", "101", "Classroom", 60, "Available"),
        ("Room 102", "102", "Classroom", 60, "Available"),
        ("Room 103", "103", "Classroom", 60, "Available"),
        ("Room 201", "201", "Classroom", 60, "Available"),
        ("Room 202", "202", "Classroom", 60, "Available"),
        ("Room 203", "203", "Classroom", 60, "Available"),
        ("Room 204", "204", "Classroom", 60, "Available"),
        ("Room 301", "301", "Classroom", 70, "Available"),
        ("Room 302", "302", "Classroom", 70, "Available"),
        ("Room 303", "303", "Classroom", 70, "Available"),
        ("Computer Lab 1", "L101", "Laboratory", 30, "Available"),
        ("Computer Lab 2", "L102", "Laboratory", 30, "Available"),
        ("Physics Lab", "L201", "Laboratory", 25, "Available"),
        ("Seminar Hall", "SH01", "Seminar Hall", 120, "Available"),
    ]
    rooms = []
    for name, num, typ, cap, status in rooms_data:
        r = Room(name=name, room_number=num, type=typ, capacity=cap, status=status)
        session.add(r)
        rooms.append(r)
    session.flush()

    # Semesters reference
    semesters = {s.name: s for s in session.query(Semester).all()}

    # Subjects - 18 subjects across 6 semesters (3 each), with varied types
    subjects_data = [
        # Sem1
        ("CS101", "Programming Fundamentals", "Semester 1", "Theory", 4, 60, 0, None),
        ("CS102", "Digital Logic", "Semester 1", "Theory", 3, 60, 1, None),
        ("MA101", "Engineering Mathematics-I", "Semester 1", "Theory", 4, 60, 1, None),
        ("PH101", "Engineering Physics", "Semester 1", "Theory", 3, 60, 2, None),
        # Sem2
        ("CS201", "Data Structures", "Semester 2", "Theory", 4, 60, 0, None),
        ("CS202", "Object Oriented Programming", "Semester 2", "Practical", 2, 120, 3, 10),  # lab
        ("MA201", "Engineering Mathematics-II", "Semester 2", "Theory", 4, 60, 5, None),
        # Sem3
        ("CS301", "Database Management Systems", "Semester 3", "Theory", 4, 60, 0, None),
        ("CS302", "Operating Systems", "Semester 3", "Theory", 3, 60, 4, None),
        ("CS303", "DBMS Lab", "Semester 3", "Lab", 2, 120, 7, 10),
        # Sem4
        ("CS401", "Computer Networks", "Semester 4", "Theory", 3, 60, 4, None),
        ("CS402", "Software Engineering", "Semester 4", "Theory", 3, 60, 3, None),
        ("CS403", "CN Lab", "Semester 4", "Lab", 2, 120, 7, 10),
        # Sem5
        ("CS501", "Machine Learning", "Semester 5", "Theory", 3, 60, 10, None),
        ("CS502", "Compiler Design", "Semester 5", "Theory", 3, 60, 0, None),
        ("CS503", "Project Lab", "Semester 5", "Lab", 2, 120, 3, 11),
        # Sem6
        ("CS601", "Artificial Intelligence", "Semester 6", "Theory", 3, 60, 10, None),
        ("CS602", "Cloud Computing", "Semester 6", "Theory", 3, 60, 4, None),
        ("CS603", "Major Project", "Semester 6", "Practical", 4, 60, 3, None),
    ]
    subjects = []
    for code, name, sem_name, stype, req, dur, t_idx, room_idx in subjects_data:
        sem = semesters[sem_name]
        teacher = teachers[t_idx] if t_idx < len(teachers) else None
        room = rooms[room_idx] if room_idx is not None and room_idx < len(rooms) else None
        subj = Subject(
            code=code, name=name, semester_id=sem.id, subject_type=stype,
            required_lectures_per_week=req, lecture_duration=dur,
            teacher_id=teacher.id if teacher else None,
            room_id=room.id if room else None,
            room_requirement=room.type if room else "Classroom"
        )
        session.add(subj)
        subjects.append(subj)
    session.flush()

    # Working days lookup
    days = {d.name: d for d in session.query(WorkingDay).all()}

    # Teacher availability: Prof. Amit unavailable Monday 09:00-11:00
    from app.models import TeacherAvailability, RoomAvailability
    # Find Amit
    amit = teachers[0]
    session.add(TeacherAvailability(teacher_id=amit.id, day_id=days["Monday"].id, start_time="09:00", end_time="11:00", is_unavailable=True, reason="Research meeting"))
    # Another: Priya unavailable Friday 14:00-16:00
    session.add(TeacherAvailability(teacher_id=teachers[1].id, day_id=days["Friday"].id, start_time="14:00", end_time="16:00", is_unavailable=True, reason="Personal"))
    # Room availability: Computer Lab 1 unavailable Wednesday 14:00-16:00
    session.add(RoomAvailability(room_id=rooms[10].id, day_id=days["Wednesday"].id, start_time="14:00", end_time="16:00", is_unavailable=True, reason="Maintenance"))

    # Sample timetable entries - non-conflicting
    timetable_samples = [
        # Sem1
        ("Semester 1", "CS101", 0, 0, "Monday", "08:00", "09:00", "Theory"),
        ("Semester 1", "MA101", 1, 1, "Monday", "09:00", "10:00", "Theory"),
        ("Semester 1", "PH101", 2, 2, "Monday", "10:00", "11:00", "Theory"),
        ("Semester 1", "CS102", 0, 3, "Tuesday", "08:00", "09:00", "Theory"),
        ("Semester 1", "CS101", 0, 0, "Wednesday", "08:00", "09:00", "Theory"),
        # Sem2
        ("Semester 2", "CS201", 0, 1, "Monday", "11:00", "12:00", "Theory"),
        ("Semester 2", "MA201", 5, 2, "Tuesday", "10:00", "11:00", "Theory"),
        ("Semester 2", "CS202", 3, 10, "Wednesday", "10:00", "12:00", "Practical"),
        # Sem3
        ("Semester 3", "CS301", 7, 4, "Monday", "14:00", "15:00", "Theory"),
        ("Semester 3", "CS302", 4, 5, "Tuesday", "14:00", "15:00", "Theory"),
        ("Semester 3", "CS303", 7, 10, "Thursday", "10:00", "12:00", "Lab"),
        # Sem4
        ("Semester 4", "CS401", 4, 6, "Monday", "15:00", "16:00", "Theory"),
        ("Semester 4", "CS402", 3, 7, "Tuesday", "11:00", "12:00", "Theory"),
        # Sem5
        ("Semester 5", "CS501", 10, 8, "Monday", "09:00", "10:00", "Theory"),
        # Sem6
        ("Semester 6", "CS601", 10, 9, "Monday", "11:00", "12:00", "Theory"),
    ]
    # Map subject code to subject object
    subj_map = {s.code: s for s in subjects}
    for sem_name, subj_code, t_idx, r_idx, day_name, st, et, ltype in timetable_samples:
        sem = semesters[sem_name]
        subj = subj_map[subj_code]
        teacher = teachers[t_idx]
        room = rooms[r_idx]
        day = days[day_name]
        entry = TimetableEntry(
            semester_id=sem.id, subject_id=subj.id, teacher_id=teacher.id, room_id=room.id,
            day_id=day.id, start_time=st, end_time=et, lecture_type=ltype, academic_year="2026-27"
        )
        session.add(entry)
    session.flush()

def clear_all_department_data(session=None):
    """Delete all department-specific data, keep only 6 semesters / working days / time slots / settings structure. Simple + effective."""
    from app.models import Teacher, Room, Subject, TimetableEntry, TeacherAvailability, RoomAvailability
    close_after = False
    if session is None:
        session = get_session()
        close_after = True
    try:
        # Order matters due to FKs
        session.query(TimetableEntry).delete()
        session.query(TeacherAvailability).delete()
        session.query(RoomAvailability).delete()
        session.query(Subject).delete()
        session.query(Teacher).delete()
        session.query(Room).delete()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if close_after:
            session.close()

def load_sample_data_if_empty(session=None):
    """Public helper for UI button — loads sample data only if DB is empty."""
    from app.models import Teacher
    close_after = False
    if session is None:
        session = get_session()
        close_after = True
    try:
        if session.query(Teacher).count() == 0:
            _seed_sample_data(session)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        raise
    finally:
        if close_after:
            session.close()
