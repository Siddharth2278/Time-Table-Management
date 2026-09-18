import sys
from pathlib import Path

# Ensure app is importable when frozen
if getattr(sys, 'frozen', False):
    # PyInstaller bundle
    base = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    sys.path.insert(0, str(base))

from app.main import main

if __name__ == "__main__":
    main()
