import sys
import os
from pathlib import Path

# Ensure app can find resources when bundled
def main():
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QLockFile, QDir
    from app.ui.main_window import MainWindow
    from app.database import init_db, get_data_dir

    app = QApplication(sys.argv)
    app.setApplicationName("College Timetable Manager")
    app.setOrganizationName("CollegeTimetable")
    app.setApplicationVersion("1.0.0")

    # Single instance: second launch warns instead of ghosting over the first
    lock_path = str(get_data_dir() / "app.lock")
    _lock = QLockFile(lock_path)
    _lock.setStaleLockTime(0)
    if not _lock.tryLock(100):
        QMessageBox.warning(
            None,
            "Already running",
            "College Timetable Manager is already open.\nClose the old window (check Task Manager for CollegeTimetable.exe) then retry.",
        )
        sys.exit(0)

    # Init DB (creates file in AppData/Roaming) — fail with dialog, not traceback
    try:
        init_db()
    except Exception as e:
        QMessageBox.critical(None, "Database error", f"Could not open database:\n{e}")
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
