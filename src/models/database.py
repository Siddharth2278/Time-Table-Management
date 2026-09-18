"""Database models for College Timetable Management System."""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, 
    ForeignKey, CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Setting(Base):
    """Application settings stored in database."""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now)
    
    __table_args__ = (
        UniqueConstraint('key', name='uq_settings_key'),
    )


class WorkingDay(Base):
    """Working days configuration."""
    __tablename__ = 'working_days'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('name', name='uq_working_day_name'),
        Index('ix_working_day_order', 'display_order'),
    )


class TimeSlot(Base):
    """Time slots for scheduling."""
    __tablename__ = 'time_slots'
    
    id = Column(Integer, primary_key=True)
    start_time = Column(String(10), nullable=False)  # e.g., "08:00"
    end_time = Column(String(10), nullable=False)   # e.g., "09:00"
    duration_minutes = Column(Integer, nullable=False)
    display_label = Column(String(20), nullable=False)  # e.g., "08:00-09:00"
    is_break = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('start_time', 'end_time', name='uq_time_slot_range'),
        Index('ix_time_slot_start', 'start_time'),
    )


class Teacher(Base):
    """Teacher management."""
    __tablename__ = 'teachers'
    
    id = Column(Integer, primary_key=True)
    teacher_id = Column(String(20), unique=True, nullable=False)  # e.g., T001
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    department = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=False)  # e.g., Professor, Associate Professor
    status = Column(String(20), default='Active', nullable=False)  # Active, On Leave, etc.
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('teacher_id', name='uq_teacher_id'),
        UniqueConstraint('email', name='uq_teacher_email'),
        Index('ix_teacher_name', 'name'),
    )
    
    # Relationships
    availability = relationship("TeacherAvailability", back_populates="teacher")
    assigned_lectures = relationship("TimetableEntry", back_populates="teacher")


class TeacherAvailability(Base):
    """Teacher availability/unavailability configuration."""
    __tablename__ = 'teacher_availability'
    
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False)
    day_id = Column(Integer, ForeignKey('working_days.id'), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    is_unavailable = Column(Boolean, default=True, nullable=False)  # True = unavailable, False = available slot
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('teacher_id', 'day_id', 'start_time', 'end_time', name='uq_teacher_avail_range'),
        Index('ix_teacher_avail_teacher', 'teacher_id'),
        Index('ix_teacher_avail_day', 'day_id'),
    )
    
    # Relationships
    teacher = relationship("Teacher", back_populates="availability")


class Subject(Base):
    """Subject management."""
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    subject_code = Column(String(20), unique=True, nullable=False)  # e.g., MATH101
    subject_name = Column(String(100), nullable=False)
    semester = Column(Integer, nullable=False)  # 1-6
    subject_type = Column(String(20), nullable=False)  # Theory, Practical, Lab, Tutorial
    required_lectures_per_week = Column(Integer, default=0, nullable=False)
    lecture_duration = Column(Integer, default=60, nullable=False)  # minutes
    assigned_teacher_id = Column(Integer, ForeignKey('teachers.id', ondelete='SET NULL'))
    room_requirement = Column(String(100))  # e.g., "Classroom", "Laboratory"
    status = Column(String(20), default='Active', nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('subject_code', name='uq_subject_code'),
        UniqueConstraint('subject_name', 'semester', name='uq_subject_name_semester'),
        Index('ix_subject_semester', 'semester'),
        Index('ix_subject_type', 'subject_type'),
    )
    
    # Relationships
    teacher = relationship("Teacher", backref="assigned_subjects")
    lectures = relationship("TimetableEntry", back_populates="subject")


class Semester(Base):
    """Semester management - exactly 6 semesters."""
    __tablename__ = 'semesters'
    
    id = Column(Integer, primary_key=True)
    semester_number = Column(Integer, unique=True, nullable=False)  # 1-6
    name = Column(String(20), nullable=False)  # "Semester 1", "Semester 2", etc.
    academic_year = Column(String(20), nullable=False, default="2026-27")
    status = Column(String(20), default='Active', nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('semester_number', name='uq_semester_number'),
        UniqueConstraint('name', name='uq_semester_name'),
        Index('ix_semester_number', 'semester_number'),
    )
    
    # Relationships
    lectures = relationship("TimetableEntry", back_populates="semester")


