import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

def backup_database(db_path: Path, backup_path: Path):
    from sqlalchemy import text as _text  # local to avoid circulars
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if Path(db_path).resolve() == Path(backup_path).resolve():
        raise ValueError("Backup destination must differ from live database.")
    # Use sqlite backup API for safety if DB is open
    src = dst = None
    try:
        src = sqlite3.connect(str(db_path), timeout=30)
        dst = sqlite3.connect(str(backup_path), timeout=30)
        src.backup(dst)
    except Exception:
        # Fallback to file copy only if backup API failed and no partial dst
        try:
            if dst is not None:
                dst.close()
                dst = None
        except Exception:
            pass
        try:
            if src is not None:
                src.close()
                src = None
        except Exception:
            pass
        shutil.copy2(str(db_path), str(backup_path))
    finally:
        for c in (dst, src):
            try:
                if c is not None:
                    c.close()
            except Exception:
                pass

def restore_database(db_path: Path, backup_path: Path):
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    # Validate backup is a real SQLite DB before overwriting live DB
    con = None
    try:
        con = sqlite3.connect(str(backup_path), timeout=30)
        cur = con.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        if not row or row[0] != "ok":
            raise ValueError(f"Backup failed integrity check: {row}")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semesters'")
        if cur.fetchone() is None:
            raise ValueError("Backup is not a CollegeTimetable database (missing semesters table).")
    finally:
        try:
            if con is not None:
                con.close()
        except Exception:
            pass
    # Safety copy of current db
    try:
        if Path(db_path).exists():
            bak = Path(str(db_path) + f".pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
            shutil.copy2(str(db_path), str(bak))
    except Exception:
        pass
    # Overwrite current db — caller must ensure no open sessions / restart after
    shutil.copy2(str(backup_path), str(db_path))

def export_json(session, filepath: Path):
    import json
    from app.models import Semester, Teacher, Room, Subject, WorkingDay, TimeSlot, TimetableEntry, TeacherAvailability, RoomAvailability, Setting
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1}
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
    from datetime import datetime as _dt
    from app.models import Semester, Teacher, Room, Subject, WorkingDay, TimeSlot, TimetableEntry, TeacherAvailability, RoomAvailability, Setting
    from sqlalchemy import text as _text
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Clear existing (except maybe keep structure) - we will delete and reinsert
    # Disable FK checks temporarily (same connection)
    con = session.connection()
    con.execute(_text("PRAGMA foreign_keys=OFF"))
    try:
        for model in [TimetableEntry, TeacherAvailability, RoomAvailability, Subject, Teacher, Room, TimeSlot, WorkingDay, Semester, Setting]:
            session.query(model).delete(synchronize_session=False)
        session.flush()
        session.expire_all()
        session.expunge_all()
        # Insert in dependency order
        def _coerce(model, item):
            item = dict(item)
            for col in model.__table__.columns:
                if str(col.type).startswith("DATETIME") and isinstance(item.get(col.name), str):
                    try:
                        item[col.name] = _dt.fromisoformat(item[col.name])
                    except (ValueError, TypeError):
                        item[col.name] = None
            return item
        def insert(model, items):
            for item in items:
                obj = model(**_coerce(model, item))
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
        # Fix sqlite autoincrement after preserving ids
        for _model, _table in [(Semester, "semesters"), (Teacher, "teachers"), (Room, "rooms"), (Subject, "subjects"), (TimetableEntry, "timetable_entries")]:
            try:
                _max = con.execute(_text(f"SELECT MAX(id) FROM {_table}")).scalar() or 0
                con.execute(_text(f"UPDATE sqlite_sequence SET seq={int(_max)} WHERE name='{_table}'"))
            except Exception:
                pass
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        try:
            con.execute(_text("PRAGMA foreign_keys=ON"))
        except Exception:
            pass

def sqlalchemy_text(s):
    from sqlalchemy import text
    return text(s)
