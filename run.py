import sys
import os
from pathlib import Path

# Ensure app is importable when frozen
if getattr(sys, 'frozen', False):
    # PyInstaller bundle
    base = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    sys.path.insert(0, str(base))

from app.main import main


def smoke_test() -> int:
    """Headless startup check for packaged builds: open the main window,
    walk every page once, verify exactly one page is visible, then exit.
    Prints SMOKE-OK on success, returns a nonzero exit code on failure."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
        from app.database import init_db
        from app.ui.main_window import MainWindow
    except Exception as e:
        print(f"SMOKE-FAIL: imports: {e}")
        return 2
    try:
        init_db()
        app = QApplication([])
        window = MainWindow()
        window.resize(1280, 800)
        window.show()
        app.processEvents()
        pages = ["Dashboard", "Timetable", "Teachers", "Subjects", "Rooms",
                 "Semesters", "TimeSlots", "Help", "Settings"]
        for key in pages:
            window.on_navigate(key)
            app.processEvents()
            visible = [window.stack.widget(i)
                       for i in range(window.stack.count())
                       if window.stack.widget(i).isVisibleTo(window.stack)]
            if window.stack.currentIndex() != window.key_to_index[key] or len(visible) != 1:
                print(f"SMOKE-FAIL: navigation to {key}")
                return 3
        print(f"SMOKE-OK: {len(pages)} pages, single visible page each")
        return 0
    except Exception as e:
        print(f"SMOKE-FAIL: {type(e).__name__}: {e}")
        return 1


def smoke_train() -> int:
    """Frozen-build check: fit a tiny model, persist, reload, score.

    Uses a temp directory (never touches real user data). Prints
    SMOKE-TRAIN-OK with the active backend on success.
    """
    import tempfile
    try:
        from app.services.local_agent import model_store
    except Exception as e:
        print(f"SMOKE-TRAIN-FAIL: imports: {e}")
        return 2
    try:
        tmp = tempfile.mkdtemp(prefix="ctm-smoke-train-")
        rows = []
        for day in ("Monday", "Wednesday", "Friday"):
            rows.append({"code": "MA101", "name": "Maths", "type": "Theory",
                         "duration": 60, "day": day,
                         "start": "09:00", "end": "10:00",
                         "teacher": "Dr A", "room": "101",
                         "source": "smoke"})
        for day in ("Tuesday", "Thursday"):
            rows.append({"code": "PH102", "name": "Physics", "type": "Practical",
                         "duration": 120, "day": day,
                         "start": "14:00", "end": "16:00",
                         "teacher": "Dr B", "room": "Lab 1",
                         "source": "smoke"})
        report = model_store.train_from_rows(rows, source_label="smoke",
                                             data_dir=tmp, replace=True)
        model, metadata = model_store.load_model(tmp)
        scores = model_store.score_candidates(
            model, [[0.5] * len(report["features"])])
        if len(scores) != 1:
            print("SMOKE-TRAIN-FAIL: prediction check")
            return 1
        print(f"SMOKE-TRAIN-OK: backend={report.get('backend', '?')} "
              f"samples={report.get('positives', 0)}+{report.get('negatives', 0)}")
        return 0
    except Exception as e:
        print(f"SMOKE-TRAIN-FAIL: {type(e).__name__}: {e}")
        return 1
    finally:
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        sys.exit(smoke_test())
    if "--smoke-train" in sys.argv:
        sys.exit(smoke_train())
    main()
