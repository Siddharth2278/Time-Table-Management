from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from app.database import get_session, init_db
from app.models import Setting
from app.ui.styles import get_theme_qss
from app.ui.dashboard import DashboardView
from app.ui.timetable_view import TimetableView
from app.ui.teacher_view import TeacherView
from app.ui.subject_view import SubjectView
from app.ui.room_view import RoomView
from app.ui.semester_view import SemesterView
from app.ui.timeslot_view import TimeSlotView
from app.ui.availability_view import AvailabilityView
from app.ui.conflict_view import ConflictView
from app.ui.backup_view import BackupView
from app.ui.help_view import HelpView
from app.ui.settings_view import SettingsView

SIDEBAR_ITEMS = [
    ("Dashboard", "Dashboard"),
    ("Timetable", "Timetable"),
    ("Teachers", "Teachers"),
    ("Subjects", "Subjects"),
    ("Rooms & Labs", "Rooms"),
    ("Semesters", "Semesters"),
    ("Time Slots", "TimeSlots"),
    ("Availability", "Availability"),
    ("Conflicts", "Conflicts"),
    ("Backup & Restore", "Backup"),
    ("Help & How to Use", "Help"),
    ("Settings", "Settings"),
]

class Sidebar(QFrame):
    def __init__(self, on_select):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(176)
        self.on_select = on_select
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(2)
        # Logo/title - compact
        self.logo = QLabel("College Timetable")
        self.logo.setStyleSheet("color: white; font-size: 13px; font-weight: 800; padding: 4px 6px 8px 6px;")
        self.logo.setWordWrap(True)
        layout.addWidget(self.logo)
        self.buttons = {}
        self._icons = {
            "Dashboard": "▦",
            "Timetable": "▤",
            "Teachers": "👤",
            "Subjects": "📚",
            "Rooms": "🏫",
            "Semesters": "🎓",
            "TimeSlots": "⏰",
            "Availability": "◷",
            "Conflicts": "⚠",
            "Backup": "▣",
            "Help": "?",
            "Settings": "⚙",
        }
        self._labels = {key: label for label, key in SIDEBAR_ITEMS}
        for label, key in SIDEBAR_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.select(k))
            btn.setText(self._icons.get(key, "") + "  " + label)
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch()
        self.foot = QLabel("Offline • SQLite\nv1.0.0")
        self.foot.setStyleSheet("color: #64748B; font-size: 10px; padding: 10px;")
        layout.addWidget(self.foot)

    def set_compact(self, compact: bool):
        if compact:
            self.setFixedWidth(52)
            self.logo.setText("CT")
            self.logo.setStyleSheet("color: white; font-size: 16px; font-weight: 900; padding: 6px; text-align: center;")
            for key, btn in self.buttons.items():
                btn.setText(self._icons.get(key, "•"))
                btn.setToolTip(self._labels.get(key, key))
                btn.setStyleSheet("text-align: center; padding: 8px 4px;")
            self.foot.hide()
        else:
            self.setFixedWidth(176)
            self.logo.setText("College Timetable")
            self.logo.setStyleSheet("color: white; font-size: 13px; font-weight: 800; padding: 4px 6px 8px 6px;")
            for key, btn in self.buttons.items():
                btn.setText(self._icons.get(key, "") + "  " + self._labels.get(key, key))
                btn.setToolTip("")
                btn.setStyleSheet("")
            self.foot.show()

    def select(self, key):
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        if self.on_select:
            self.on_select(key)

    def set_active(self, key):
        for k, b in self.buttons.items():
            b.setChecked(k == key)

