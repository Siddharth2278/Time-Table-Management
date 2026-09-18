import sys
import os
from pathlib import Path

# Ensure app can find resources when bundled
def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from app.ui.main_window import MainWindow
    from app.database import init_db

    # High DPI
    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("College Timetable Manager")
    app.setOrganizationName("CollegeTimetable")
    app.setApplicationVersion("1.0.0")

    # Init DB (creates file in AppData/Roaming)
    init_db()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
