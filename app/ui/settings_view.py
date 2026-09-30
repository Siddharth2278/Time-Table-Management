from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QTimeEdit, QComboBox, QScrollArea, QFileDialog
)
from PySide6.QtCore import QTime, Signal
from PySide6.QtCore import Qt
from pathlib import Path
from app.database import get_session, get_data_dir, get_db_path
from app.models import Setting
from app.services.backup_service import backup_database, restore_database, export_json, import_json
from app.ui.widgets import Switch, page_header, show_toast
from app.ui.modals import ask, info, warn, error


class SettingsView(QWidget):
    themeChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._updating = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(12)
        outer.addWidget(page_header("Settings", "College profile, hours, appearance and data backup."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll, 1)

        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        self.group_college = QGroupBox("COLLEGE INFORMATION")
        form = QFormLayout(self.group_college)
        form.setContentsMargins(16, 22, 16, 16)
        form.setSpacing(12)
        self.college_edit = QLineEdit()
        self.college_edit.setPlaceholderText("e.g., Government Polytechnic, Awasari")
        self.dept_edit = QLineEdit()
        self.dept_edit.setPlaceholderText("e.g., Computer Engineering")
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("e.g., 2026-27")
        form.addRow("College Name:", self.college_edit)
        form.addRow("Department:", self.dept_edit)
        form.addRow("Academic Year:", self.year_edit)
        layout.addWidget(self.group_college)

        self.group_time = QGroupBox("DEFAULT TIMETABLE HOURS")
        tf = QFormLayout(self.group_time)
        tf.setContentsMargins(16, 22, 16, 16)
        tf.setSpacing(12)
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        tf.addRow("Default Start:", self.start_edit)
        tf.addRow("Default End:", self.end_edit)
        layout.addWidget(self.group_time)

        self.group_appear = QGroupBox("APPEARANCE")
        af = QFormLayout(self.group_appear)
        af.setContentsMargins(16, 22, 16, 16)
        af.setSpacing(10)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark — low brightness", "dark")
        self.theme_combo.addItem("Light — soft & clean", "light")
        af.addRow("Theme:", self.theme_combo)
        hint2 = QLabel("Takes effect after Save.")
        hint2.setObjectName("Muted")
        hint2.setWordWrap(True)
        af.addRow("", hint2)
        layout.addWidget(self.group_appear)

        self.group_ai = QGroupBox("AI TIMETABLE ASSISTANT")
        af_ai = QFormLayout(self.group_ai)
        af_ai.setContentsMargins(16, 22, 16, 16)
        af_ai.setSpacing(10)
        self.ai_status = QLabel("● Checking...")
        self.ai_status.setObjectName("Muted")
        af_ai.addRow("Internet Status:", self.ai_status)
        self.ai_provider = QComboBox()
        self.ai_provider.addItems(["openai-compatible", "custom"])
        af_ai.addRow("AI Provider:", self.ai_provider)
        self.ai_endpoint = QLineEdit()
        self.ai_endpoint.setPlaceholderText("https://api.example.com/v1")
        af_ai.addRow("Endpoint:", self.ai_endpoint)
        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("e.g., gpt-4o-mini")
        af_ai.addRow("Model:", self.ai_model)
        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.Password)
        self.ai_key.setPlaceholderText("Not set")
        af_ai.addRow("API Key:", self.ai_key)
        key_hint = QLabel("Stored locally, never shown again after saving. CTM_AI_API_KEY env wins.")
        key_hint.setObjectName("Muted")
        key_hint.setWordWrap(True)
        af_ai.addRow("", key_hint)
        self.ai_reference = Switch("Use reference timetable patterns")
        af_ai.addRow("Reference:", self.ai_reference)
        test_row = QHBoxLayout()
        test_row.setContentsMargins(0, 0, 0, 0)
        self.ai_test_btn = QPushButton("Test Connection")
        self.ai_test_btn.setObjectName("SecondaryButton")
        self.ai_test_btn.setCursor(Qt.PointingHandCursor)
        self.ai_test_btn.clicked.connect(self.test_ai_connection)
        test_row.addWidget(self.ai_test_btn)
        test_row.addStretch()
        af_ai.addRow("", test_row)
        layout.addWidget(self.group_ai)

        self.group_backup = QGroupBox("DATA BACKUP")
        bf = QVBoxLayout(self.group_backup)
        bf.setContentsMargins(16, 20, 16, 16)
        bf.setSpacing(8)
        note = QLabel("SQLite database file backup, plus full JSON export / import. Restoring replaces current data — restart the app afterwards.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        bf.addWidget(note)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.backup_btn = QPushButton("Backup Now")
        self.backup_btn.setObjectName("SecondaryButton")
        self.backup_btn.setCursor(Qt.PointingHandCursor)
        self.backup_btn.clicked.connect(self.backup_now)
        row.addWidget(self.backup_btn)
        self.restore_btn = QPushButton("Restore")
        self.restore_btn.setObjectName("SecondaryButton")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.clicked.connect(self.restore_now)
        row.addWidget(self.restore_btn)
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.setObjectName("SecondaryButton")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_data)
        row.addWidget(self.export_btn)
        self.import_btn = QPushButton("Import JSON")
        self.import_btn.setObjectName("SecondaryButton")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self.import_data)
        row.addWidget(self.import_btn)
        row.addStretch()
        bf.addLayout(row)
        layout.addWidget(self.group_backup)

        self.info_label = QLabel("")
        self.info_label.setObjectName("InfoBar")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addStretch()
        scroll.setWidget(container)

        btns = QHBoxLayout()
        btns.setContentsMargins(0, 4, 0, 0)
        btns.addStretch()
        self.save_btn = QPushButton("  Save Settings  ")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setMinimumWidth(140)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save)
        btns.addWidget(self.save_btn)
        outer.addLayout(btns)

    def refresh(self):
        self._updating = True
        session = get_session()
        try:
            def get(key, default=""):
                s = session.query(Setting).filter(Setting.key == key).first()
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
            except Exception:
                self.start_edit.setTime(QTime(10, 15))
                self.end_edit.setTime(QTime(17, 15))
            theme = get("theme", "dark")
            idx = self.theme_combo.findData(theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
            provider = get("ai_provider", "openai-compatible")
            pidx = self.ai_provider.findText(provider)
            if pidx >= 0:
                self.ai_provider.setCurrentIndex(pidx)
            self.ai_endpoint.setText(get("ai_endpoint", ""))
            self.ai_model.setText(get("ai_model", ""))
            self.ai_reference.blockSignals(True)
            self.ai_reference.setChecked(get("ai_reference_enabled", "1") != "0")
            self.ai_reference.blockSignals(False)
            self.ai_key.clear()
            try:
                import os
                from app.services.ai.ai_client import stored_key_get
                has_key = bool(os.environ.get("CTM_AI_API_KEY", "") or stored_key_get())
            except Exception:
                has_key = False
            self.ai_key.setPlaceholderText("Saved (hidden)" if has_key else "Not set")
            self.refresh_ai_status()
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
            warn(self, "Validation", "College name is required.")
            return
        if not year:
            warn(self, "Validation", "Academic year is required.")
            return
        try:
            from app.utils.helpers import time_to_minutes
            if time_to_minutes(end) <= time_to_minutes(start):
                warn(self, "Validation", "End time must be after start time.")
                return
        except Exception as e:
            warn(self, "Validation", str(e))
            return
        session = get_session()
        try:
            def set_key(k, v):
                s = session.query(Setting).filter(Setting.key == k).first()
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
            set_key("ai_provider", self.ai_provider.currentText())
            set_key("ai_endpoint", self.ai_endpoint.text().strip())
            set_key("ai_model", self.ai_model.text().strip())
            set_key("ai_reference_enabled", "1" if self.ai_reference.isChecked() else "0")
            new_key = self.ai_key.text().strip()
            if new_key:
                try:
                    from app.services.ai.ai_client import stored_key_set
                    stored_key_set(new_key)
                except Exception:
                    pass
                self.ai_key.clear()
                self.ai_key.setPlaceholderText("Saved (hidden)")
            session.commit()
            self.themeChanged.emit(theme)
            self.refresh_ai_status()
            show_toast(self, "Settings saved and theme applied.")
        except Exception as e:
            session.rollback()
            error(self, "Error", str(e))
        finally:
            session.close()

    def refresh_ai_status(self):
        try:
            from app.services.ai.ai_client import config_from_settings, provider_status
            session = get_session()
            try:
                state = provider_status(config_from_settings(session))
            finally:
                session.close()
        except Exception:
            state = {"state": "offline", "message": "Internet connection required."}
        dot = {"ready": "● Connected", "offline": "● Offline"}.get(
            state["state"], "● Not configured")
        self.ai_status.setText(f"{dot} — {state['message']}")

    def test_ai_connection(self):
        try:
            from app.services.ai.ai_client import (
                AIConfig, provider_status, stored_key_get,
            )
            import os
            key = self.ai_key.text().strip() or os.environ.get("CTM_AI_API_KEY", "") or stored_key_get()
            config = AIConfig(
                provider=self.ai_provider.currentText(),
                endpoint=self.ai_endpoint.text().strip(),
                model=self.ai_model.text().strip(),
                api_key=key)
            state = provider_status(config)
        except Exception:
            state = {"state": "offline", "message": "Internet connection required."}
        if state["state"] == "ready":
            info(self, "AI Connection", "Connected. The AI generator is available.")
        else:
            warn(self, "AI Connection", state["message"])
        self.refresh_ai_status()

    def backup_now(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", str(get_data_dir() / "timetable_backup.db"), "SQLite DB (*.db)")
        if not path:
            return
        try:
            backup_database(get_db_path(), Path(path))
            show_toast(self, "Backup saved.")
        except Exception as e:
            error(self, "Backup Failed", str(e))

    def restore_now(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore Database", str(get_data_dir()), "SQLite DB (*.db)")
        if not path:
            return
        if not ask(self, "Confirm Restore", "This will overwrite the current database with the backup.\n\nContinue?", ok_text="Restore", destructive=True):
            return
        try:
            restore_database(get_db_path(), Path(path))
            info(self, "Restore Complete", "Database restored successfully. Please restart the application for all views to refresh.")
        except Exception as e:
            error(self, "Restore Failed", str(e))

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", str(get_data_dir() / "timetable_export.json"), "JSON (*.json)")
        if not path:
            return
        session = get_session()
        try:
            export_json(session, Path(path))
            show_toast(self, "Data exported.")
        except Exception as e:
            error(self, "Export Failed", str(e))
        finally:
            session.close()

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import JSON", str(get_data_dir()), "JSON (*.json)")
        if not path:
            return
        if not ask(self, "Confirm Import", "Importing will replace all current data.\n\nContinue?", ok_text="Import", destructive=True):
            return
        session = get_session()
        try:
            import_json(session, Path(path))
            info(self, "Imported", "Data imported successfully. Please restart the application.")
        except Exception as e:
            error(self, "Import Failed", str(e))
        finally:
            session.close()
