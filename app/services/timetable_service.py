from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import TimetableEntry, Subject, Semester, Teacher, Room, WorkingDay
from app.services.conflict_service import ConflictService, ConflictResult

class TimetableService:

    @staticmethod
    def create_entry(session: Session, semester_id: int, subject_id: int, teacher_id: int, room_id: int, day_id: int, start_time: str, end_time: str, lecture_type: str = "Theory", academic_year: str = "2026-27", check_subject_limit: bool = False) -> tuple[bool, List[ConflictResult] | TimetableEntry]:
        # Validate required fields
        if not all([semester_id, subject_id, teacher_id, room_id, day_id, start_time, end_time]):
            return False, [ConflictResult(True, "validation", "All fields are required.")]
        conflicts = ConflictService.validate_all(session, semester_id, subject_id, teacher_id, room_id, day_id, start_time, end_time, exclude_id=None, check_subject_limit=check_subject_limit)
        has = [c for c in conflicts if c.has_conflict]
        if has:
            return False, has
        # Validate working day enabled
        day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
        if not day or not day.is_enabled:
            return False, [ConflictResult(True, "validation", f"Selected day {(day.name if day else day_id)} is not a working day.")]
        # All good, create
        try:
            entry = TimetableEntry(
                semester_id=semester_id, subject_id=subject_id, teacher_id=teacher_id, room_id=room_id,
                day_id=day_id, start_time=start_time, end_time=end_time, lecture_type=lecture_type, academic_year=academic_year
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return True, entry
        except SQLAlchemyError as e:
            session.rollback()
            return False, [ConflictResult(True, "database", f"Database error: {str(e)}")]

    @staticmethod
    def update_entry(session: Session, entry_id: int, **kwargs) -> tuple[bool, List[ConflictResult] | TimetableEntry]:
        entry = session.query(TimetableEntry).filter(TimetableEntry.id == entry_id).first()
        if not entry:
            return False, [ConflictResult(True, "validation", "Timetable entry not found.")]
        # Prepare new values, falling back to existing
        semester_id = kwargs.get("semester_id", entry.semester_id)
        subject_id = kwargs.get("subject_id", entry.subject_id)
        teacher_id = kwargs.get("teacher_id", entry.teacher_id)
        room_id = kwargs.get("room_id", entry.room_id)
        day_id = kwargs.get("day_id", entry.day_id)
        start_time = kwargs.get("start_time", entry.start_time)
        end_time = kwargs.get("end_time", entry.end_time)
        lecture_type = kwargs.get("lecture_type", entry.lecture_type)
        academic_year = kwargs.get("academic_year", entry.academic_year)

        # Validate working day
        day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
        if not day or not day.is_enabled:
            return False, [ConflictResult(True, "validation", f"Selected day {(day.name if day else day_id)} is not a working day.")]

        conflicts = ConflictService.validate_all(session, semester_id, subject_id, teacher_id, room_id, day_id, start_time, end_time, exclude_id=entry_id, check_subject_limit=False)
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
        return session.query(TimetableEntry).filter(TimetableEntry.semester_id == semester_id).order_by(TimetableEntry.day_id, TimetableEntry.start_time).all()

    @staticmethod
    def get_teacher_timetable(session: Session, teacher_id: int) -> List[TimetableEntry]:
        return session.query(TimetableEntry).filter(TimetableEntry.teacher_id == teacher_id).order_by(TimetableEntry.day_id, TimetableEntry.start_time).all()

    @staticmethod
    def get_room_timetable(session: Session, room_id: int) -> List[TimetableEntry]:
        return session.query(TimetableEntry).filter(TimetableEntry.room_id == room_id).order_by(TimetableEntry.day_id, TimetableEntry.start_time).all()
