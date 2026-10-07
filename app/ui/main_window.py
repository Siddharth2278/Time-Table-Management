from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget,
    QFrame, QScrollArea, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from pathlib import Path
import sys

from app.database import get_session, init_db
from app.models import Setting
from app.ui.styles import get_theme_qss
from app.ui.icons import icon, nav_icon
from app.ui.widgets import set_switch_theme
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
# conflicts are shown inline as direct messages wherever they occur.
SIDEBAR_ITEMS = [
    ("Dashboard", "Dashboard", "MAIN", "dashboard"),
    ("Timetable Builder", "Timetable", "MAIN", "calendar"),
    ("Teachers", "Teachers", "MANAGE", "users"),
    ("Subjects", "Subjects", "MANAGE", "book"),
    ("Rooms & Labs", "Rooms", "MANAGE", "building"),
    ("Semesters", "Semesters", "MANAGE", "layers"),
    ("Time Slots", "TimeSlots", "MANAGE", "clock"),
    ("Help & Guide", "Help", "SYSTEM", "help"),
    ("Settings", "Settings", "SYSTEM", "sliders"),
]

WIDTH_OPEN = 232
WIDTH_SHUT = 68


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


class BrandMark(QLabel):
    """App logo mark; falls back to a styled letter badge."""

    def __init__(self, size: int = 36, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        pm = QPixmap(logo_path())
        if not pm.isNull():
            self.setPixmap(pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText("C")
            self.setStyleSheet(
                "color: #FFFFFF; font-size: 17px; font-weight: 700; "
                "background: #5B8CFF; border-radius: 8px;"
            )


class Sidebar(QFrame):
    def __init__(self, on_select):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(WIDTH_OPEN)
        self.setMinimumWidth(WIDTH_OPEN)
        self.on_select = on_select
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(1)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(14, 2, 10, 2)
        brand_row.setSpacing(10)
        self.brand_mark = BrandMark(36)
        brand_row.addWidget(self.brand_mark)
        self.brand_box = QWidget()
        self.brand_box.setStyleSheet("background: transparent; border: none;")
        brand_layout = QVBoxLayout(self.brand_box)
        brand_layout.setContentsMargins(0, 2, 0, 2)
        brand_layout.setSpacing(1)
        self.brand = QLabel("College Timetable")
        self.brand.setObjectName("SidebarBrand")
        brand_layout.addWidget(self.brand)
        self.brand_sub = QLabel("MANAGER  •  OFFLINE")
        self.brand_sub.setObjectName("SidebarSub")
        brand_layout.addWidget(self.brand_sub)
        brand_row.addWidget(self.brand_box, 1)
        layout.addLayout(brand_row)

        self.buttons = {}
        self._labels = {key: label for label, key, _, _ in SIDEBAR_ITEMS}
        self._icons = {key: icon_name for _, key, _, icon_name in SIDEBAR_ITEMS}
        last_section = None
        for label, key, section, icon_name in SIDEBAR_ITEMS:
            if section != last_section:
                sec = QLabel(section)
                sec.setObjectName("SidebarSection")
                layout.addWidget(sec)
                last_section = section
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.select(k))
            self.buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch()
        from app import __version__ as _app_version
        self._version = _app_version
        self.foot = QLabel(f"v{_app_version} • Offline")
        self.foot.setObjectName("SidebarFoot")
        layout.addWidget(self.foot)
        self.set_theme_icons(dark=True)

    def set_theme_icons(self, dark: bool):
        if dark:
            off, on = "#9AA6B2", "#FFFFFF"
        else:
            off, on = "#BFD0E4", "#1C355E"
        for key, btn in self.buttons.items():
            btn.setIcon(nav_icon(self._icons.get(key, "help"), off, on, 18))

    def set_compact(self, compact: bool):
        if compact:
            self.setFixedWidth(WIDTH_SHUT)
            self.setMinimumWidth(WIDTH_SHUT)
            self.brand_box.hide()
            self.brand_mark.setFixedSize(36, 36)
            for btn in self.buttons.values():
                btn.setText("")
            for i in range(self.layout().count()):
                w = self.layout().itemAt(i).widget()
                if isinstance(w, QLabel) and w.objectName() == "SidebarSection":
                    w.hide()
            self.foot.setText("v1")
        else:
            self.setFixedWidth(WIDTH_OPEN)
            self.setMinimumWidth(WIDTH_OPEN)
            self.brand_box.show()
            for key, btn in self.buttons.items():
                btn.setText(self._labels.get(key, key))
            for i in range(self.layout().count()):
                w = self.layout().itemAt(i).widget()
                if isinstance(w, QLabel) and w.objectName() == "SidebarSection":
                    w.show()
            self.foot.setText(f"v{self._version} • Offline")

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
        self.setFixedHeight(60)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 14, 8)
        layout.setSpacing(10)
        if toggle_callback:
            self.toggle_btn = QPushButton()
            self.toggle_btn.setObjectName("IconButton")
            self.toggle_btn.setFixedSize(36, 36)
            self.toggle_btn.setToolTip("Collapse / expand sidebar")
            self.toggle_btn.setCursor(Qt.PointingHandCursor)
            self.toggle_btn.clicked.connect(toggle_callback)
            layout.addWidget(self.toggle_btn)
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("College Timetable Manager")
        self.title_label.setObjectName("HeaderTitle")
        self.sub_label = QLabel("Computer Science  •  2026-27")
        self.sub_label.setObjectName("HeaderSub")
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.sub_label)
        layout.addLayout(text_col)
        layout.addStretch()
        self.status = QLabel("● Offline Ready")
        self.status.setObjectName("StatusPill")
        layout.addWidget(self.status)
        if export_callback:
            self.export_btn = QPushButton("Export PDF")
            self.export_btn.setObjectName("PrimaryButton")
            self.export_btn.setToolTip("Export current timetable to PDF")
            self.export_btn.setCursor(Qt.PointingHandCursor)
            self.export_btn.clicked.connect(export_callback)
            layout.addWidget(self.export_btn)
            self.export_btn.hide()
        self.assistant_btn = QPushButton("Assistant")
        self.assistant_btn.setObjectName("SecondaryButton")
        self.assistant_btn.setToolTip("Open the AI assistant (typed chat always works; voice is optional).")
        self.assistant_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.assistant_btn)

    def set_menu_icon(self, dark: bool):
        color = "#F4F7FA" if dark else "#334155"
        if hasattr(self, "toggle_btn"):
            self.toggle_btn.setIcon(icon("menu", color, 18))

    def set_export_visible(self, visible: bool):
        if hasattr(self, "export_btn"):
            self.export_btn.setVisible(visible)

    def refresh(self):
        session = get_session()
        try:
            def get(k, d=""):
                s = session.query(Setting).filter(Setting.key == k).first()
                return s.value if s else d
            college = get("college_name", "My College")
            dept = get("department", "Computer Science")
            year = get("academic_year", "2026-27")
            self.title_label.setText(college)
            self.sub_label.setText(f"{dept}  •  {year}")
        finally:
            session.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("College Timetable Manager")
        self.resize(1280, 800)
        self.setMinimumSize(980, 640)
        try:
            icon_file = logo_path()
            if icon_file:
                self.setWindowIcon(QIcon(icon_file))
        except Exception:
            pass
        init_db()
        try:
            # First launch with a bundled baseline becomes immediately
            # trained; existing installs are never touched.
            from app.services.local_agent.baseline import (
                seed_active_from_baseline,
            )
            seed_active_from_baseline()
        except Exception:
            pass
        central = QWidget()
        central.setObjectName("AppRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.header = Header(toggle_callback=self.toggle_sidebar, export_callback=self.export_current_pdf)
        self.header.export_btn.setIcon(icon("download", "#FFFFFF", 16))
        self.header.assistant_btn.clicked.connect(self.open_assistant)
        root.addWidget(self.header)
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
        try:
            self.dashboard.action_requested.connect(self.on_dashboard_action)
        except Exception:
            pass
        self.settings.themeChanged.connect(lambda t: self.apply_theme())

        self.apply_theme()
        self.sidebar.set_active("Dashboard")
        self.stack.setCurrentIndex(self.key_to_index["Dashboard"])
        self.header.refresh()
        self.header.set_export_visible(False)
        self.dashboard.refresh()

    @staticmethod
    def _wrap_page(view: QWidget) -> QScrollArea:
        """Exactly one page visible: QStackedWidget owns visibility.

        Scroll areas are opaque with no graphics effects, so hidden pages
        can never ghost over the current one.
        """
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(view)
        return scroll

    @staticmethod
    def _clear_effects(root):
        """Remove leftover opacity effects (ghost vector); keep static shadows."""
        def _kill(w):
            try:
                eff = w.graphicsEffect()
                if isinstance(eff, QGraphicsOpacityEffect):
                    w.setGraphicsEffect(None)
            except Exception:
                pass
        _kill(root)
        try:
            for child in root.findChildren(QWidget):
                _kill(child)
        except Exception:
            pass

    def _show_only(self, idx: int):
        # QStackedWidget alone guarantees exactly one visible page.
        # (Manual show()/hide() of layout-managed pages wedges the new
        # page at sizeHint width instead of full stack width.)
        for _, i in self.key_to_index.items():
            try:
                self._clear_effects(self.stack.widget(i))
            except Exception:
                pass
        self.stack.setCurrentIndex(idx)

    def on_navigate(self, key):
        idx = self.key_to_index.get(key)
        if idx is not None:
            self._show_only(idx)
            view = self.views.get(key)
            if view and hasattr(view, "refresh"):
                try:
                    view.refresh()
                except Exception as e:
                    print(f"Refresh error for {key}: {e}")
            if key != "Settings":
                self.header.refresh()
        self.sidebar.set_active(key)
        try:
            self.header.set_export_visible(key == "Timetable")
        except Exception:
            pass

    def on_dashboard_action(self, action: str):
        try:
            if action == "timetable":
                self.on_navigate("Timetable")
            elif action == "add_teacher":
                self.on_navigate("Teachers")
                self.teachers.add_teacher()
            elif action == "add_subject":
                self.on_navigate("Subjects")
                self.subjects.add_subject()
            elif action == "add_room":
                self.on_navigate("Rooms")
                self.rooms.add_room()
        except Exception as e:
            print(f"Dashboard action error {action}: {e}")

    def open_timetable_for_semester(self, semester_id: int):
        self.sidebar.set_active("Timetable")
        self._show_only(self.key_to_index["Timetable"])
        try:
            self.timetable.sem_combo.blockSignals(True)
            idx = self.timetable.sem_combo.findData(semester_id)
            if idx >= 0:
                self.timetable.sem_combo.setCurrentIndex(idx)
            else:
                self.timetable.refresh()
                idx = self.timetable.sem_combo.findData(semester_id)
                if idx >= 0:
                    self.timetable.sem_combo.setCurrentIndex(idx)
        finally:
            try:
                self.timetable.sem_combo.blockSignals(False)
            except Exception:
                pass
        self.timetable.load_timetable()
        self.header.refresh()
        try:
            self.header.set_export_visible(True)
        except Exception:
            pass

    def apply_theme(self):
        session = get_session()
        try:
            s = session.query(Setting).filter(Setting.key == "theme").first()
            theme = s.value if s and s.value in ("light", "dark") else "dark"
        except Exception:
            theme = "dark"
        finally:
            try:
                session.close()
            except Exception:
                pass
        self.setStyleSheet(get_theme_qss(theme))
        dark = theme != "light"
        set_switch_theme(dark)
        try:
            self.sidebar.set_theme_icons(dark)
            self.header.set_menu_icon(dark)
        except Exception:
            pass
        if hasattr(self, "timetable"):
            try:
                self.timetable.grid.set_theme(not dark)
            except Exception:
                pass

    def toggle_sidebar(self):
        self.sidebar_expanded = not getattr(self, "sidebar_expanded", True)
        self.sidebar.set_compact(not self.sidebar_expanded)

    def export_current_pdf(self):
        try:
            self.on_navigate("Timetable")
            self.timetable.export("pdf")
        except Exception:
            pass

    def open_assistant(self):
        try:
            from app.ui.assistant_dialog import open_assistant_dialog
            context = {}
            try:
                context["selected_entry_id"] = getattr(
                    self.timetable.grid, "selected_entry_id", None)
            except Exception:
                pass
            open_assistant_dialog(self, context=context)
        except Exception as e:
            try:
                from app.ui.modals import error as modal_error
                modal_error(self, "Assistant", str(e))
            except Exception:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
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
