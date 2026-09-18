from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGroupBox, QPushButton
)
from PySide6.QtCore import Qt


class HelpView(QWidget):
    """Plain-language help for college administrators using the offline app."""

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("Help & How to Use")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #132A3A;")
        title_row.addWidget(title)
        title_row.addStretch()
        self.status = QLabel("Offline guide")
        self.status.setStyleSheet("color: #176B57; font-weight: 700; background: #E8F3F0; padding: 6px 10px; border-radius: 6px;")
        title_row.addWidget(self.status)
        outer.addLayout(title_row)

        subtitle = QLabel("Use this guide whenever you need a quick explanation of a page, button, or timetable rule.")
        subtitle.setStyleSheet("color: #70808B; font-size: 12px; padding-bottom: 6px;")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 4, 8, 4)
        layout.setSpacing(12)

        sections = [
            ("Start here", [
                "1. Open Settings and enter your college name, department, academic year, working hours, and working days.",
                "2. Add teachers, subjects, rooms, and laboratories from the left menu.",
                "3. Open Timetable, choose one of the six semesters, and choose Format Photo before generating your first timetable.",
                "4. Add lectures using the subject, teacher, room, day, start time, end time, and lecture type.",
            ]),
            ("Timetable Builder", [
                "Each semester has one timetable. Divisions are not used.",
                "Use Add Lecture to create an entry. Double-click a lecture or use Edit to change it.",
                "Use Delete to remove an entry. Deleting a lecture frees its teacher, semester slot, and room.",
                "Use Find Available Slot to see valid times for the selected teacher, room, semester, and duration.",
                "You can move lectures with drag and drop when the new position passes every validation check.",
            ]),
            ("Automatic conflict protection", [
                "A teacher cannot teach two classes at overlapping times, even when the classes belong to different semesters.",
                "A semester cannot have two lectures at the same time.",
                "A room or laboratory cannot be used by two lectures at the same time.",
                "Teacher and room unavailable periods, breaks, invalid times, and subject weekly limits are checked before saving.",
                "Back-to-back lectures are allowed. For example, 10:00–11:00 and 11:00–12:00 do not overlap.",
            ]),
            ("Management pages", [
                "Teachers: add, edit, search, delete, and view a teacher's timetable across all six semesters.",
                "Subjects: set the semester, type, required lectures per week, duration, assigned teacher, and room requirement.",
                "Rooms & Labs: manage classrooms, laboratories, seminar halls, capacity, and status.",
                "Semesters: view completion progress and open a semester timetable.",
                "Time Slots: add custom durations such as 30, 45, 60, 90, or 120 minutes and configure breaks.",
                "Availability: mark teacher or room periods as unavailable so the scheduler blocks those periods.",
            ]),
            ("Save, export, and protect your data", [
                "All data is stored locally in SQLite on this PC. The app works without internet, a browser, or a server.",
                "Use Backup & Restore to save a database backup or restore an earlier backup.",
                "From Timetable, export the current semester to PDF, Excel, or CSV, or use Print for a paper copy.",
                "Closing and reopening the app does not remove your timetable. Uninstalling preserves the database unless you explicitly delete it.",
            ]),
            ("When an error appears", [
                "Read the complete message in the error window. It identifies the exact teacher, semester, room, day, and time causing the problem.",
                "The message may include suggested alternative slots. Correct the conflicting field and try again.",
                "If a file or backup cannot be found, choose the file again from the relevant page.",
            ]),
        ]

        for heading, points in sections:
            group = QGroupBox(heading)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(14, 22, 14, 12)
            group_layout.setSpacing(7)
            for point in points:
                label = QLabel(point)
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label.setStyleSheet("color: #29424F; font-size: 12px; padding: 2px 0;")
                group_layout.addWidget(label)
            layout.addWidget(group)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def refresh(self):
        """Keep the view compatible with the main window refresh contract."""
        self.status.setText("Offline guide")