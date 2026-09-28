import sys
import os
from pathlib import Path

# Ensure app can find resources when bundled
def main():
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.ui.main_window import MainWindow
    from app.database import init_db

    app = QApplication(sys.argv)
    app.setApplicationName("College Timetable Manager")
    app.setOrganizationName("CollegeTimetable")
    app.setApplicationVersion("1.0.0")

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
