from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from app.database import get_session
from app.models import Teacher, Subject, Room, TimetableEntry, Semester
from app.services.conflict_service import ConflictService


class StatCard(QFrame):
    """Web-style metric card: muted icon square plus mono value."""

    ICON_BG = ("#E0E7FF", "#D1FAE5", "#FEF3C7", "#FCE7F3")
    ICON_FG = ("#1C355E", "#065F46", "#92400E", "#9A2C2C")
    ICON_TXT = ("T", "S", "R", "Se")

    def __init__(self, title, value, icon_index: int = 0):
        super().__init__()
        self.setObjectName("StatCard")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)
        icon = QLabel(self.ICON_TXT[icon_index % len(self.ICON_TXT)])
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"background: {self.ICON_BG[icon_index % len(self.ICON_BG)]};"
            f"color: {self.ICON_FG[icon_index % len(self.ICON_FG)]};"
            "font-size: 18px; font-weight: 700; border: none; border-radius: 2px;"
        )
        outer.addWidget(icon)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        self.val_label = QLabel("0")
        self.val_label.setObjectName("StatValue")
        col.addWidget(self.val_label)
        title_label = QLabel(title)
        title_label.setObjectName("StatLabel")
        col.addWidget(title_label)
        outer.addLayout(col, 1)
        self.setMinimumHeight(92)
        self.setMinimumWidth(150)
        self._target = value

    def play(self, delay: int = 0):
        from app.ui.animations import count_up
        count_up(self.val_label, self._target, delay=delay)