class Header(QFrame):
    def __init__(self, toggle_callback=None):
        super().__init__()
        self.setObjectName("Header")
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        # Collapse button — reduces left bars
        if toggle_callback:
            self.toggle_btn = QPushButton("☰")
            self.toggle_btn.setFixedSize(30, 30)
            self.toggle_btn.setStyleSheet("QPushButton { background: #EEF2F7; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 14px; } QPushButton:hover { background: #E2E8F0; }")
            self.toggle_btn.setToolTip("Toggle sidebar (less bars)")
            self.toggle_btn.clicked.connect(toggle_callback)
            layout.addWidget(self.toggle_btn)
        self.title_label = QLabel("College Timetable Manager")
        self.title_label.setObjectName("HeaderTitle")
        layout.addWidget(self.title_label)
        self.sub_label = QLabel("Department: Computer Science  •  Academic Year: 2026–27")
        self.sub_label.setObjectName("HeaderSub")
        layout.addWidget(self.sub_label)
        layout.addStretch()
        # Status
        self.status = QLabel("● Offline Ready")
        self.status.setStyleSheet("color: #10B981; font-weight: 600; font-size: 11px; background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 12px; padding: 4px 10px;")
        layout.addWidget(self.status)

    def refresh(self):
        session = get_session()
        try:
            def get(k, d=""):
                s = session.query(Setting).filter(Setting.key==k).first()
                return s.value if s else d
            college = get("college_name", "College Timetable Manager")
            dept = get("department", "Computer Science")
            year = get("academic_year", "2026-27")
            self.title_label.setText(college)
            self.sub_label.setText(f"Department: {dept}  •  Academic Year: {year}")
        finally:
            session.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("College Timetable Manager")
        self.resize(1240, 760)
        self.setMinimumSize(1100, 650)
        # Ensure DB init
        init_db()
        # Theme will be applied after UI creation
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        # Header with toggle
        self.header = Header(toggle_callback=self.toggle_sidebar)
        root.addWidget(self.header)
        # Body: sidebar + stack
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        # Sidebar
        self.sidebar = Sidebar(self.on_navigate)
        self.sidebar_expanded = True
        body_layout.addWidget(self.sidebar)
        # Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: #F2F4F8;")
        body_layout.addWidget(self.stack, 1)
        root.addWidget(body, 1)

        # Create views
        self.views = {}
        self.dashboard = DashboardView()
        self.timetable = TimetableView()
        self.teachers = TeacherView()
        self.subjects = SubjectView()
        self.rooms = RoomView()
        self.semesters = SemesterView()
        self.timeslots = TimeSlotView()
        self.availability = AvailabilityView()
        self.conflicts = ConflictView()
        self.backup = BackupView()
        self.settings = SettingsView()

        mapping = {
            "Dashboard": self.dashboard,
            "Timetable": self.timetable,
            "Teachers": self.teachers,
            "Subjects": self.subjects,
            "Rooms": self.rooms,
            "Semesters": self.semesters,
            "TimeSlots": self.timeslots,
            "Availability": self.availability,
            "Conflicts": self.conflicts,
            "Backup": self.backup,
            "Help": HelpView(),
            "Settings": self.settings,
        }
        self.key_to_index = {}
        for key, view in mapping.items():
            idx = self.stack.addWidget(view)
            self.key_to_index[key] = idx
            self.views[key] = view

        # Connect semester overview to timetable
        self.semesters.openTimetable.connect(self.open_timetable_for_semester)
        # Theme change
        self.settings.themeChanged.connect(lambda t: self.apply_theme())

        # Apply theme now that stack exists
        self.apply_theme()
        # Default
        self.sidebar.set_active("Dashboard")
        self.stack.setCurrentIndex(self.key_to_index["Dashboard"])
        self.header.refresh()
        self.dashboard.refresh()

    def on_navigate(self, key):
        idx = self.key_to_index.get(key)
        if idx is not None:
            self.stack.setCurrentIndex(idx)
            view = self.views.get(key)
            if view and hasattr(view, "refresh"):
                try:
                    view.refresh()
                except Exception as e:
                    print(f"Refresh error for {key}: {e}")
            # Header may need refresh if settings changed
            if key != "Settings":
                self.header.refresh()
            else:
                # When leaving settings, refresh header
                pass
        # Update sidebar active
        self.sidebar.set_active(key)

    def open_timetable_for_semester(self, semester_id: int):
        # Switch to timetable and set semester
        self.sidebar.set_active("Timetable")
        self.stack.setCurrentIndex(self.key_to_index["Timetable"])
        # Set combo
        # Find index for semester_id
        idx = self.timetable.sem_combo.findData(semester_id)
        if idx >= 0:
            self.timetable.sem_combo.setCurrentIndex(idx)
        else:
            # If not found, refresh first
            self.timetable.refresh()
            idx = self.timetable.sem_combo.findData(semester_id)
            if idx >= 0:
                self.timetable.sem_combo.setCurrentIndex(idx)
        self.timetable.load_timetable()
        # Refresh header
        self.header.refresh()

    def apply_theme(self):
        session = get_session()
        try:
            s = session.query(Setting).filter(Setting.key=="theme").first()
            theme = s.value if s and s.value in ("light", "dark") else "light"
        except:
            theme = "light"
        finally:
            try:
                session.close()
            except:
                pass
        self.setStyleSheet(get_theme_qss(theme))
        # Also update stack background for light/dark (guard for early call)
        if hasattr(self, 'stack'):
            if theme == "dark":
                self.stack.setStyleSheet("background: #0F172A;")
            else:
                self.stack.setStyleSheet("background: #E6EAF0;")

    def toggle_sidebar(self):
        self.sidebar_expanded = not getattr(self, 'sidebar_expanded', True)
        # Compact = less left bars — icon-only 52px vs 176px
        self.sidebar.set_compact(not self.sidebar_expanded)

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure initial data loaded
        self.apply_theme()
        self.header.refresh()
