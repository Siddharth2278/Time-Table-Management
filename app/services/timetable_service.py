from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import TimetableEntry, Subject, Semester, Teacher, Room, WorkingDay, TimeSlot
from app.services.conflict_service import ConflictService, ConflictResult

class TimetableService:

    @staticmethod
    def _fk_missing(session: Session, semester_id: int, subject_id: int, teacher_id: int, room_id: int, day_id: int) -> Optional[str]:
        if session.query(Semester).filter(Semester.id == semester_id).first() is None:
            return f"Semester id {semester_id} does not exist."
        if session.query(Subject).filter(Subject.id == subject_id).first() is None:
            return f"Subject id {subject_id} does not exist."
        if session.query(Teacher).filter(Teacher.id == teacher_id).first() is None:
            return f"Teacher id {teacher_id} does not exist."
        if session.query(Room).filter(Room.id == room_id).first() is None:
            return f"Room id {room_id} does not exist."
        if session.query(WorkingDay).filter(WorkingDay.id == day_id).first() is None:
            return f"Day id {day_id} does not exist."
        return None

    @staticmethod
    def create_entry(session: Session, semester_id: int, subject_id: int, teacher_id: int, room_id: int, day_id: int, start_time: str, end_time: str, lecture_type: str = "Theory", academic_year: str = "2026-27", check_subject_limit: bool = True) -> tuple[bool, List[ConflictResult] | TimetableEntry]:
        # Validate required fields (explicit, 0 is invalid for ids)
        if any(v is None for v in [semester_id, subject_id, teacher_id, room_id, day_id, start_time, end_time]):
            return False, [ConflictResult(True, "validation", "All fields are required.")]
        if any(not isinstance(v, int) or v <= 0 for v in [semester_id, subject_id, teacher_id, room_id, day_id]):
            return False, [ConflictResult(True, "validation", "Invalid semester/subject/teacher/room/day id.")]
        if not start_time or not end_time:
            return False, [ConflictResult(True, "validation", "Start and end time are required.")]
        # Validate working day enabled first (cheap, avoids wasted conflict scans)
        day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
        if not day or not day.is_enabled:
            return False, [ConflictResult(True, "validation", f"Selected day {(day.name if day else day_id)} is not a working day.")]
        fk_err = TimetableService._fk_missing(session, semester_id, subject_id, teacher_id, room_id, day_id)
        if fk_err:
            return False, [ConflictResult(True, "validation", fk_err)]
        conflicts = ConflictService.validate_all(session, semester_id, subject_id, teacher_id, room_id, day_id, start_time, end_time, exclude_id=None, check_subject_limit=check_subject_limit)
        has = [c for c in conflicts if c.has_conflict]
        if has:
            return False, has
        # All good, create
        try:
            entry = TimetableEntry(
                semester_id=semester_id, subject_id=subject_id, teacher_id=teacher_id, room_id=room_id,
                day_id=day_id, start_time=start_time, end_time=end_time, lecture_type=lecture_type or "Theory", academic_year=academic_year or "2026-27"
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return True, entry
        except SQLAlchemyError as e:
            session.rollback()
            return False, [ConflictResult(True, "database", f"Database error: {str(e)}")]
        except (ValueError, AttributeError, TypeError) as e:
            session.rollback()
            return False, [ConflictResult(True, "validation", f"Invalid data: {str(e)}")]

    @staticmethod
    def update_entry(session: Session, entry_id: int, **kwargs) -> tuple[bool, List[ConflictResult] | TimetableEntry]:
        entry = session.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
        if not entry:
            return False, [ConflictResult(True, "validation", "Timetable entry not found.")]
        # Prepare new values, falling back to existing (explicit None keeps old value)
        def _pick(key, current):
            v = kwargs.get(key, current)
            return current if v is None else v
        semester_id = _pick("semester_id", entry.semester_id)
        subject_id = _pick("subject_id", entry.subject_id)
        teacher_id = _pick("teacher_id", entry.teacher_id)
        room_id = _pick("room_id", entry.room_id)
        day_id = _pick("day_id", entry.day_id)
        start_time = _pick("start_time", entry.start_time)
        end_time = _pick("end_time", entry.end_time)
        lecture_type = _pick("lecture_type", entry.lecture_type)
        academic_year = _pick("academic_year", entry.academic_year)
        check_subject_limit = kwargs.get("check_subject_limit", True)

        # Validate working day
        day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
        if not day or not day.is_enabled:
            return False, [ConflictResult(True, "validation", f"Selected day {(day.name if day else day_id)} is not a working day.")]

        fk_err = TimetableService._fk_missing(session, semester_id, subject_id, teacher_id, room_id, day_id)
        if fk_err:
            return False, [ConflictResult(True, "validation", fk_err)]

        conflicts = ConflictService.validate_all(session, semester_id, subject_id, teacher_id, room_id, day_id, start_time, end_time, exclude_id=entry_id, check_subject_limit=bool(check_subject_limit))
        has = [c for c in conflicts if c.has_conflict]
        if has:
            return False, has
        try:
            entry.semester_id = semester_id
            entry.subject_id = subject_id
            entry.teacher_id = teacher_id
            entry.room_id = room_id
            entry.day_id = day_id
            entry.start_time = start_time
            entry.end_time = end_time
            entry.lecture_type = lecture_type
            entry.academic_year = academic_year
            session.commit()
            session.refresh(entry)
            return True, entry
        except SQLAlchemyError as e:
            session.rollback()
            return False, [ConflictResult(True, "database", f"Database error: {str(e)}")]
        except (ValueError, AttributeError, TypeError) as e:
            session.rollback()
            return False, [ConflictResult(True, "validation", f"Invalid data: {str(e)}")]

    @staticmethod
    def delete_entry(session: Session, entry_id: int) -> bool:
        entry = session.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
        if not entry:
            return False
        try:
            session.delete(entry)
            session.commit()
            return True
        except SQLAlchemyError:
            session.rollback()
            return False

    @staticmethod
    def move_entry(session: Session, entry_id: int, new_day_id: int, new_start: str, new_end: str) -> tuple[bool, List[ConflictResult] | TimetableEntry]:
        return TimetableService.update_entry(session, entry_id, day_id=new_day_id, start_time=new_start, end_time=new_end)

    @staticmethod
    def get_semester_timetable(session: Session, semester_id: int) -> List[TimetableEntry]:
        return session.query(TimetableEntry).join(WorkingDay, TimetableEntry.day_id == WorkingDay.id).filter(TimetableEntry.semester_id == semester_id).order_by(WorkingDay.sort_order, TimetableEntry.start_time).all()

    @staticmethod
    def get_teacher_timetable(session: Session, teacher_id: int) -> List[TimetableEntry]:
        return session.query(TimetableEntry).join(WorkingDay, TimetableEntry.day_id == WorkingDay.id).filter(TimetableEntry.teacher_id == teacher_id).order_by(WorkingDay.sort_order, TimetableEntry.start_time).all()

    @staticmethod
    def get_room_timetable(session: Session, room_id: int) -> List[TimetableEntry]:
        return session.query(TimetableEntry).join(WorkingDay, TimetableEntry.day_id == WorkingDay.id).filter(TimetableEntry.room_id == room_id).order_by(WorkingDay.sort_order, TimetableEntry.start_time).all()

    @staticmethod
    def analyze_generation_need(session: Session, semester_id: int) -> List[Dict[str, Any]]:
        """Per-subject weekly analysis: required vs scheduled vs remaining.

        Existing entries are treated as fixed; only the remaining count is
        ever scheduled. Read-only.
        """
        analysis = []
        subjects = session.query(Subject).filter(
            Subject.semester_id == semester_id).order_by(Subject.code).all()
        for s in subjects:
            try:
                required = max(0, int(s.required_lectures_per_week or 0))
            except (TypeError, ValueError):
                required = 0
            scheduled = session.query(TimetableEntry).filter(
                TimetableEntry.semester_id == semester_id,
                TimetableEntry.subject_id == s.id).count()
            analysis.append({
                "subject": s,
                "required": required,
                "scheduled": scheduled,
                "remaining": max(0, required - scheduled),
            })
        return analysis

    @staticmethod
    def generate_for_semester(session: Session, semester_id: int) -> Dict[str, Any]:
        """Offline auto-scheduler: fill unscheduled weekly lectures.

        Greedy and deterministic. Every placement goes through create_entry,
        so the full ConflictService validation (teacher / semester / room /
        availability / break / subject limit) applies — a generated
        timetable can never contain a conflict the manual flow would block.
        Returns {"placed": int, "unplaced": [...], "analysis": [...] buckets}.
        """
        analysis = TimetableService.analyze_generation_need(session, semester_id)
        days = session.query(WorkingDay).filter(
            WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()
        slots = session.query(TimeSlot).filter(
            TimeSlot.is_enabled == True, TimeSlot.is_break == False
        ).order_by(TimeSlot.start_time).all()
        teachers = session.query(Teacher).filter(
            Teacher.status == "Active").order_by(Teacher.name).all()
        rooms = session.query(Room).filter(
            Room.status == "Available").order_by(Room.name).all()
        result: Dict[str, Any] = {"placed": 0, "unplaced": [], "analysis": analysis}
        if not days:
            result["error"] = "No working days enabled."
            return result
        if not slots:
            result["error"] = "No teaching slots defined."
            return result
        if not teachers:
            result["error"] = "No active teachers."
            return result
        if not rooms:
            result["error"] = "No available rooms."
            return result
        teacher_ids = [t.id for t in teachers]
        # Subjects with the most remaining lectures first (packs tighter).
        todo = sorted(
            [a for a in analysis if a["remaining"] > 0],
            key=lambda a: (-a["remaining"], a["subject"].code or ""))
        for item in todo:
            subject = item["subject"]
            teacher_order = []
            if subject.teacher_id in teacher_ids:
                teacher_order.append(subject.teacher_id)
            teacher_order += [t for t in teacher_ids if t not in teacher_order]
            room_order = []
            room_ids = [r.id for r in rooms]
            if subject.room_id in room_ids:
                room_order.append(subject.room_id)
            room_order += [r.id for r in rooms
                           if r.id not in room_order
                           and (r.type == subject.room_requirement or not subject.room_requirement)]
            room_order += [r.id for r in rooms if r.id not in room_order]
            need = item["remaining"]
            placed_here = 0
            last_reason = "No free day/slot combination."
            while need > 0:
                done = False
                for day in days:
                    if done:
                        break
                    for slot in slots:
                        if done:
                            break
                        for teacher_id in teacher_order:
                            if done:
                                break
                            for room_id in room_order:
                                ok, out = TimetableService.create_entry(
                                    session, semester_id, subject.id, teacher_id, room_id,
                                    day.id, slot.start_time, slot.end_time,
                                    lecture_type=subject.subject_type or "Theory")
                                if ok:
                                    placed_here += 1
                                    need -= 1
                                    done = True
                                    break
                                try:
                                    msgs = [c.message for c in out if getattr(c, "has_conflict", False)]
                                    if msgs:
                                        last_reason = msgs[0]
                                except (TypeError, AttributeError):
                                    pass
                if not done:
                    break
            result["placed"] += placed_here
            left = item["remaining"] - placed_here
            if left > 0:
                result["unplaced"].append({
                    "code": subject.code,
                    "name": subject.name,
                    "remaining": left,
                    "reason": last_reason,
                })
        return result
