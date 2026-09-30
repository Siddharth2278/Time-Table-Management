from PySide6.QtWidgets import (
    QFormLayout, QLabel, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QTimeEdit, QCheckBox
)
from PySide6.QtCore import QTime
from sqlalchemy.orm import Session
from app.database import get_session
from app.models import Teacher, Subject, Room, Semester, WorkingDay, TimeSlot, TeacherAvailability, RoomAvailability
from app.utils.validators import is_valid_email
from app.utils.helpers import time_to_minutes
from app.services.conflict_service import ConflictService
from app.ui.base_dialog import BaseDialog
from app.ui.modals import info as modal_info, error as modal_error


def show_error(parent, msg):
    # Keep validation and conflict text exactly as produced by the service.
    modal_error(parent, "Error", str(msg))

def show_info(parent, msg):
    modal_info(parent, "Info", str(msg))

class TeacherDialog(BaseDialog):
    def __init__(self, parent=None, teacher: Teacher | None = None):
        super().__init__(parent, "Edit Teacher" if teacher else "Add Teacher",
                         min_width=420)
        self.teacher = teacher
        form = QFormLayout()
        self.name_edit = QLineEdit(teacher.name if teacher else "")
        self.email_edit = QLineEdit(teacher.email if teacher else "")
        self.dept_edit = QLineEdit(teacher.department if teacher else "Computer Science")
        self.desig_combo = QComboBox()
        self.desig_combo.addItems(["Professor", "Associate Professor", "Assistant Professor", "Lecturer", "HOD"])
        if teacher and teacher.designation:
            idx = self.desig_combo.findText(teacher.designation)
            if idx >= 0:
                self.desig_combo.setCurrentIndex(idx)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])
        if teacher and teacher.status:
            self.status_combo.setCurrentText(teacher.status)
        form.addRow("Name*:", self.name_edit)
        form.addRow("Email:", self.email_edit)
        form.addRow("Department:", self.dept_edit)
        form.addRow("Designation:", self.desig_combo)
        form.addRow("Status:", self.status_combo)
        self.body_layout.addLayout(form)

    def accept(self):
        if not self.name_edit.text().strip():
            show_error(self, "Teacher name is required.")
            return
        if self.email_edit.text().strip() and not is_valid_email(self.email_edit.text().strip()):
            show_error(self, "Invalid email format.")
            return
        super().accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "department": self.dept_edit.text().strip(),
            "designation": self.desig_combo.currentText(),
            "status": self.status_combo.currentText()
        }

class RoomDialog(BaseDialog):
    def __init__(self, parent=None, room: Room | None = None):
        super().__init__(parent, "Edit Room/Lab" if room else "Add Room/Lab",
                         min_width=420)
        self.room = room
        form = QFormLayout()
        self.name_edit = QLineEdit(room.name if room else "")
        self.number_edit = QLineEdit(room.room_number if room else "")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Classroom", "Laboratory", "Seminar Hall"])
        if room and room.type:
            self.type_combo.setCurrentText(room.type)
        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 500)
        self.capacity_spin.setValue(room.capacity if room else 60)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Available", "Unavailable", "Maintenance"])
        if room and room.status:
            self.status_combo.setCurrentText(room.status)
        form.addRow("Name*:", self.name_edit)
        form.addRow("Room Number*:", self.number_edit)
        form.addRow("Type:", self.type_combo)
        form.addRow("Capacity:", self.capacity_spin)
        form.addRow("Status:", self.status_combo)
        self.body_layout.addLayout(form)

    def accept(self):
        if not self.name_edit.text().strip():
            show_error(self, "Name is required.")
            return
        if not self.number_edit.text().strip():
            show_error(self, "Room number is required.")
            return
        super().accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "room_number": self.number_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "capacity": self.capacity_spin.value(),
            "status": self.status_combo.currentText()
        }

