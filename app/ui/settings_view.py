from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout, QMessageBox, QGroupBox, QTimeEdit, QComboBox, QScrollArea
from PySide6.QtCore import QTime, Signal
from app.database import get_session, get_data_dir, get_db_path
from app.models import Setting

class SettingsView(QWidget):
    themeChanged = Signal(str)
    def __init__(self):
        super().__init__()
        self._updating = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(0)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        outer.addWidget(title)
        sub = QLabel("Configure college and timetable preferences")
        sub.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 10px;")
        outer.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget { background: transparent; }")
        outer.addWidget(scroll, 1)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(16)

        # College info
        self.group_college = QGroupBox("College Information")
        form = QFormLayout(self.group_college)
        form.setContentsMargins(16, 22, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(form.labelAlignment())
        self.college_edit = QLineEdit()
        self.college_edit.setPlaceholderText("e.g., Government Polytechnic, Awasari")
        self.dept_edit = QLineEdit()
        self.dept_edit.setPlaceholderText("e.g., Computer Engineering")
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("e.g., 2026-27")
        for w in [self.college_edit, self.dept_edit, self.year_edit]:
            w.setMinimumHeight(36)
        form.addRow("College Name:", self.college_edit)
        form.addRow("Department:", self.dept_edit)
        form.addRow("Academic Year:", self.year_edit)
        layout.addWidget(self.group_college)

        # Time defaults
        self.group_time = QGroupBox("Default Timetable Hours")
        tf = QFormLayout(self.group_time)
        tf.setContentsMargins(16, 22, 16, 16)
        tf.setSpacing(12)
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setMinimumHeight(36)
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setMinimumHeight(36)
        tf.addRow("Default Start:", self.start_edit)
        tf.addRow("Default End:", self.end_edit)
        layout.addWidget(self.group_time)

        # Appearance
        self.group_appear = QGroupBox("Appearance")
        af = QFormLayout(self.group_appear)
        af.setContentsMargins(16, 22, 16, 16)
        af.setSpacing(10)
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumHeight(36)
        self.theme_combo.addItem("Light — soft & clean", "light")
        self.theme_combo.addItem("Dark — low brightness", "dark")
        af.addRow("Theme:", self.theme_combo)
        hint2 = QLabel("Dark reduces eye strain. Takes effect after Save.")
        hint2.setStyleSheet("color: #64748B; font-size: 11px;")
        hint2.setWordWrap(True)
        af.addRow("", hint2)
        layout.addWidget(self.group_appear)

        # Info - subtle
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #64748B; font-size: 11px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addStretch()
        scroll.setWidget(container)

        # Save bar - fixed at bottom
        btns = QHBoxLayout()
        btns.setContentsMargins(0, 12, 0, 0)
        btns.addStretch()
        self.save_btn = QPushButton("  Save Settings  ")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setMinimumHeight(38)
        self.save_btn.setMinimumWidth(140)
        self.save_btn.clicked.connect(self.save)
        btns.addWidget(self.save_btn)
        outer.addLayout(btns)

    def refresh(self):
        self._updating = True
        session = get_session()
        try:
            def get(key, default=""):
                s = session.query(Setting).filter(Setting.key==key).first()
                return s.value if s else default
            self.college_edit.setText(get("college_name", "My College"))
            self.dept_edit.setText(get("department", "Computer Engineering"))
            self.year_edit.setText(get("academic_year", "2026-27"))
            start = get("default_start_time", "08:00")
            end = get("default_end_time", "17:00")
            try:
                sh, sm = map(int, start.split(":"))
                eh, em = map(int, end.split(":"))
                self.start_edit.setTime(QTime(sh, sm))
                self.end_edit.setTime(QTime(eh, em))
            except:
                self.start_edit.setTime(QTime(10, 15))
                self.end_edit.setTime(QTime(17, 15))
            theme = get("theme", "dark")
            idx = self.theme_combo.findData(theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
            self.info_label.setText(f"Storage: {get_data_dir()}  •  DB: {get_db_path().name}  •  Offline SQLite — survives reinstall")
        finally:
            session.close()
            self._updating = False

    def save(self):
        college = self.college_edit.text().strip()
        dept = self.dept_edit.text().strip()
        year = self.year_edit.text().strip()
        start = self.start_edit.time().toString("HH:mm")
        end = self.end_edit.time().toString("HH:mm")
        if not college:
            QMessageBox.warning(self, "Validation", "College name is required.")
            return
        if not year:
            QMessageBox.warning(self, "Validation", "Academic year is required.")
            return
        try:
            from app.utils.helpers import time_to_minutes
            if time_to_minutes(end) <= time_to_minutes(start):
                QMessageBox.warning(self, "Validation", "End time must be after start time.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Validation", str(e))
            return
        session = get_session()
        try:
            def set_key(k, v):
                s = session.query(Setting).filter(Setting.key==k).first()
                if s:
                    s.value = v
                else:
                    session.add(Setting(key=k, value=v))
            set_key("college_name", college)
            set_key("department", dept)
            set_key("academic_year", year)
            set_key("default_start_time", start)
            set_key("default_end_time", end)
            theme = self.theme_combo.currentData()
            set_key("theme", theme)
            session.commit()
            self.themeChanged.emit(theme)
            QMessageBox.information(self, "Saved", "Settings saved and theme applied.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
