from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QProgressBar, QFrame
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import Teacher, Subject, Room, TimetableEntry, Semester
from app.services.conflict_service import ConflictService


class StatCard(QFrame):
    def __init__(self, title, value, accent="#4F46E5"):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        dot = QLabel("\u25cf")
        dot.setStyleSheet(f"color: {accent}; font-size: 14px; background: transparent; border: none;")
        top.addWidget(dot)
        top.addStretch()
        layout.addLayout(top)
        val_label = QLabel(str(value))
        val_label.setObjectName("StatValue")
        layout.addWidget(val_label)
        title_label = QLabel(title.upper())
        title_label.setObjectName("StatLabel")
        layout.addWidget(title_label)
        self.setMinimumHeight(104)
        self.setMinimumWidth(150)
        # Accent top border via stylesheet addition (kept subtle, theme-safe)
        self.setStyleSheet(self.styleSheet() + f" QFrame#Card {{ border-top: 3px solid {accent}; }}")


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(22, 18, 22, 18)
        self.main_layout.setSpacing(12)
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        self.main_layout.addWidget(title)
        sub = QLabel("Overview of timetable, resources and completion status")
        sub.setObjectName("PageSubtitle")
        self.main_layout.addWidget(sub)

        self.stats_container = QWidget()
        self.stats_container.setStyleSheet("background: transparent; border: none;")
        self.stats_layout = QGridLayout(self.stats_container)
        self.stats_layout.setSpacing(12)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.stats_container)

        self.sem_label = QLabel("Semester Completion")
        self.sem_label.setObjectName("SectionTitle")
        self.main_layout.addWidget(self.sem_label)
        self.sem_container = QFrame()
        self.sem_container.setObjectName("ContentCard")
        self.sem_layout = QVBoxLayout(self.sem_container)
        self.sem_layout.setContentsMargins(16, 16, 16, 16)
        self.sem_layout.setSpacing(12)
        self.main_layout.addWidget(self.sem_container)

        # Inline schedule-health banner: conflicts are reported HERE directly,
        # no separate Conflicts page.
        self.health_label = QLabel("")
        self.health_label.setWordWrap(True)
        self.main_layout.addWidget(self.health_label)
        self.main_layout.addStretch()

    def refresh(self):
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        while self.sem_layout.count():
            item = self.sem_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        session = get_session()
        try:
            total_teachers = session.query(Teacher).count()
            total_subjects = session.query(Subject).count()
            total_rooms = session.query(Room).filter(Room.type == "Classroom").count()
            total_labs = session.query(Room).filter(Room.type == "Laboratory").count()
            total_lectures = session.query(TimetableEntry).count()
            sems = session.query(Semester).order_by(Semester.id).all()
            required_total = 0
            for s in sems:
                subs = session.query(Subject).filter(Subject.semester_id == s.id).all()
                required_total += sum(x.required_lectures_per_week for x in subs)
            unscheduled = max(0, required_total - total_lectures)
            conflicts = ConflictService.detect_all_conflicts(session)
            cards = [
                ("Total Teachers", total_teachers, "#4F46E5"),
                ("Total Subjects", total_subjects, "#0EA5E9"),
                ("Classrooms", total_rooms, "#059669"),
                ("Laboratories", total_labs, "#D97706"),
                ("Scheduled Lectures", total_lectures, "#7C3AED"),
                ("Unscheduled", unscheduled, "#DC2626" if unscheduled else "#059669"),
            ]
            for idx, (title, val, color) in enumerate(cards):
                card = StatCard(title, val, color)
                self.stats_layout.addWidget(card, idx // 3, idx % 3)
            for sem in sems:
                comp = ConflictService.calculate_timetable_completion(session, sem.id)
                row = QHBoxLayout()
                row.setSpacing(10)
                name = QLabel(sem.name)
                name.setMinimumWidth(130)
                name.setStyleSheet("font-weight: 700; font-size: 13px; background: transparent; border: none;")
                bar = QProgressBar()
                bar.setMaximum(100)
                bar.setValue(int(comp["completion_pct"]))
                bar.setFormat(f"{comp['scheduled']}/{comp['required']}  {comp['completion_pct']}%")
                pct_label = QLabel(f"{comp['completion_pct']}%")
                pct_label.setMinimumWidth(52)
                pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                pct_label.setStyleSheet("font-weight: 800; font-size: 13px; background: transparent; border: none;")
                row.addWidget(name)
                row.addWidget(bar, 1)
                row.addWidget(pct_label)
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container.setLayout(row)
                self.sem_layout.addWidget(container)
            if conflicts:
                # Direct message: list first few conflicts inline.
                first = conflicts[0].get("message", "") if conflicts else ""
                extra = f" (+{len(conflicts) - 1} more)" if len(conflicts) > 1 else ""
                self.health_label.setText(
                    f"\u26a0 {len(conflicts)} scheduling conflict(s) detected. Fix them in Timetable \u2014 errors appear directly when you save.\n{first}{extra}"
                )
                self.health_label.setStyleSheet(
                    "color: #991B1B; font-weight: 600; font-size: 12.5px; background: #FEF2F2; "
                    "border: 1px solid #FECACA; border-radius: 10px; padding: 12px;"
                )
            else:
                self.health_label.setText("\u2713 Schedule is clean. No teacher, semester or room overlaps detected.")
                self.health_label.setStyleSheet(
                    "color: #065F46; font-weight: 600; font-size: 12.5px; background: #ECFDF5; "
                    "border: 1px solid #A7F3D0; border-radius: 10px; padding: 12px;"
                )
        finally:
            session.close()
