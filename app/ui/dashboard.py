from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QProgressBar, QFrame
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import Teacher, Subject, Room, TimetableEntry, Semester
from app.services.conflict_service import ConflictService


class StatCard(QFrame):
    """Web-style metric card: muted icon square plus mono value. Flow unchanged."""

    ICON_BG = ("#E0E7FF", "#D1FAE5", "#FEF3C7", "#FCE7F3", "#DBEAFE", "#F3F1EA")
    ICON_FG = ("#1C355E", "#065F46", "#92400E", "#9A2C2C", "#1C355E", "#57534E")
    ICON_TXT = ("T", "S", "C", "L", "S", "U")

    def __init__(self, title, value, gradient=None, icon_index: int = 0):
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


CARD_GRADIENTS = [
    ("#4F46E5", "#8B5CF6"),
    ("#0EA5E9", "#6366F1"),
    ("#059669", "#34D399"),
    ("#D97706", "#F59E0B"),
    ("#7C3AED", "#D946EF"),
    ("#DC2626", "#F97316"),
]


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
                for x in subs:
                    try:
                        v = int(x.required_lectures_per_week) if x.required_lectures_per_week is not None else 0
                        required_total += max(0, v)
                    except (TypeError, ValueError):
                        continue
            unscheduled = 0
            for s in sems:
                comp_s = ConflictService.calculate_timetable_completion(session, s.id)
                unscheduled += max(0, comp_s["required"] - comp_s["scheduled"])
            conflicts = ConflictService.detect_all_conflicts(session)
            # Include availability/break violations so banner is not falsely green
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
            cards = [
                ("Total Teachers", total_teachers),
                ("Total Subjects", total_subjects),
                ("Classrooms", total_rooms),
                ("Laboratories", total_labs),
                ("Scheduled Lectures", total_lectures),
                ("Unscheduled", unscheduled),
            ]
            made = []
            for idx, (title, val) in enumerate(cards):
                card = StatCard(title, val, CARD_GRADIENTS[idx % len(CARD_GRADIENTS)], icon_index=idx)
                self.stats_layout.addWidget(card, idx // 3, idx % 3)
                made.append(card)
            from app.ui.animations import stagger_in
            stagger_in(made)
            for i, card in enumerate(made):
                card.play(delay=60 + i * 70)
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
            if total_conflicts:
                # Direct message: list first few conflicts inline.
                first = conflicts[0].get("message", "") if conflicts else "Availability/break violation detected."
                extra_txt = f" (+{total_conflicts - 1} more)" if total_conflicts > 1 else ""
                self.health_label.setText(
                    f"{total_conflicts} conflict(s) detected ({len(conflicts)} scheduling + {extra} availability/break). Fix them in Timetable \u2014 errors appear directly when you save.\n{first}{extra_txt}"
                )
                self.health_label.setStyleSheet(
                    "color: #991B1B; font-weight: 600; font-size: 12.5px; background: #FEF2F2; "
                    "border: 1px solid #FECACA; border-radius: 10px; padding: 12px;"
                )
            else:
                self.health_label.setText("Schedule is clean. No teacher, semester, room, availability or break overlaps detected.")
                self.health_label.setStyleSheet(
                    "color: #065F46; font-weight: 600; font-size: 12.5px; background: #ECFDF5; "
                    "border: 1px solid #A7F3D0; border-radius: 10px; padding: 12px;"
                )
        finally:
            session.close()
