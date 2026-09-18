from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import TimetableEntry, TeacherAvailability, RoomAvailability, TimeSlot, Subject
from app.utils.helpers import do_overlap, time_to_minutes

@dataclass
class ConflictResult:
    has_conflict: bool
    conflict_type: str  # teacher/semester/room/lab/availability/break/subject_limit/time
    message: str
    details: Optional[Dict[str, Any]] = None

class ConflictService:
    """Independent of GUI - pure conflict detection logic."""

    @staticmethod
    def check_time_valid(start_time: str, end_time: str) -> ConflictResult:
        try:
            s = time_to_minutes(start_time)
            e = time_to_minutes(end_time)
        except ValueError as ve:
            return ConflictResult(True, "time", str(ve))
        if e <= s:
            return ConflictResult(True, "time", "End time must be after start time.")
        return ConflictResult(False, "", "")

    @staticmethod
    def check_teacher_conflict(session: Session, teacher_id: int, day_id: int, start_time: str, end_time: str, exclude_id: Optional[int] = None) -> ConflictResult:
        q = session.query(TimetableEntry).filter(
            TimetableEntry.teacher_id == teacher_id,
            TimetableEntry.day_id == day_id
        )
        if exclude_id:
            q = q.filter(TimetableEntry.id != exclude_id)
        for entry in q.all():
            if do_overlap(entry.start_time, entry.end_time, start_time, end_time):
                # Fetch details for message
                subj = session.query(Subject).filter(Subject.id == entry.subject_id).first()
                sem_name = entry.semester.name if entry.semester else f"Semester {entry.semester_id}"
                subj_name = subj.name if subj else f"Subject {entry.subject_id}"
                teacher_name = entry.teacher.name if entry.teacher else f"Teacher {teacher_id}"
                day_name = entry.day.name if entry.day else f"Day {day_id}"
                msg = f"Teacher Conflict: {teacher_name} is already teaching {subj_name} for {sem_name} on {day_name} from {entry.start_time}-{entry.end_time}. The requested lecture from {start_time}-{end_time} overlaps."
                return ConflictResult(True, "teacher", msg, {"existing": entry})
        return ConflictResult(False, "", "")

    @staticmethod
    def check_semester_conflict(session: Session, semester_id: int, day_id: int, start_time: str, end_time: str, exclude_id: Optional[int] = None) -> ConflictResult:
        q = session.query(TimetableEntry).filter(
            TimetableEntry.semester_id == semester_id,
            TimetableEntry.day_id == day_id
        )
        if exclude_id:
            q = q.filter(TimetableEntry.id != exclude_id)
        for entry in q.all():
            if do_overlap(entry.start_time, entry.end_time, start_time, end_time):
                sem_name = entry.semester.name if entry.semester else f"Semester {semester_id}"
                msg = f"Semester Conflict: {sem_name} already has a lecture ({entry.subject.name if entry.subject else ''}) on {entry.day.name if entry.day else ''} from {entry.start_time}-{entry.end_time}. Requested {start_time}-{end_time} overlaps."
                return ConflictResult(True, "semester", msg, {"existing": entry})
        return ConflictResult(False, "", "")

    @staticmethod
    def check_room_conflict(session: Session, room_id: int, day_id: int, start_time: str, end_time: str, exclude_id: Optional[int] = None) -> ConflictResult:
        q = session.query(TimetableEntry).filter(
            TimetableEntry.room_id == room_id,
            TimetableEntry.day_id == day_id
        )
        if exclude_id:
            q = q.filter(TimetableEntry.id != exclude_id)
        for entry in q.all():
            if do_overlap(entry.start_time, entry.end_time, start_time, end_time):
                room_name = entry.room.name if entry.room else f"Room {room_id}"
                sem_name = entry.semester.name if entry.semester else ""
                msg = f"Room Conflict: {room_name} is already occupied by {sem_name} ({entry.subject.name if entry.subject else ''}) on {entry.day.name if entry.day else ''} from {entry.start_time}-{entry.end_time}. Requested {start_time}-{end_time} overlaps."
                return ConflictResult(True, "room", msg, {"existing": entry})
        return ConflictResult(False, "", "")

    @staticmethod
    def check_teacher_availability(session: Session, teacher_id: int, day_id: int, start_time: str, end_time: str) -> ConflictResult:
        q = session.query(TeacherAvailability).filter(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.day_id == day_id,
            TeacherAvailability.is_unavailable == True
        )
        for av in q.all():
            if do_overlap(av.start_time, av.end_time, start_time, end_time):
                teacher = av.teacher
                tname = teacher.name if teacher else f"Teacher {teacher_id}"
                msg = f"Teacher Availability Conflict: {tname} is unavailable on {av.day.name if av.day else ''} from {av.start_time}-{av.end_time} ({av.reason}). Requested {start_time}-{end_time} overlaps."
                return ConflictResult(True, "teacher_availability", msg, {"availability": av})
        return ConflictResult(False, "", "")

    @staticmethod
    def check_room_availability(session: Session, room_id: int, day_id: int, start_time: str, end_time: str) -> ConflictResult:
        q = session.query(RoomAvailability).filter(
            RoomAvailability.room_id == room_id,
            RoomAvailability.day_id == day_id,
            RoomAvailability.is_unavailable == True
        )
        for av in q.all():
            if do_overlap(av.start_time, av.end_time, start_time, end_time):
                room = av.room
                rname = room.name if room else f"Room {room_id}"
                msg = f"Room Availability Conflict: {rname} is unavailable on {av.day.name if av.day else ''} from {av.start_time}-{av.end_time} ({av.reason}). Requested {start_time}-{end_time} overlaps."
                return ConflictResult(True, "room_availability", msg, {"availability": av})
        return ConflictResult(False, "", "")

    @staticmethod
    def check_break_conflict(session: Session, day_id: int, start_time: str, end_time: str) -> ConflictResult:
        # Breaks are stored as time_slots with is_break=True. For simplicity, breaks apply to all days.
        # Check if requested time overlaps any break slot
        breaks = session.query(TimeSlot).filter(TimeSlot.is_break == True, TimeSlot.is_enabled == True).all()
        for b in breaks:
            if do_overlap(b.start_time, b.end_time, start_time, end_time):
                bname = b.break_name or "Break"
                msg = f"Break Conflict: Requested time {start_time}-{end_time} overlaps with break period {b.start_time}-{b.end_time} ({bname})."
                return ConflictResult(True, "break", msg, {"break": b})
        return ConflictResult(False, "", "")

    @staticmethod
    def check_subject_limit(session: Session, subject_id: int) -> ConflictResult:
        subj = session.query(Subject).filter(Subject.id == subject_id).first()
        if not subj:
            return ConflictResult(True, "subject", "Subject not found.")
        scheduled = session.query(TimetableEntry).filter(TimetableEntry.subject_id == subject_id).count()
        if scheduled >= subj.required_lectures_per_week:
            msg = f"Subject Limit: {subj.name} ({subj.code}) already has {scheduled}/{subj.required_lectures_per_week} lectures scheduled. Cannot add more."
            return ConflictResult(True, "subject_limit", msg, {"scheduled": scheduled, "required": subj.required_lectures_per_week})
        return ConflictResult(False, "", "", {"scheduled": scheduled, "required": subj.required_lectures_per_week})

    @staticmethod
    def validate_all(session: Session, semester_id: int, subject_id: int, teacher_id: int, room_id: int, day_id: int, start_time: str, end_time: str, exclude_id: Optional[int] = None, check_subject_limit: bool = False) -> List[ConflictResult]:
        conflicts = []
        # 1. time valid
        cr = ConflictService.check_time_valid(start_time, end_time)
        if cr.has_conflict:
            conflicts.append(cr)
            return conflicts  # no point checking further
        # 2. break
        cr = ConflictService.check_break_conflict(session, day_id, start_time, end_time)
        if cr.has_conflict:
            conflicts.append(cr)
        # 3. teacher availability
        cr = ConflictService.check_teacher_availability(session, teacher_id, day_id, start_time, end_time)
        if cr.has_conflict:
            conflicts.append(cr)
        # 4. room availability
        cr = ConflictService.check_room_availability(session, room_id, day_id, start_time, end_time)
        if cr.has_conflict:
            conflicts.append(cr)
        # 5. teacher conflict
        cr = ConflictService.check_teacher_conflict(session, teacher_id, day_id, start_time, end_time, exclude_id)
        if cr.has_conflict:
            conflicts.append(cr)
        # 6. semester conflict
        cr = ConflictService.check_semester_conflict(session, semester_id, day_id, start_time, end_time, exclude_id)
        if cr.has_conflict:
            conflicts.append(cr)
        # 7. room conflict
        cr = ConflictService.check_room_conflict(session, room_id, day_id, start_time, end_time, exclude_id)
        if cr.has_conflict:
            conflicts.append(cr)
        # 8. subject limit (optional, warn only if explicitly checked)
        if check_subject_limit:
            cr = ConflictService.check_subject_limit(session, subject_id)
            if cr.has_conflict:
                conflicts.append(cr)
        return conflicts

    @staticmethod
    def find_available_slots(session: Session, semester_id: int, teacher_id: int, room_id: int, duration_minutes: int, day_ids: Optional[List[int]] = None, start_bound: str = "08:00", end_bound: str = "17:00", step_minutes: int = 30) -> List[Dict[str, Any]]:
        """Find all slots where teacher, semester, room, availabilities and breaks are free."""
        from app.models import WorkingDay
        if day_ids is None:
            enabled_days = session.query(WorkingDay).filter(WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()
            day_ids = [d.id for d in enabled_days]
        # Pre-fetch day objects
        day_map = {d.id: d for d in session.query(WorkingDay).filter(WorkingDay.id.in_(day_ids)).all()}
        results = []
        s_bound = time_to_minutes(start_bound)
        e_bound = time_to_minutes(end_bound)
        # iterate days and times
        for day_id in day_ids:
            cur = s_bound
            while cur + duration_minutes <= e_bound:
                st = f"{cur//60:02d}:{cur%60:02d}"
                et = f"{(cur+duration_minutes)//60:02d}:{(cur+duration_minutes)%60:02d}"
                # Check all conflicts
                conflicts = ConflictService.validate_all(session, semester_id, 1, teacher_id, room_id, day_id, st, et, exclude_id=None)
                # validate_all needs subject_id but for slot finder we don't care about subject_limit; pass dummy 1
                # However we passed subject 1 which may not belong to semester; but teacher/room/semester checks are what matter
                # Filter out subject_limit if present (we didn't enable check_subject_limit=True, so fine)
                # Also need to handle break/availability/teacher/semester/room
                has = any(c.has_conflict for c in conflicts)
                if not has:
                    results.append({"day_id": day_id, "day_name": day_map[day_id].name if day_id in day_map else str(day_id), "start_time": st, "end_time": et})
                cur += step_minutes
        return results

    @staticmethod
    def suggest_alternative_slots(session: Session, semester_id: int, teacher_id: int, room_id: int, duration_minutes: int, day_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Suggest up to limit alternative slots, prioritizing same day then other days."""
        from app.models import WorkingDay
        # Try same day first
        suggestions = []
        if day_id is not None:
            avail = ConflictService.find_available_slots(session, semester_id, teacher_id, room_id, duration_minutes, day_ids=[day_id])
            suggestions.extend(avail)
            if len(suggestions) >= limit:
                return suggestions[:limit]
        # Then other days
        all_days = session.query(WorkingDay).filter(WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()
        other_ids = [d.id for d in all_days if d.id != day_id]
        if other_ids:
            avail = ConflictService.find_available_slots(session, semester_id, teacher_id, room_id, duration_minutes, day_ids=other_ids)
            suggestions.extend(avail)
        return suggestions[:limit]

    @staticmethod
    def calculate_timetable_completion(session: Session, semester_id: int) -> Dict[str, Any]:
        from app.models import Subject
        subjects = session.query(Subject).filter(Subject.semester_id == semester_id).all()
        required = sum(s.required_lectures_per_week for s in subjects)
        scheduled = session.query(TimetableEntry).filter(TimetableEntry.semester_id == semester_id).count()
        pct = (scheduled / required * 100) if required > 0 else 0
        return {"required": required, "scheduled": scheduled, "remaining": max(0, required - scheduled), "completion_pct": round(pct, 1)}

    @staticmethod
    def calculate_teacher_workload(session: Session, teacher_id: int) -> Dict[str, Any]:
        scheduled = session.query(TimetableEntry).filter(TimetableEntry.teacher_id == teacher_id).count()
        # Could compute weekly hours
        entries = session.query(TimetableEntry).filter(TimetableEntry.teacher_id == teacher_id).all()
        total_minutes = 0
        for e in entries:
            try:
                total_minutes += time_to_minutes(e.end_time) - time_to_minutes(e.start_time)
            except:
                pass
        return {"lectures": scheduled, "hours": round(total_minutes / 60, 1)}

    @staticmethod
    def detect_all_conflicts(session: Session) -> List[Dict[str, Any]]:
        """Scan entire timetable for existing conflicts (should be zero if validations work, but detect manual DB corruption)."""
        entries = session.query(TimetableEntry).all()
        conflicts = []
        # Check pairwise same day overlaps
        for i, a in enumerate(entries):
            for b in entries[i+1:]:
                if a.day_id != b.day_id:
                    continue
                if not do_overlap(a.start_time, a.end_time, b.start_time, b.end_time):
                    continue
                # Now check which resource overlaps
                if a.teacher_id == b.teacher_id:
                    conflicts.append({"type": "teacher", "entries": (a, b), "message": f"Teacher {a.teacher.name if a.teacher else a.teacher_id} double-booked on {a.day.name} {a.start_time}-{a.end_time} vs {b.start_time}-{b.end_time}"})
                if a.semester_id == b.semester_id:
                    conflicts.append({"type": "semester", "entries": (a, b), "message": f"Semester {a.semester.name} double-booked on {a.day.name} {a.start_time}-{a.end_time} vs {b.start_time}-{b.end_time}"})
                if a.room_id == b.room_id:
                    conflicts.append({"type": "room", "entries": (a, b), "message": f"Room {a.room.name if a.room else a.room_id} double-booked on {a.day.name} {a.start_time}-{a.end_time} vs {b.start_time}-{b.end_time}"})
        return conflicts
