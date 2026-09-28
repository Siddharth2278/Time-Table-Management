from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from pathlib import Path
import sys

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
from app.ui.help_view import HelpView
from app.ui.settings_view import SettingsView

# Availability / Conflicts / Backup pages removed by design:
# conflicts are now shown inline as direct error messages wherever they occur.
SIDEBAR_ITEMS = [
    ("Dashboard", "Dashboard", "MAIN"),
    ("Timetable", "Timetable", "MAIN"),
    ("Teachers", "Teachers", "MANAGE"),
    ("Subjects", "Subjects", "MANAGE"),
    ("Rooms & Labs", "Rooms", "MANAGE"),
    ("Semesters", "Semesters", "MANAGE"),
    ("Time Slots", "TimeSlots", "MANAGE"),
    ("Help & Guide", "Help", "SYSTEM"),
    ("Settings", "Settings", "SYSTEM"),
]

_SHORT = {
    "Dashboard": "D",
    "Timetable": "T",
    "Teachers": "Te",
    "Subjects": "S",
    "Rooms": "R",
    "Semesters": "Se",
    "TimeSlots": "Ti",
    "Help": "H",
    "Settings": "St",
}


def logo_path() -> str:
    """Resolve assets/logo.svg in dev and frozen (PyInstaller) layouts."""
    candidates = []
    try:
        base = getattr(sys, "_MEIPASS", None)
        if base:
            candidates.append(Path(base) / "assets" / "logo.svg")
    except Exception:
        pass
    candidates.append(Path(__file__).resolve().parents[2] / "assets" / "logo.svg")
    candidates.append(Path.cwd() / "assets" / "logo.svg")
    for p in candidates:
        try:
            if p.exists():
                return str(p)
        except Exception:
            continue
    return ""


