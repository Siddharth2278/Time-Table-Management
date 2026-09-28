from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base

class Semester(Base):
    __tablename__ = "semesters"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # Semester 1..6
    code = Column(String(20), unique=True)
    status = Column(String(20), default="Active")
    academic_year = Column(String(20), default="2026-27")

    subjects = relationship("Subject", back_populates="semester", cascade="all, delete-orphan")
    timetable_entries = relationship("TimetableEntry", back_populates="semester")

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    department = Column(String(100))
    designation = Column(String(100))
    status = Column(String(20), default="Active")  # Active/Inactive

    subjects = relationship("Subject", back_populates="assigned_teacher")
    timetable_entries = relationship("TimetableEntry", back_populates="teacher")
    availabilities = relationship("TeacherAvailability", back_populates="teacher", cascade="all, delete-orphan")

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    room_number = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)  # Classroom/Laboratory/Seminar Hall
    capacity = Column(Integer, default=60)
    status = Column(String(20), default="Available")

    subjects = relationship("Subject", back_populates="assigned_room")
    timetable_entries = relationship("TimetableEntry", back_populates="room")
    availabilities = relationship("RoomAvailability", back_populates="room", cascade="all, delete-orphan")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False)
    subject_type = Column(String(50), nullable=False)  # Theory/Practical/Lab/Tutorial
    required_lectures_per_week = Column(Integer, default=3)
    lecture_duration = Column(Integer, default=60)  # minutes
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    room_requirement = Column(String(50), default="Classroom")

    semester = relationship("Semester", back_populates="subjects")
    assigned_teacher = relationship("Teacher", back_populates="subjects")
    assigned_room = relationship("Room", back_populates="subjects")
    timetable_entries = relationship("TimetableEntry", back_populates="subject")

class WorkingDay(Base):
    __tablename__ = "working_days"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)  # Monday...
    is_enabled = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    timetable_entries = relationship("TimetableEntry", back_populates="day")

class TimeSlot(Base):
    __tablename__ = "time_slots"
    id = Column(Integer, primary_key=True)
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)
    label = Column(String(100))
    is_break = Column(Boolean, default=False)
    break_name = Column(String(100), default="")
    is_enabled = Column(Boolean, default=True)

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    day_id = Column(Integer, ForeignKey("working_days.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    lecture_type = Column(String(50), default="Theory")
    academic_year = Column(String(20), default="2026-27")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        UniqueConstraint("semester_id", "day_id", "start_time", "end_time", "subject_id", name="uq_entry_exact"),
        Index("ix_entry_teacher_day", "teacher_id", "day_id"),
        Index("ix_entry_room_day", "room_id", "day_id"),
        Index("ix_entry_sem_day", "semester_id", "day_id"),
    )

    semester = relationship("Semester", back_populates="timetable_entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    teacher = relationship("Teacher", back_populates="timetable_entries")
    room = relationship("Room", back_populates="timetable_entries")
    day = relationship("WorkingDay", back_populates="timetable_entries")

class TeacherAvailability(Base):
    __tablename__ = "teacher_availability"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    day_id = Column(Integer, ForeignKey("working_days.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    is_unavailable = Column(Boolean, default=True)
    reason = Column(String(200), default="")

    teacher = relationship("Teacher", back_populates="availabilities")
    day = relationship("WorkingDay")

class RoomAvailability(Base):
    __tablename__ = "room_availability"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    day_id = Column(Integer, ForeignKey("working_days.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    is_unavailable = Column(Boolean, default=True)
    reason = Column(String(200), default="")

    room = relationship("Room", back_populates="availabilities")
    day = relationship("WorkingDay")

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500), default="")
