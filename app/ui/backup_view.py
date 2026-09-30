from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QGroupBox, QLineEdit
from PySide6.QtCore import Qt
from app.database import get_db_path, get_data_dir, get_session
from app.services.backup_service import backup_database, restore_database, export_json, import_json
from app.ui.modals import ask, info, error
from app.ui.widgets import show_toast, page_header

class BackupView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(page_header(
            "Backup & Restore",
            "Keep your timetable safe. Backup stores a copy of the SQLite database. Restore will overwrite current data."))

        # Database location
        self.path_label = QLabel(f"Database location: {get_db_path()}")
        self.path_label.setObjectName("InfoBar")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.path_label)

        # Backup group
        bg = QGroupBox("Backup Database")
        bgl = QVBoxLayout(bg)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Create a backup file (.db):"))
        row1.addStretch()
        self.backup_btn = QPushButton("Backup Now")
        self.backup_btn.setObjectName("PrimaryButton")
        self.backup_btn.clicked.connect(self.do_backup)
        row1.addWidget(self.backup_btn)
        bgl.addLayout(row1)
        bgl.addWidget(QLabel("You can choose any location (USB, Documents, etc.). Keep backups safely."))
        layout.addWidget(bg)

        rg = QGroupBox("Restore Database")
        rgl = QVBoxLayout(rg)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Restore from a previous backup (.db):"))
        row2.addStretch()
        self.restore_btn = QPushButton("Restore...")
        self.restore_btn.setObjectName("SecondaryButton")
        self.restore_btn.clicked.connect(self.do_restore)
        row2.addWidget(self.restore_btn)
        rgl.addLayout(row2)
        rgl.addWidget(QLabel("Restore will replace all current data. Backup current data first."))
        layout.addWidget(rg)

        # Import/export json
        jg = QGroupBox("Export / Import (JSON)")
        jgl = QVBoxLayout(jg)
        jr = QHBoxLayout()
        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.setObjectName("SecondaryButton")
        self.export_json_btn.clicked.connect(self.do_export_json)
        jr.addWidget(self.export_json_btn)
        self.import_json_btn = QPushButton("Import JSON")
        self.import_json_btn.setObjectName("SecondaryButton")
        self.import_json_btn.clicked.connect(self.do_import_json)
        jr.addWidget(self.import_json_btn)
        jr.addStretch()
        jgl.addLayout(jr)
        jgl.addWidget(QLabel("JSON export contains all tables and can be imported on another machine."))
        layout.addWidget(jg)

        layout.addStretch()

    def refresh(self):
        self.path_label.setText(f"Database location: {get_db_path()}")

    def do_backup(self):
        default = str(Path.home() / "Documents" / f"timetable_backup_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        path, _ = QFileDialog.getSaveFileName(self, "Save Backup", default, "SQLite DB (*.db);;All Files (*.*)")
        if not path:
            return
        try:
            backup_database(get_db_path(), Path(path))
            show_toast(self, "Backup saved.")
        except Exception as e:
            error(self, "Backup Failed", str(e))

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Backup to Restore", str(Path.home()), "SQLite DB (*.db);;All Files (*.*)")
        if not path:
            return
        if not ask(self, "Confirm Restore", "This will overwrite the current database with the backup.\n\nContinue?", ok_text="Restore", destructive=True):
            return
        try:
            # Close any open sessions? Just copy
            restore_database(get_db_path(), Path(path))
            info(self, "Restore Complete", "Database restored successfully. Please restart the application for all views to refresh.")
        except Exception as e:
            error(self, "Restore Failed", str(e))

    def do_export_json(self):
        default = str(Path.home() / "Documents" / "timetable_export.json")
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", default, "JSON (*.json)")
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

    def do_import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import JSON", str(Path.home()), "JSON (*.json)")
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