class DashboardView(QWidget):
    navigate = Signal(str)

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(22, 18, 22, 18)
        self.main_layout.setSpacing(12)
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        self.main_layout.addWidget(title)
        sub = QLabel("Timetable health, recent scheduling activity and shortcuts.")
        sub.setObjectName("PageSubtitle")
        self.main_layout.addWidget(sub)

        self.stats_container = QWidget()
        self.stats_container.setStyleSheet("background: transparent; border: none;")
        self.stats_layout = QGridLayout(self.stats_container)
        self.stats_layout.setSpacing(12)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.stats_container)

        row = QHBoxLayout()
        row.setSpacing(12)
        self.recent_card = QFrame()
        self.recent_card.setObjectName("ContentCard")
        recent_outer = QVBoxLayout(self.recent_card)
        recent_outer.setContentsMargins(16, 16, 16, 16)
        recent_outer.setSpacing(8)
        recent_title = QLabel("Recent Activity")
        recent_title.setObjectName("SectionTitle")
        recent_outer.addWidget(recent_title)
        self.recent_body = QVBoxLayout()
        self.recent_body.setSpacing(6)
        recent_outer.addLayout(self.recent_body)
        row.addWidget(self.recent_card, 2)

        links_card = QFrame()
        links_card.setObjectName("ContentCard")
        links_outer = QVBoxLayout(links_card)
        links_outer.setContentsMargins(16, 16, 16, 16)
        links_outer.setSpacing(8)
        links_title = QLabel("Quick Links")
        links_title.setObjectName("SectionTitle")
        links_outer.addWidget(links_title)
        for label, key in [
            ("Open Timetable", "Timetable"),
            ("Add Teacher", "Teachers"),
            ("Add Subject", "Subjects"),
            ("Settings", "Settings"),
        ]:
            btn = QPushButton(f"{label}  \u2192")
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.navigate.emit(k))
            links_outer.addWidget(btn)
        links_outer.addStretch()
        row.addWidget(links_card, 1)
        self.main_layout.addLayout(row)

        self.health_label = QLabel("")
        self.health_label.setWordWrap(True)
        self.main_layout.addWidget(self.health_label)
        self.main_layout.addStretch()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def refresh(self):
        self._clear_layout(self.stats_layout)
        self._clear_layout(self.recent_body)
        session = get_session()
        try:
            total_teachers = session.query(Teacher).count()
            total_subjects = session.query(Subject).count()
            total_rooms = session.query(Room).count()
            total_sems = session.query(Semester).count()
            cards = [
                ("Total Teachers", total_teachers),
                ("Total Subjects", total_subjects),
                ("Rooms", total_rooms),
                ("Active Semesters", total_sems),
            ]
            made = []
            for idx, (title, val) in enumerate(cards):
                card = StatCard(title, val, icon_index=idx)
                self.stats_layout.addWidget(card, 0, idx)
                made.append(card)
            for i, card in enumerate(made):
                card.play(delay=40 + i * 50)

            entries = (
                session.query(TimetableEntry)
                .order_by(TimetableEntry.id.desc())
                .limit(6)
                .all()
            )
            if not entries:
                empty = QLabel(
                    "No lectures scheduled yet. Open Timetable and assign your first class."
                )
                empty.setWordWrap(True)
                empty.setObjectName("PageSubtitle")
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet(
                    "padding: 24px; border: 1px dashed #DEDCD3; border-radius: 2px;"
                )
                self.recent_body.addWidget(empty)
            else:
                for e in entries:
                    line = QHBoxLayout()
                    left = QLabel(
                        f"Sem {e.semester_id} \u2022 Day {e.day_id}  "
                        f"{e.start_time}\u2013{e.end_time}"
                    )
                    left.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-weight: 600;")
                    right = QLabel(
                        f"Sub {e.subject_id} \u2022 T{e.teacher_id} \u2022 R{e.room_id}"
                    )
                    right.setObjectName("PageSubtitle")
                    right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    wrap = QWidget()
                    wrap.setStyleSheet("background: transparent; border: none;")
                    line.addWidget(left, 1)
                    line.addWidget(right, 1)
                    wrap.setLayout(line)
                    self.recent_body.addWidget(wrap)

            conflicts = ConflictService.detect_all_conflicts(session)
            try:
                from app.models import TeacherAvailability, RoomAvailability, TimeSlot
                from app.utils.helpers import time_to_minutes as _t2m
                extra = 0
                _entries = session.query(TimetableEntry).all()
                _tas = session.query(TeacherAvailability).filter(TeacherAvailability.is_unavailable == True).all()
                _ras = session.query(RoomAvailability).filter(RoomAvailability.is_unavailable == True).all()
                _brks = session.query(TimeSlot).filter(TimeSlot.is_break == True, TimeSlot.is_enabled == True).all()

                def _ov(a, b, c, d):
                    try:
                        return _t2m(a) < _t2m(d) and _t2m(b) > _t2m(c)
                    except (ValueError, AttributeError, TypeError):
                        return False

                for e in _entries:
                    for ta in _tas:
                        if ta.teacher_id == e.teacher_id and ta.day_id == e.day_id and _ov(ta.start_time, ta.end_time, e.start_time, e.end_time):
                            extra += 1
                            break
                    for ra in _ras:
                        if ra.room_id == e.room_id and ra.day_id == e.day_id and _ov(ra.start_time, ra.end_time, e.start_time, e.end_time):
                            extra += 1
                            break
                    for b in _brks:
                        if _ov(b.start_time, b.end_time, e.start_time, e.end_time):
                            extra += 1
                            break
                total_conflicts = len(conflicts) + extra
            except Exception:
                total_conflicts = len(conflicts)
                extra = 0

            if total_conflicts:
                first = conflicts[0].get("message", "") if conflicts else "Availability/break violation detected."
                extra_txt = f" (+{total_conflicts - 1} more)" if total_conflicts > 1 else ""
                self.health_label.setText(
                    f"{total_conflicts} conflict(s) detected. Fix them in Timetable — errors appear when you save.\n{first}{extra_txt}"
                )
                self.health_label.setStyleSheet(
                    "color: #991B1B; font-weight: 600; font-size: 12.5px; background: #FEF2F2; "
                    "border: 1px solid #FECACA; border-radius: 10px; padding: 12px;"
                )
            else:
                self.health_label.setText(
                    "Schedule is clean. No teacher, semester, room, availability or break overlaps detected."
                )
                self.health_label.setStyleSheet(
                    "color: #065F46; font-weight: 600; font-size: 12.5px; background: #ECFDF5; "
                    "border: 1px solid #A7F3D0; border-radius: 10px; padding: 12px;"
                )
        finally:
            session.close()