class SubjectDialog(BaseDialog):
    def __init__(self, parent=None, subject: Subject | None = None, session: Session | None = None):
        super().__init__(parent, "Edit Subject" if subject else "Add Subject",
                         min_width=480)
        self.subject = subject
        self.session = session or get_session()
        self.owns_session = session is None
        form = QFormLayout()
        self.code_edit = QLineEdit(subject.code if subject else "")
        self.name_edit = QLineEdit(subject.name if subject else "")
        self.semester_combo = QComboBox()
        sems = self.session.query(Semester).order_by(Semester.id).all()
        for s in sems:
            self.semester_combo.addItem(s.name, s.id)
        if subject:
            idx = self.semester_combo.findData(subject.semester_id)
            if idx >= 0:
                self.semester_combo.setCurrentIndex(idx)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Theory", "Practical", "Lab", "Tutorial"])
        if subject and subject.subject_type:
            self.type_combo.setCurrentText(subject.subject_type)
        self.req_spin = QSpinBox()
        self.req_spin.setRange(1, 10)
        self.req_spin.setValue(subject.required_lectures_per_week if subject else 3)
        self.dur_combo = QComboBox()
        self.dur_combo.addItems(["30", "45", "60", "90", "120"])
        if subject:
            self.dur_combo.setCurrentText(str(subject.lecture_duration))
        else:
            self.dur_combo.setCurrentText("60")
        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem("-- None --", None)
        teachers = self.session.query(Teacher).filter(Teacher.status=="Active").order_by(Teacher.name).all()
        for t in teachers:
            self.teacher_combo.addItem(t.name, t.id)
        if subject and subject.teacher_id:
            idx = self.teacher_combo.findData(subject.teacher_id)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- None --", None)
        rooms = self.session.query(Room).filter(Room.status=="Available").order_by(Room.name).all()
        for r in rooms:
            self.room_combo.addItem(f"{r.name} ({r.room_number})", r.id)
        if subject and subject.room_id:
            idx = self.room_combo.findData(subject.room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
        form.addRow("Subject Code*:", self.code_edit)
        form.addRow("Subject Name*:", self.name_edit)
        form.addRow("Semester*:", self.semester_combo)
        form.addRow("Subject Type:", self.type_combo)
        form.addRow("Required Lectures/Week:", self.req_spin)
        form.addRow("Lecture Duration (mins):", self.dur_combo)
        form.addRow("Assigned Teacher:", self.teacher_combo)
        form.addRow("Assigned Room:", self.room_combo)
        self.body_layout.addLayout(form)

    def closeEvent(self, event):
        if self.owns_session:
            try:
                self.session.close()
            except:
                pass
        super().closeEvent(event)

    def accept(self):
        if not self.code_edit.text().strip():
            show_error(self, "Subject code is required.")
            return
        if not self.name_edit.text().strip():
            show_error(self, "Subject name is required.")
            return
        super().accept()

    def get_data(self):
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "semester_id": self.semester_combo.currentData(),
            "subject_type": self.type_combo.currentText(),
            "required_lectures_per_week": self.req_spin.value(),
            "lecture_duration": int(self.dur_combo.currentText()),
            "teacher_id": self.teacher_combo.currentData(),
            "room_id": self.room_combo.currentData(),
            "room_requirement": "Laboratory" if self.type_combo.currentText() in ["Lab", "Practical"] else "Classroom"
        }