class Room(Base):
    """Classroom and Laboratory management."""
    __tablename__ = 'rooms'
    
    id = Column(Integer, primary_key=True)
    room_name = Column(String(100), nullable=False)  # e.g., "Room 101", "Lab 2"
    room_number = Column(String(20), nullable=False)  # e.g., "101", "204"
    room_type = Column(String(30), nullable=False)  # Classroom, Laboratory, Seminar Hall
    capacity = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default='Active', nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('room_number', name='uq_room_number'),
        UniqueConstraint('room_name', name='uq_room_name'),
        Index('ix_room_type', 'room_type'),
    )
    
    # Relationships
    assigned_lectures = relationship("TimetableEntry", back_populates="room")


class Laboratory(Base):
    """Laboratory-specific configuration (inherits from Rooms but with extra fields)."""
    __tablename__ = 'laboratories'
    
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey('rooms.id', ondelete='CASCADE'), unique=True, nullable=False)
    room_number = Column(String(20), nullable=False)
    room_name = Column(String(100), nullable=False)
    capacity = Column(Integer, default=0, nullable=False)
    equipment = Column(String(500))  # e.g., "Computers, Projector, AC"
    status = Column(String(20), default='Active', nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('room_number', name='uq_lab_room_number'),
    )
    
    # Relationships
    room = relationship("Room", backref="laboratory_details")
    assigned_lectures = relationship("TimetableEntry", back_populates="laboratory")


class TimetableEntry(Base):
    """Timetable entry - the main scheduling table."""
    __tablename__ = 'timetable_entries'
    
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey('semesters.id', ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='SET NULL'))
    teacher_id = Column(Integer, ForeignKey('teachers.id', ondelete('SET NULL')))
    room_id = Column(Integer, ForeignKey('rooms.id', ondelete('SET NULL')))
    laboratory_id = Column(Integer, ForeignKey('laboratories.id', ondelete='SET NULL'))
    day_id = Column(Integer, ForeignKey('working_days.id'), nullable=False)
    start_time = Column(String(10), nullable=False)  # e.g., "10:00"
    end_time = Column(String(10), nullable=False)   # e.g., "11:30"
    lecture_type = Column(String(20), nullable=False)  # Theory, Practical, Lab, Tutorial
    academic_year = Column(String(20), nullable=False, default="2026-27")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_entry_semester_day', 'semester_id', 'day_id'),
        Index('ix_entry_teacher_day', 'teacher_id', 'day_id'),
        Index('ix_entry_room_day', 'room_id', 'day_id'),
        Index('ix_entry_lab_day', 'laboratory_id', 'day_id'),
        Index('ix_entry_start_end', 'start_time', 'end_time'),
        UniqueConstraint(
            'semester_id', 'subject_id', 'day_id', 'start_time', 'end_time', 
            name='uq_entry_semester_subject_time',
            deferrable=True, initially='DEFERRED'
        ),
    )
    
    # Relationships
    semester = relationship("Semester", back_populates="lectures")
    subject = relationship("Subject", back_populates="lectures")
    teacher = relationship("Teacher", back_populates="assigned_lectures")
    room = relationship("Room", back_populates="assigned_lectures")
    laboratory = relationship("Laboratory", back_populates="assigned_lectures")


# Helper function to create engine
def create_engine_url(db_path="college_timetable.db"):
    """Create SQLAlchemy engine URL for SQLite."""
    import os
    # Use absolute path for the database
    if not os.path.isabs(db_path):
        # Store database in user data directory
        from pathlib import Path
        home = Path.home()
        db_path = str(home / "CollegeTimetable" / db_path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f"sqlite:///{db_path}"


def create_engine_config(db_path="college_timetable.db"):
    """Create SQLAlchemy engine with configuration."""
    from sqlalchemy import event
    engine = create_engine(
        create_engine_url(db_path),
        echo=False,
        future=True,
    )
    return engine


def create_all_tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all database tables."""
    Base.metadata.drop_all(engine)