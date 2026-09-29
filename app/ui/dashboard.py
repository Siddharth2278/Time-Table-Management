from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QProgressBar, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal
from app.database import get_session
from app.models import Teacher, Subject, Room, TimetableEntry, Semester
from app.services.conflict_service import ConflictService
from app.ui.icons import icon
from app.ui.widgets import page_header


class StatCard(QFrame):
    """Metric card: tinted SVG icon square + mono value + label. Real values only."""

    def __init__(self, title, value, icon_name, badge, icon_color):
        super().__init__()
        self.setObjectName("StatCard")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)
        badge_label = QLabel()
        badge_label.setObjectName(badge)
        badge_label.setFixedSize(48, 48)
        badge_label.setAlignment(Qt.AlignCenter)
        badge_label.setPixmap(icon(icon_name, icon_color, 22).pixmap(22, 22))
        outer.addWidget(badge_label)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        self.val_label = QLabel(str(value))
        self.val_label.setObjectName("StatValue")
        col.addWidget(self.val_label)
        name_label = QLabel(title)
        name_label.setObjectName("StatLabel")
        col.addWidget(name_label)
        outer.addLayout(col, 1)


class DashboardView(QWidget):
    action_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(22, 18, 22, 18)
        self.main_layout.setSpacing(14)
        self.main_layout.addWidget(page_header(
            "Dashboard", "Timetable health, recent scheduling activity and shortcuts."))

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        self.stats_grid.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addLayout(self.stats_grid)

        mid = QHBoxLayout()
        mid.setSpacing(12)
        # Completion card
        self.comp_card = QFrame()
        self.comp_card.setObjectName("Card")
        comp_layout = QVBoxLayout(self.comp_card)
        comp_layout.setContentsMargins(20, 16, 20, 16)
        comp_layout.setSpacing(10)
        comp_title = QLabel("Semester Completion")
        comp_title.setObjectName("SectionTitle")
        comp_layout.addWidget(comp_title)
        self.comp_body = QVBoxLayout()
        self.comp_body.setSpacing(10)
        comp_layout.addLayout(self.comp_body)
        mid.addWidget(self.comp_card, 2)
        # Quick actions card
        self.quick_card = QFrame()
        self.quick_card.setObjectName("Card")
        quick_layout = QVBoxLayout(self.quick_card)
        quick_layout.setContentsMargins(20, 16, 20, 16)
        quick_layout.setSpacing(8)
        quick_title = QLabel("Quick Actions")
        quick_title.setObjectName("SectionTitle")
        quick_layout.addWidget(quick_title)
        for label, key in [
            ("Open Timetable", "timetable"),
            ("Add Teacher", "add_teacher"),
            ("Add Subject", "add_subject"),
            ("Add Room / Lab", "add_room"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.action_requested.emit(k))
            quick_layout.addWidget(btn)
        quick_layout.addStretch()
        mid.addWidget(self.quick_card, 1)
        self.main_layout.addLayout(mid)

        # Schedule health banner (real conflict summary, clean empty state).
        self.health_label = QLabel("")
        self.health_label.setWordWrap(True)
        self.main_layout.addWidget(self.health_label)
        self.main_layout.addStretch()

    def refresh(self):
        for layout in (self.stats_grid, self.comp_body):
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
        session = get_session()
        try:
            total_teachers = session.query(Teacher).count()
            total_subjects = session.query(Subject).count()
            total_rooms = session.query(Room).count()
            sems = session.query(Semester).order_by(Semester.id).all()
            cards = [
                ("Total Teachers", total_teachers, "users", "BadgeIndigo", "#5B8CFF"),
                ("Total Subjects", total_subjects, "book", "BadgeGreen", "#22B07D"),
                ("Rooms & Labs", total_rooms, "building", "BadgeAmber", "#D99A26"),
                ("Active Semesters", len(sems), "layers", "BadgeRose", "#E05D52"),
            ]
            for idx, (title, val, ic, badge, color) in enumerate(cards):
                self.stats_grid.addWidget(StatCard(title, val, ic, badge, color), 0, idx)
                self.stats_grid.setColumnStretch(idx, 1)
            if not sems:
                empty = QLabel("No semesters yet. Add semesters and subjects to track completion.")
                empty.setObjectName("EmptyState")
                self.comp_body.addWidget(empty)
            for sem in sems:
                comp = ConflictService.calculate_timetable_completion(session, sem.id)
                row = QHBoxLayout()
                row.setSpacing(10)
                name = QLabel(sem.name)
                name.setMinimumWidth(120)
                name.setObjectName("Muted")
                bar = QProgressBar()
                bar.setMaximum(100)
                bar.setValue(int(comp["completion_pct"]))
                bar.setFormat(f"{comp['scheduled']}/{comp['required']}  {comp['completion_pct']}%")
                pct = QLabel(f"{comp['completion_pct']}%")
                pct.setMinimumWidth(48)
                pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                pct.setObjectName("Mono")
                row.addWidget(name)
                row.addWidget(bar, 1)
                row.addWidget(pct)
                holder = QWidget()
                holder.setStyleSheet("background: transparent; border: none;")
                holder.setLayout(row)
                self.comp_body.addWidget(holder)
            conflicts = ConflictService.detect_all_conflicts(session)
            if conflicts:
                first = conflicts[0].get("message", "")
                extra = f" (+{len(conflicts) - 1} more)" if len(conflicts) > 1 else ""
                self.health_label.setText(
                    f"{len(conflicts)} conflict(s) detected. Fix them in Timetable — errors appear directly when you save.\n{first}{extra}"
                )
                self.health_label.setObjectName("BannerErr")
            else:
                total_lectures = session.query(TimetableEntry).count()
                if total_lectures == 0:
                    self.health_label.setText("No lectures scheduled yet. Open Timetable and assign your first class.")
                else:
                    self.health_label.setText(
                        "Schedule is clean. No teacher, semester or room overlaps detected.")
                self.health_label.setObjectName("BannerOk")
            # Re-apply object-name stylesheet after change.
            try:
                self.style().unpolish(self.health_label)
                self.style().polish(self.health_label)
            except Exception:
                pass
        finally:
            session.close()