class LectureDialog(BaseDialog):
    def __init__(self, parent=None, semester_id: int | None = None, day_id: int | None = None, start_time: str | None = None, end_time: str | None = None, entry=None):
        super().__init__(parent, "Edit Lecture" if entry else "Add Lecture",
                         min_width=520)
        self.entry = entry
        self.session = get_session()
        form = QFormLayout()
        # Semester
        self.sem_combo = QComboBox()
        sems = self.session.query(Semester).order_by(Semester.id).all()
        for s in sems:
            self.sem_combo.addItem(s.name, s.id)
        if entry:
            idx = self.sem_combo.findData(entry.semester_id)
            if idx >= 0:
                self.sem_combo.setCurrentIndex(idx)
        elif semester_id:
            idx = self.sem_combo.findData(semester_id)
            if idx >= 0:
                self.sem_combo.setCurrentIndex(idx)
        # Subject - filtered by semester
        self.subj_combo = QComboBox()
        self._populate_subjects()
        if entry:
            idx = self.subj_combo.findData(entry.subject_id)
            if idx >= 0:
                self.subj_combo.setCurrentIndex(idx)
        # Teacher
        self.teacher_combo = QComboBox()
        teachers = self.session.query(Teacher).filter(Teacher.status=="Active").order_by(Teacher.name).all()
        for t in teachers:
            self.teacher_combo.addItem(t.name, t.id)
        if entry:
            idx = self.teacher_combo.findData(entry.teacher_id)
            if idx >= 0:
                self.teacher_combo.setCurrentIndex(idx)
        # Room
        self.room_combo = QComboBox()
        rooms = self.session.query(Room).filter(Room.status=="Available").order_by(Room.name).all()
        for r in rooms:
            self.room_combo.addItem(f"{r.name} ({r.room_number}) - {r.type}", r.id)
        if entry:
            idx = self.room_combo.findData(entry.room_id)
            if idx >= 0:
                self.room_combo.setCurrentIndex(idx)
        # Day
        self.day_combo = QComboBox()
        days = self.session.query(WorkingDay).filter(WorkingDay.is_enabled==True).order_by(WorkingDay.sort_order).all()
        for d in days:
            self.day_combo.addItem(d.name, d.id)
        if entry:
            idx = self.day_combo.findData(entry.day_id)
            if idx >= 0:
                self.day_combo.setCurrentIndex(idx)
        elif day_id:
            idx = self.day_combo.findData(day_id)
            if idx >= 0:
                self.day_combo.setCurrentIndex(idx)
        # Time (guard malformed DB values)
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        def _to_qtime(v, fallback):
            try:
                h, m = map(int, str(v).split(":")[:2])
                if 0 <= h < 24 and 0 <= m < 60:
                    return QTime(h, m)
            except (ValueError, AttributeError, TypeError):
                pass
            return fallback
        if entry:
            self.start_edit.setTime(_to_qtime(entry.start_time, QTime(9, 0)))
            self.end_edit.setTime(_to_qtime(entry.end_time, QTime(10, 0)))
        else:
            self.start_edit.setTime(_to_qtime(start_time, QTime(9, 0)) if start_time else QTime(9, 0))
            self.end_edit.setTime(_to_qtime(end_time, QTime(10, 0)) if end_time else QTime(10, 0))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Theory", "Practical", "Lab", "Tutorial"])
        if entry and entry.lecture_type:
            self.type_combo.setCurrentText(entry.lecture_type)

        # Connect subject changes only after every dependent widget exists. The
        # previous order silently swallowed AttributeError and left new lectures
        # with the first teacher/room instead of the subject assignment.
        self.sem_combo.currentIndexChanged.connect(self._populate_subjects)
        self.subj_combo.currentIndexChanged.connect(self._on_subject_changed)

        form.addRow("Semester*:", self.sem_combo)
        form.addRow("Subject*:", self.subj_combo)
        form.addRow("Teacher*:", self.teacher_combo)
        form.addRow("Room/Lab*:", self.room_combo)
        form.addRow("Day*:", self.day_combo)
        form.addRow("Start Time*:", self.start_edit)
        form.addRow("End Time*:", self.end_edit)
        form.addRow("Lecture Type:", self.type_combo)
        self.body_layout.addLayout(form)

        # Info label for suggestions
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setObjectName("InfoBar")
        self.body_layout.addWidget(self.info_label)

        if not self.entry:
            self._on_subject_changed()

        self.find_btn = QPushButton("Find Available Slot")
        self.find_btn.setObjectName("SecondaryButton")
        self.find_btn.clicked.connect(self.find_slots)
        self.body_layout.addWidget(self.find_btn)

    def _set_info(self, text, banner):
        """Themed info line: 'InfoBar' neutral, 'BannerOk' success, 'BannerErr' error."""
        self.info_label.setText(text)
        self.info_label.setObjectName(banner)
        try:
            self.style().unpolish(self.info_label)
            self.style().polish(self.info_label)
        except Exception:
            pass

    def _populate_subjects(self):
        sem_id = self.sem_combo.currentData()
        self.subj_combo.blockSignals(True)
        self.subj_combo.clear()
        if sem_id is None:
            self.subj_combo.blockSignals(False)
            return
        try:
            subjects = self.session.query(Subject).filter(Subject.semester_id==sem_id).order_by(Subject.name).all()
            for s in subjects:
                self.subj_combo.addItem(f"{s.code} - {s.name}", s.id)
        except:
            pass
        self.subj_combo.blockSignals(False)
        # Auto-select teacher/room for first subject only after the dependent
        # controls have been constructed.
        if not self.entry and self.subj_combo.count() > 0 and hasattr(self, "teacher_combo"):
            self._on_subject_changed()

    def _on_subject_changed(self, idx=None):
        # Auto-select teacher/room/type when subject changes — specific, no manual teacher pick needed
        if not hasattr(self, "teacher_combo") or not hasattr(self, "room_combo") or not hasattr(self, "type_combo"):
            return
        subj_id = self.subj_combo.currentData()
        if not subj_id:
            return
        try:
            subj = self.session.query(Subject).filter(Subject.id==subj_id).first()
            if not subj:
                return
            # Existing lectures may intentionally use an override, so automatic
            # resource assignment is limited to new lectures.
            if not self.entry and subj.teacher_id:
                ti = self.teacher_combo.findData(subj.teacher_id)
                if ti >= 0:
                    self.teacher_combo.blockSignals(True)
                    self.teacher_combo.setCurrentIndex(ti)
                    self.teacher_combo.blockSignals(False)
            if not self.entry and subj.room_id:
                ri = self.room_combo.findData(subj.room_id)
                if ri >= 0:
                    self.room_combo.blockSignals(True)
                    self.room_combo.setCurrentIndex(ri)
                    self.room_combo.blockSignals(False)
            # Map subject type to lecture type
            if not self.entry and subj.subject_type:
                lt = subj.subject_type
                # Normalize: subject Lab -> Lab, Practical -> Practical
                idx_lt = self.type_combo.findText(lt)
                if idx_lt >= 0:
                    self.type_combo.blockSignals(True)
                    self.type_combo.setCurrentIndex(idx_lt)
                    self.type_combo.blockSignals(False)
            # Auto set end time based on subject lecture_duration for new entries
            if not self.entry and subj.lecture_duration:
                try:
                    start = self.start_edit.time()
                    dur = int(subj.lecture_duration)
                    end = start.addSecs(dur * 60)
                    self.end_edit.blockSignals(True)
                    self.end_edit.setTime(end)
                    self.end_edit.blockSignals(False)
                    self._set_info(f"Auto: {subj.code} → {subj.name} | Teacher: {self.teacher_combo.currentText()} | Room: {self.room_combo.currentText()} | Duration: {dur} min", "BannerOk")
                except:
                    pass
            elif self.entry:
                # For edit, just show hint
                self._set_info(f"Selected: {subj.code} — {subj.name} | Teacher: {self.teacher_combo.currentText()} | Room: {self.room_combo.currentText()}", "InfoBar")
        except Exception:
            pass

    def find_slots(self):
        sem_id = self.sem_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        room_id = self.room_combo.currentData()
        if not all([sem_id, teacher_id, room_id]):
            self.info_label.setText("Please select semester, teacher and room to find slots.")
            return
        # duration from time edits
        st = self.start_edit.time()
        et = self.end_edit.time()
        dur = (et.hour()*60+et.minute()) - (st.hour()*60+st.minute())
        if dur <= 0:
            dur = 60
        from app.services.conflict_service import ConflictService
        slots = ConflictService.find_available_slots(self.session, sem_id, teacher_id, room_id, dur)
        if not slots:
            self.info_label.setText("No available slots found for the selected criteria.")
            return
        # Show top 5
        txt = "Available: " + ", ".join([f"{s['day_name']} {s['start_time']}-{s['end_time']}" for s in slots[:5]])
        self.info_label.setText(txt)
        # Also popup
        msg = "\n".join([f"• {s['day_name']} {s['start_time']}-{s['end_time']}" for s in slots[:8]])
        modal_info(self, "Available Slots", msg)

    def accept(self):
        # Basic validation
        sem_id = self.sem_combo.currentData()
        subj_id = self.subj_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        room_id = self.room_combo.currentData()
        day_id = self.day_combo.currentData()
        start = self.start_edit.time().toString("HH:mm")
        end = self.end_edit.time().toString("HH:mm")
        if not all([sem_id, subj_id, teacher_id, room_id, day_id]):
            show_error(self, "All fields are required.")
            return
        # Time validation
        try:
            s = time_to_minutes(start)
            e = time_to_minutes(end)
            if e <= s:
                show_error(self, "End time must be after start time.")
                return
        except Exception as ex:
            show_error(self, str(ex))
            return
        # Check conflicts (if editing, exclude self)
        exclude = self.entry.id if self.entry else None
        conflicts = ConflictService.validate_all(self.session, sem_id, subj_id, teacher_id, room_id, day_id, start, end, exclude_id=exclude, check_subject_limit=True)
        has = [c for c in conflicts if c.has_conflict]
        if has:
            msgs = "\n\n".join([c.message for c in has])
            # Suggest alternatives
            try:
                dur = time_to_minutes(end) - time_to_minutes(start)
                suggestions = ConflictService.suggest_alternative_slots(self.session, sem_id, teacher_id, room_id, dur, day_id=day_id, limit=5)
                if suggestions:
                    msgs += "\n\nSuggested alternatives:\n" + "\n".join([f"• {s['day_name']} {s['start_time']}-{s['end_time']}" for s in suggestions])
            except:
                pass
            modal_error(self, "Conflict Detected", msgs)
            return
        super().accept()

    def get_data(self):
        return {
            "semester_id": self.sem_combo.currentData(),
            "subject_id": self.subj_combo.currentData(),
            "teacher_id": self.teacher_combo.currentData(),
            "room_id": self.room_combo.currentData(),
            "day_id": self.day_combo.currentData(),
            "start_time": self.start_edit.time().toString("HH:mm"),
            "end_time": self.end_edit.time().toString("HH:mm"),
            "lecture_type": self.type_combo.currentText()
        }

    def closeEvent(self, event):
        try:
            self.session.close()
        except:
            pass
        super().closeEvent(event)

