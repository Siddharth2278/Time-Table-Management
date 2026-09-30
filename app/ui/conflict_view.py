from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QGroupBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.database import get_session
from app.services.conflict_service import ConflictService

class ConflictView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        title = QLabel("Conflict Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        layout.addWidget(title)
        sub = QLabel("Detects teacher, semester, room/lab conflicts and availability violations. All overlaps use: existingStart < newEnd AND existingEnd > newStart")
        sub.setStyleSheet("color: #64748B; font-size: 11px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        btns = QHBoxLayout()
        self.scan_btn = QPushButton("Scan All Conflicts")
        self.scan_btn.setObjectName("PrimaryButton")
        self.scan_btn.clicked.connect(self.scan)
        btns.addWidget(self.scan_btn)
        self.clear_btn = QPushButton("Clear Table")
        self.clear_btn.setObjectName("SecondaryButton")
        self.clear_btn.clicked.connect(self.clear_table)
        btns.addWidget(self.clear_btn)
        btns.addStretch()
        layout.addLayout(btns)

        # Summary labels
        self.summary = QLabel("")
        self.summary.setStyleSheet("font-weight: 600; padding: 8px; border-radius: 8px;")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Type", "Day/Time", "Resources", "Message"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 120)
        layout.addWidget(self.table)

        # Legend
        legend = QLabel("Types: Teacher • Semester • Room/Lab • Availability • Break • Subject Limit\nGreen = No conflicts  •  Red = Conflict found")
        legend.setStyleSheet("color: #64748B; font-size: 11px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px;")
        layout.addWidget(legend)

    def clear_table(self):
        self.table.setRowCount(0)
        self.summary.setText("")
        self.summary.setStyleSheet("font-weight: 600; padding: 8px; border-radius: 8px;")

    def refresh(self):
        self.scan()

    def scan(self):
        session = get_session()
        try:
            conflicts = ConflictService.detect_all_conflicts(session)
            # Also check availability conflicts that are not captured by pairwise
            # For each entry, check teacher/room availability and break
            from app.models import TimetableEntry, TeacherAvailability, RoomAvailability, TimeSlot
            from app.utils.helpers import do_overlap
            entries = session.query(TimetableEntry).all()
            avail_conflicts = []
            for e in entries:
                # teacher availability
                tas = session.query(TeacherAvailability).filter(TeacherAvailability.teacher_id==e.teacher_id, TeacherAvailability.day_id==e.day_id, TeacherAvailability.is_unavailable==True).all()
                for ta in tas:
                    if do_overlap(ta.start_time, ta.end_time, e.start_time, e.end_time):
                        avail_conflicts.append({"type": "teacher_availability", "entry": e, "av": ta, "message": f"Teacher {e.teacher.name if e.teacher else ''} scheduled during unavailable period {ta.start_time}-{ta.end_time} ({ta.reason})"})
                ras = session.query(RoomAvailability).filter(RoomAvailability.room_id==e.room_id, RoomAvailability.day_id==e.day_id, RoomAvailability.is_unavailable==True).all()
                for ra in ras:
                    if do_overlap(ra.start_time, ra.end_time, e.start_time, e.end_time):
                        avail_conflicts.append({"type": "room_availability", "entry": e, "av": ra, "message": f"Room {e.room.name if e.room else ''} scheduled during unavailable period {ra.start_time}-{ra.end_time} ({ra.reason})"})
                breaks = session.query(TimeSlot).filter(TimeSlot.is_break==True, TimeSlot.is_enabled==True).all()
                for b in breaks:
                    if do_overlap(b.start_time, b.end_time, e.start_time, e.end_time):
                        avail_conflicts.append({"type": "break", "entry": e, "break": b, "message": f"Lecture overlaps break {b.start_time}-{b.end_time} ({b.break_name})"})

            total = len(conflicts) + len(avail_conflicts)
            if total == 0:
                self.summary.setText("No conflicts detected. Timetable is clean.")
                self.summary.setStyleSheet("background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; padding: 10px; border-radius: 8px; font-weight: 700;")
            else:
                self.summary.setText(f"{total} conflict(s) found: {len(conflicts)} scheduling + {len(avail_conflicts)} availability/break")
                self.summary.setStyleSheet("background: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; padding: 10px; border-radius: 8px; font-weight: 700;")

            # Combine into table
            self.table.setRowCount(total)
            row = 0
            for c in conflicts:
                a, b = c["entries"]
                typ = c["type"]
                # Map type to display
                type_label = {"teacher": "Teacher", "semester": "Semester", "room": "Room/Lab"}.get(typ, typ)
                self.table.setItem(row, 0, QTableWidgetItem(type_label))
                day = a.day.name if a.day else ""
                time = f"{a.start_time}-{a.end_time} vs {b.start_time}-{b.end_time}"
                self.table.setItem(row, 1, QTableWidgetItem(f"{day} {time}"))
                if typ == "teacher":
                    res = a.teacher.name if a.teacher else str(a.teacher_id)
                elif typ == "semester":
                    res = a.semester.name if a.semester else str(a.semester_id)
                else:
                    res = a.room.name if a.room else str(a.room_id)
                self.table.setItem(row, 2, QTableWidgetItem(res))
                self.table.setItem(row, 3, QTableWidgetItem(c["message"]))
                # Color
                for col in range(4):
                    it = self.table.item(row, col)
                    if c["type"] in ("teacher", "semester", "room"):
                        it.setBackground(QColor("#EFF6FF"))
                    else:
                        it.setBackground(QColor("#FEF9E7"))
                row += 1
            for c in avail_conflicts:
                typ = c["type"]
                display = {"teacher_availability": "Teacher Unavail", "room_availability": "Room Unavail", "break": "Break"}.get(typ, typ)
                e = c["entry"]
                self.table.setItem(row, 0, QTableWidgetItem(display))
                day = e.day.name if e.day else ""
                self.table.setItem(row, 1, QTableWidgetItem(f"{day} {e.start_time}-{e.end_time}"))
                res = (e.teacher.name if e.teacher else "") if "teacher" in typ else (e.room.name if e.room else "")
                if typ == "break":
                    res = c["break"].break_name if "break" in c else "Break"
                self.table.setItem(row, 2, QTableWidgetItem(res))
                self.table.setItem(row, 3, QTableWidgetItem(c["message"]))
                for col in range(4):
                    it = self.table.item(row, col)
                    it.setBackground(QColor("#FEF9E7"))
                row += 1
            self.table.resizeRowsToContents()
        finally:
            session.close()
