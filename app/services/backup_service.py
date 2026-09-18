import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

def backup_database(db_path: Path, backup_path: Path):
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    # Use sqlite backup API for safety if DB is open
    # Fallback to shutil copy
    try:
        # Try sqlite3 backup
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(backup_path))
        src.backup(dst)
        dst.close()
        src.close()
    except Exception:
        shutil.copy2(str(db_path), str(backup_path))

def restore_database(db_path: Path, backup_path: Path):
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    # Ensure backup is valid sqlite (quick check)
    # Overwrite current db
    # Close connections before - caller should ensure no open sessions
    shutil.copy2(str(backup_path), str(db_path))

def export_json(session, filepath: Path):
    import json
    from app.models import Semester, Teacher, Room, Subject, WorkingDay, TimeSlot, TimetableEntry, TeacherAvailability, RoomAvailability, Setting
    data = {}
    for model, name in [
        (Semester, "semesters"),
        (Teacher, "teachers"),
        (Room, "rooms"),
        (Subject, "subjects"),
        (WorkingDay, "working_days"),
        (TimeSlot, "time_slots"),
        (TimetableEntry, "timetable_entries"),
        (TeacherAvailability, "teacher_availability"),
        (RoomAvailability, "room_availability"),
        (Setting, "settings"),
    ]:
        rows = session.query(model).all()
        items = []
        for r in rows:
            d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
            # Convert datetime to iso
            for k, v in list(d.items()):
                if hasattr(v, 'isoformat'):
                    try:
                        d[k] = v.isoformat()
                    except:
                        pass
            items.append(d)
        data[name] = items
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def import_json(session, filepath: Path):
    import json
    from app.models import Semester, Teacher, Room, Subject, WorkingDay, TimeSlot, TimetableEntry, TeacherAvailability, RoomAvailability, Setting
    from app.database import Base
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Clear existing (except maybe keep structure) - we will delete and reinsert
    # Disable FK checks temporarily
    session.execute(sqlalchemy_text("PRAGMA foreign_keys=OFF"))
    try:
        for model in [TimetableEntry, TeacherAvailability, RoomAvailability, Subject, Teacher, Room, TimeSlot, WorkingDay, Semester, Setting]:
            session.query(model).delete()
        session.flush()
        # Insert in dependency order
        def insert(model, items):
            for item in items:
                # Remove id to let autoincrement? But we want preserve ids - keep id
                # Handle datetime fields
                obj = model(**item)
                session.add(obj)
            session.flush()
        mapping = {
            "semesters": Semester,
            "teachers": Teacher,
            "rooms": Room,
            "subjects": Subject,
            "working_days": WorkingDay,
            "time_slots": TimeSlot,
            "timetable_entries": TimetableEntry,
            "teacher_availability": TeacherAvailability,
            "room_availability": RoomAvailability,
            "settings": Setting,
        }
        for key, model in mapping.items():
            if key in data:
                insert(model, data[key])
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.execute(sqlalchemy_text("PRAGMA foreign_keys=ON"))

def sqlalchemy_text(s):
    from sqlalchemy import text
    return text(s)
