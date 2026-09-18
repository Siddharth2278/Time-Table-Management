from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QProgressBar, QFrame, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.database import get_session
from app.models import Teacher, Subject, Room, TimetableEntry, Semester
from app.services.conflict_service import ConflictService

class StatCard(QFrame):
    def __init__(self, title, value, color="#2F5496"):
        super().__init__()
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        # Icon color bar
        top = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        top.addWidget(dot)
        top.addStretch()
        layout.addLayout(top)
        val_label = QLabel(str(value))
        val_label.setObjectName("StatValue")
        layout.addWidget(val_label)
        title_label = QLabel(title.upper())
        title_label.setObjectName("StatLabel")
        layout.addWidget(title_label)
        self.setMinimumHeight(96)
        self.setMinimumWidth(140)

class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(14)
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #1E2A3A;")
        self.main_layout.addWidget(title)
        sub = QLabel("Overview of timetable, resources and completion status")
        sub.setStyleSheet("color: #64748B; font-size: 12px;")
        self.main_layout.addWidget(sub)

        # Stats grid placeholder
        self.stats_container = QWidget()
        self.stats_layout = QGridLayout(self.stats_container)
        self.stats_layout.setSpacing(12)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.stats_container)

        # Semester completion section
        self.sem_label = QLabel("Semester Completion")
        self.sem_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E2A3A; margin-top: 6px;")
        self.main_layout.addWidget(self.sem_label)
        self.sem_container = QWidget()
        self.sem_container.setStyleSheet("background: white; border: 1px solid #E2E8F0; border-radius: 12px;")
        self.sem_layout = QVBoxLayout(self.sem_container)
        self.sem_layout.setContentsMargins(16, 16, 16, 16)
        self.sem_layout.setSpacing(12)
        self.main_layout.addWidget(self.sem_container)

        # Conflicts summary
        self.conflict_label = QLabel("")
        self.conflict_label.setWordWrap(True)
        self.main_layout.addWidget(self.conflict_label)
        self.main_layout.addStretch()

    def refresh(self):
        # Clear previous
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
            total_rooms = session.query(Room).filter(Room.type=="Classroom").count()
            total_labs = session.query(Room).filter(Room.type=="Laboratory").count()
            total_lectures = session.query(TimetableEntry).count()
            sems = session.query(Semester).order_by(Semester.id).all()
            required_total = 0
            for s in sems:
                subs = session.query(Subject).filter(Subject.semester_id==s.id).all()
                required_total += sum(x.required_lectures_per_week for x in subs)
            unscheduled = max(0, required_total - total_lectures)
            conflicts = ConflictService.detect_all_conflicts(session)
            # Stats cards
            cards = [
                ("Total Teachers", total_teachers, "#2F5496"),
                ("Total Subjects", total_subjects, "#0EA5E9"),
                ("Classrooms", total_rooms, "#10B981"),
                ("Laboratories", total_labs, "#F59E0B"),
                ("Scheduled Lectures", total_lectures, "#8B5CF6"),
                ("Unscheduled", unscheduled, "#EF4444"),
                ("Conflicts", len(conflicts), "#DC2626" if conflicts else "#10B981"),
            ]
            for idx, (title, val, color) in enumerate(cards):
                card = StatCard(title, val, color)
                self.stats_layout.addWidget(card, idx // 4, idx % 4)
            # Semester progress
            for sem in sems:
                comp = ConflictService.calculate_timetable_completion(session, sem.id)
                row = QHBoxLayout()
                name = QLabel(sem.name)
                name.setMinimumWidth(120)
                name.setStyleSheet("font-weight: 600; color: #334155;")
                bar = QProgressBar()
                bar.setMaximum(100)
                bar.setValue(int(comp["completion_pct"]))
                bar.setFormat(f"{comp['scheduled']}/{comp['required']}  {comp['completion_pct']}%")
                bar.setStyleSheet("""
                    QProgressBar { border: 1px solid #E2E8F0; border-radius: 8px; background: #F1F5F9; text-align: center; height: 18px; font-size: 11px; color: #1E2A3A; }
                    QProgressBar::chunk { background-color: #2F5496; border-radius: 7px; }
                """)
                pct_label = QLabel(f"{comp['completion_pct']}%")
                pct_label.setMinimumWidth(50)
                pct_label.setStyleSheet("font-weight: 700; color: #2F5496;")
                row.addWidget(name)
                row.addWidget(bar, 1)
                row.addWidget(pct_label)
                container = QWidget()
                container.setLayout(row)
                self.sem_layout.addWidget(container)
            if conflicts:
                self.conflict_label.setText(f"⚠ {len(conflicts)} conflict(s) detected. Please check Conflicts page.")
                self.conflict_label.setStyleSheet("color: #DC2626; font-weight: 600; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 10px;")
            else:
                self.conflict_label.setText("✓ No conflicts detected. Timetable is consistent.")
                self.conflict_label.setStyleSheet("color: #065F46; font-weight: 600; background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 10px;")
        finally:
            session.close()