class AnimatedLogo(QLabel):
    """App logo with a soft pulsing glow so the brand feels alive."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        pm = QPixmap(logo_path())
        if not pm.isNull():
            self.setPixmap(pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Fallback institutional badge if the SVG cannot load
            self.setText("C")
            self.setStyleSheet(
                "color: #FFFFFF; font-size: 17px; font-weight: 700; font-family: 'Playfair Display', Georgia, serif; "
                "background: #1C355E; "
                "border-radius: 2px;"
            )


class Sidebar(QFrame):
    def __init__(self, on_select):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(248)
        self.setMinimumWidth(248)
        self.on_select = on_select
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(1)

        # Logo row: animated SVG mark + brand text
        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(6, 2, 4, 2)
        logo_row.setSpacing(10)
        self.logo_icon = AnimatedLogo(40)
        logo_row.addWidget(self.logo_icon)
        self.brand_box = QWidget()
        self.brand_box.setStyleSheet("background: transparent; border: none;")
        brand_layout = QVBoxLayout(self.brand_box)
        brand_layout.setContentsMargins(0, 2, 0, 2)
        brand_layout.setSpacing(1)
        self.brand = QLabel("College Timetable")
        self.brand.setObjectName("SidebarBrand")
        brand_layout.addWidget(self.brand)
        self.brand_sub = QLabel("Manager  \u2022  Offline")
        self.brand_sub.setObjectName("SidebarSub")
        brand_layout.addWidget(self.brand_sub)
        logo_row.addWidget(self.brand_box, 1)
        layout.addLayout(logo_row)

        self.buttons = {}
        self._labels = {key: label for label, key, _ in SIDEBAR_ITEMS}
        last_section = None
        for label, key, section in SIDEBAR_ITEMS:
            if section != last_section:
                sec = QLabel(section)
                sec.setObjectName("SidebarSection")
                layout.addWidget(sec)
                last_section = section
            btn = QPushButton(f"{label}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.select(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch()
        self.foot = QLabel("Offline \u2022 SQLite\nv1.0.0")
        self.foot.setObjectName("SidebarFoot")
        layout.addWidget(self.foot)

    def set_compact(self, compact: bool):
        if compact:
            self.setFixedWidth(72)
            self.setMinimumWidth(72)
            self.brand_box.hide()
            for key, btn in self.buttons.items():
                btn.setText(_SHORT.get(key, "•"))
                btn.setToolTip(self._labels.get(key, key))
            # hide section headers in compact mode
            for i in range(self.layout().count()):
                w = self.layout().itemAt(i).widget()
                if isinstance(w, QLabel) and w.objectName() == "SidebarSection":
                    w.hide()
            self.foot.hide()
        else:
            self.setFixedWidth(248)
            self.setMinimumWidth(248)
            self.brand_box.show()
            for key, btn in self.buttons.items():
                btn.setText(f"{_ICONS.get(key, '')}   {self._labels.get(key, key)}")
                btn.setToolTip("")
            for i in range(self.layout().count()):
                w = self.layout().itemAt(i).widget()
                if isinstance(w, QLabel) and w.objectName() == "SidebarSection":
                    w.show()
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
    def __init__(self, toggle_callback=None, export_callback=None):
        super().__init__()
        self.setObjectName("Header")
        self.setFixedHeight(62)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        if toggle_callback:
            self.toggle_btn = QPushButton("\u2630")
            self.toggle_btn.setObjectName("IconButton")
            self.toggle_btn.setFixedSize(44, 44)
            self.toggle_btn.setToolTip("Collapse / expand sidebar")
            self.toggle_btn.clicked.connect(toggle_callback)
            layout.addWidget(self.toggle_btn)
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("College Timetable Manager")
        self.title_label.setObjectName("HeaderTitle")
        self.sub_label = QLabel("Department: Computer Science  \u2022  Academic Year: 2026\u201327")
        self.sub_label.setObjectName("HeaderSub")
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.sub_label)
        layout.addLayout(text_col)
        layout.addStretch()
        self.status = QLabel("\u25cf Offline Ready")
        self.status.setObjectName("StatusPill")
        layout.addWidget(self.status)
        if export_callback:
            self.export_btn = QPushButton("Export PDF")
            self.export_btn.setObjectName("PrimaryButton")
            self.export_btn.setToolTip("Export current timetable to PDF")
            self.export_btn.clicked.connect(export_callback)
            layout.addWidget(self.export_btn)

    def refresh(self):
        session = get_session()
        try:
            def get(k, d=""):
                s = session.query(Setting).filter(Setting.key == k).first()
                return s.value if s else d
            college = get("college_name", "College Timetable Manager")
            dept = get("department", "Computer Science")
            year = get("academic_year", "2026-27")
            self.title_label.setText(college)
            self.sub_label.setText(f"Department: {dept}  \u2022  Academic Year: {year}")
        finally:
            session.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("College Timetable Manager")
        self.resize(1280, 780)
        self.setMinimumSize(960, 620)
        try:
            icon_file = logo_path()
            if icon_file:
                self.setWindowIcon(QIcon(icon_file))
        except Exception:
            pass
        init_db()
        central = QWidget()
        central.setObjectName("AppRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.header = Header(toggle_callback=self.toggle_sidebar, export_callback=self.export_current_pdf)
        root.addWidget(self.header)
        self.accent = QFrame()
        self.accent.setFixedHeight(3)
        self.accent.setStyleSheet("background: #1C355E; border: none;")
        root.addWidget(self.accent)
        body = QWidget()
        body.setObjectName("ContentArea")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        self.sidebar = Sidebar(self.on_navigate)
        self.sidebar_expanded = True
        body_layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")
        body_layout.addWidget(self.stack, 1)
        root.addWidget(body, 1)

        self.dashboard = DashboardView()
        self.timetable = TimetableView()
        self.teachers = TeacherView()
        self.subjects = SubjectView()
        self.rooms = RoomView()
        self.semesters = SemesterView()
        self.timeslots = TimeSlotView()
        self.settings = SettingsView()

        mapping = {
            "Dashboard": self.dashboard,
            "Timetable": self.timetable,
            "Teachers": self.teachers,
            "Subjects": self.subjects,
            "Rooms": self.rooms,
            "Semesters": self.semesters,
            "TimeSlots": self.timeslots,
            "Help": HelpView(),
            "Settings": self.settings,
        }
        self.key_to_index = {}
        self.views = {}
        for key, view in mapping.items():
            idx = self.stack.addWidget(self._wrap_page(view))
            self.key_to_index[key] = idx
            self.views[key] = view

        self.semesters.openTimetable.connect(self.open_timetable_for_semester)
        self.settings.themeChanged.connect(lambda t: self.apply_theme())

        self.apply_theme()
        self.sidebar.set_active("Dashboard")
        self.stack.setCurrentIndex(self.key_to_index["Dashboard"])
        self.header.refresh()
        self.dashboard.refresh()

    @staticmethod
    def _wrap_page(view: QWidget) -> QScrollArea:
        """Keep each page isolated and scrollable at smaller window sizes."""
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setAttribute(Qt.WA_OpaquePaintEvent, True)
        scroll.setAutoFillBackground(True)
        scroll.setWidget(view)
        return scroll

    def on_navigate(self, key):
        idx = self.key_to_index.get(key)
        if idx is not None:
            # Belt and suspenders: exactly one page visible, no ghost compositing
            for k, i in self.key_to_index.items():
                w = self.stack.widget(i)
                try:
                    if i == idx:
                        w.show()
                    else:
                        w.hide()
                        v = self.views.get(k)
                        if v is not None:
                            try:
                                v.setGraphicsEffect(None)
                            except Exception:
                                pass
                except Exception:
                    pass
            self.stack.setCurrentIndex(idx)
            view = self.views.get(key)
            if view and hasattr(view, "refresh"):
                try:
                    view.refresh()
                except Exception as e:
                    print(f"Refresh error for {key}: {e}")
            if key != "Settings":
                self.header.refresh()
        self.sidebar.set_active(key)

    def open_timetable_for_semester(self, semester_id: int):
        self.sidebar.set_active("Timetable")
        self.stack.setCurrentIndex(self.key_to_index["Timetable"])
        idx = self.timetable.sem_combo.findData(semester_id)
        if idx >= 0:
            self.timetable.sem_combo.setCurrentIndex(idx)
        else:
            self.timetable.refresh()
            idx = self.timetable.sem_combo.findData(semester_id)
            if idx >= 0:
                self.timetable.sem_combo.setCurrentIndex(idx)
        self.timetable.load_timetable()
        self.header.refresh()

    def apply_theme(self):
        session = get_session()
        try:
            s = session.query(Setting).filter(Setting.key == "theme").first()
            theme = s.value if s and s.value in ("light", "dark") else "light"
        except Exception:
            theme = "light"
        finally:
            try:
                session.close()
            except Exception:
                pass
        self.setStyleSheet(get_theme_qss(theme))
        if hasattr(self, "timetable"):
            self.timetable.grid.set_theme(theme == "dark")

    def toggle_sidebar(self):
        self.sidebar_expanded = not getattr(self, 'sidebar_expanded', True)
        self.sidebar.set_compact(not self.sidebar_expanded)

    def export_current_pdf(self):
        # Global Publish: go to Timetable and export current semester
        try:
            self.on_navigate("Timetable")
            self.timetable.export("pdf")
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Mobile-representative: auto-compact sidebar on narrow widths
        try:
            narrow = self.width() < 900
            if narrow != (not self.sidebar_expanded):
                self.sidebar_expanded = not narrow
                self.sidebar.set_compact(narrow)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_theme()
        self.header.refresh()