class TimeSlotDialog(BaseDialog):
    def __init__(self, parent=None, slot: TimeSlot | None = None):
        super().__init__(parent, "Edit Time Slot" if slot else "Add Time Slot",
                         min_width=380)
        self.slot = slot
        form = QFormLayout()
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        if slot:
            sh, sm = map(int, slot.start_time.split(":"))
            eh, em = map(int, slot.end_time.split(":"))
            self.start_edit.setTime(QTime(sh, sm))
            self.end_edit.setTime(QTime(eh, em))
        else:
            self.start_edit.setTime(QTime(8, 0))
            self.end_edit.setTime(QTime(9, 0))
        self.is_break_check = QCheckBox("Is Break")
        self.is_break_check.setChecked(slot.is_break if slot else False)
        self.break_name_edit = QLineEdit(slot.break_name if slot and slot.break_name else "")
        self.break_name_edit.setPlaceholderText("e.g., Lunch Break")
        form.addRow("Start Time:", self.start_edit)
        form.addRow("End Time:", self.end_edit)
        form.addRow("", self.is_break_check)
        form.addRow("Break Name:", self.break_name_edit)
        self.body_layout.addLayout(form)

    def accept(self):
        s = self.start_edit.time().toString("HH:mm")
        e = self.end_edit.time().toString("HH:mm")
        try:
            if time_to_minutes(e) <= time_to_minutes(s):
                show_error(self, "End time must be after start time.")
                return
        except Exception as ex:
            show_error(self, str(ex))
            return
        if self.is_break_check.isChecked() and not self.break_name_edit.text().strip():
            show_error(self, "Break name is required when Is Break is checked.")
            return
        super().accept()

    def get_data(self):
        s = self.start_edit.time().toString("HH:mm")
        e = self.end_edit.time().toString("HH:mm")
        is_break = self.is_break_check.isChecked()
        label = f"{s}-{e}" + (f" ({self.break_name_edit.text().strip()})" if is_break else "")
        return {
            "start_time": s,
            "end_time": e,
            "label": label,
            "is_break": is_break,
            "break_name": self.break_name_edit.text().strip() if is_break else "",
            "is_enabled": True
        }

