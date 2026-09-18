from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QGroupBox, QLineEdit
from PySide6.QtCore import Qt
from app.database import get_db_path, get_data_dir, get_session
from app.services.backup_service import backup_database, restore_database, export_json, import_json

class BackupView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)
        title = QLabel("Backup & Restore")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #1E2A3A;")
        layout.addWidget(title)
        sub = QLabel("Keep your timetable safe. Backup stores a copy of the SQLite database. Restore will overwrite current data.")
        sub.setStyleSheet("color: #64748B; font-size: 11px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Database location
        self.path_label = QLabel(f"Database location: {get_db_path()}")
        self.path_label.setStyleSheet("background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; color: #334155; font-size: 11px;")
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
        rgl.addWidget(QLabel("⚠ Restore will replace all current data. Backup current data first."))
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
            QMessageBox.information(self, "Backup Complete", f"Backup saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Backup to Restore", str(Path.home()), "SQLite DB (*.db);;All Files (*.*)")
        if not path:
            return
        if QMessageBox.question(self, "Confirm Restore", "This will overwrite the current database with the backup.\n\nContinue?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            # Close any open sessions? Just copy
            restore_database(get_db_path(), Path(path))
            QMessageBox.information(self, "Restore Complete", "Database restored successfully. Please restart the application for all views to refresh.")
        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", str(e))

    def do_export_json(self):
        default = str(Path.home() / "Documents" / "timetable_export.json")
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", default, "JSON (*.json)")
        if not path:
            return
        session = get_session()
        try:
            export_json(session, Path(path))
            QMessageBox.information(self, "Exported", f"Exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
        finally:
            session.close()

    def do_import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import JSON", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        if QMessageBox.question(self, "Confirm Import", "Importing will replace all current data.\n\nContinue?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            import_json(session, Path(path))
            QMessageBox.information(self, "Imported", "Data imported successfully. Please restart the application.")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))
        finally:
            session.close()