class AvailabilityDialog(BaseDialog):
    def __init__(self, parent=None, teacher_id=None, room_id=None, existing=None, is_teacher=True):
        super().__init__(parent, "Edit Unavailability" if existing else ("Add Teacher Unavailability" if is_teacher else "Add Room Unavailability"),
                         min_width=420)
        self.is_teacher = is_teacher
        self.existing = existing
        self.session = get_session()
        form = QFormLayout()
        self.entity_combo = QComboBox()
        if is_teacher:
            teachers = self.session.query(Teacher).order_by(Teacher.name).all()
            for t in teachers:
                self.entity_combo.addItem(t.name, t.id)
            if teacher_id:
                idx = self.entity_combo.findData(teacher_id)
                if idx >= 0:
                    self.entity_combo.setCurrentIndex(idx)
            elif existing:
                idx = self.entity_combo.findData(existing.teacher_id)
                if idx >= 0:
                    self.entity_combo.setCurrentIndex(idx)
        else:
            rooms = self.session.query(Room).order_by(Room.name).all()
            for r in rooms:
                self.entity_combo.addItem(f"{r.name} ({r.room_number})", r.id)
            if room_id:
                idx = self.entity_combo.findData(room_id)
                if idx >= 0:
                    self.entity_combo.setCurrentIndex(idx)
            elif existing:
                idx = self.entity_combo.findData(existing.room_id)
                if idx >= 0:
                    self.entity_combo.setCurrentIndex(idx)
        self.day_combo = QComboBox()
        days = self.session.query(WorkingDay).order_by(WorkingDay.sort_order).all()
        for d in days:
            self.day_combo.addItem(d.name, d.id)
        if existing:
            idx = self.day_combo.findData(existing.day_id)
            if idx >= 0:
                self.day_combo.setCurrentIndex(idx)
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        if existing:
            sh, sm = map(int, existing.start_time.split(":"))
            eh, em = map(int, existing.end_time.split(":"))
            self.start_edit.setTime(QTime(sh, sm))
            self.end_edit.setTime(QTime(eh, em))
        else:
            self.start_edit.setTime(QTime(9, 0))
            self.end_edit.setTime(QTime(11, 0))
        self.reason_edit = QLineEdit(existing.reason if existing and existing.reason else "")
        form.addRow("Teacher:" if is_teacher else "Room/Lab:", self.entity_combo)
        form.addRow("Day:", self.day_combo)
        form.addRow("Start:", self.start_edit)
        form.addRow("End:", self.end_edit)
        form.addRow("Reason:", self.reason_edit)
        self.body_layout.addLayout(form)

    def accept(self):
        s = self.start_edit.time().toString("HH:mm")
        e = self.end_edit.time().toString("HH:mm")
        if time_to_minutes(e) <= time_to_minutes(s):
            show_error(self, "End time must be after start time.")
            return
        super().accept()

    def get_data(self):
        return {
            "entity_id": self.entity_combo.currentData(),
            "day_id": self.day_combo.currentData(),
            "start_time": self.start_edit.time().toString("HH:mm"),
            "end_time": self.end_edit.time().toString("HH:mm"),
            "reason": self.reason_edit.text().strip()
        }

    def closeEvent(self, event):
        try:
            self.session.close()
        except:
            pass
        super().closeEvent(event)
