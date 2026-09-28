#!/usr/bin/env python3
"""
Build script for College Timetable Manager
- Builds executable with PyInstaller
- Creates installer with Inno Setup (if available)
"""
import subprocess
import sys
import shutil
from pathlib import Path
import os

ROOT = Path(__file__).parent

def run(cmd, cwd=ROOT):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(result.returncode)

def main():
    print("="*60)
    print("College Timetable Manager - Build Script")
    print("="*60)

    # 1. Clean
    for p in [ROOT / "build", ROOT / "dist", ROOT / "__pycache__"]:
        if p.exists():
            print(f"Cleaning {p}")
            shutil.rmtree(p, ignore_errors=True)
    for p in ROOT.rglob("*.spec"):
        # keep our spec
        if p.name != "CollegeTimetable.spec":
            p.unlink(missing_ok=True)

    # 2. Ensure dependencies
    print("\n--- Installing dependencies ---")
    run(f"{sys.executable} -m pip install -r requirements.txt --quiet")

    # 3. Run tests
    print("\n--- Running tests ---")
    run(f"{sys.executable} -m pytest tests/ -v")

    # 4. Build with PyInstaller
    print("\n--- Building executable with PyInstaller ---")
    # Use spec file
    run(f"{sys.executable} -m PyInstaller --noconfirm --clean CollegeTimetable.spec")

    exe = ROOT / "dist" / "CollegeTimetable.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024*1024)
        print(f"\n✓ Executable built: {exe} ({size_mb:.1f} MB)")
    else:
        # Try alternative location for onedir
        exe_dir = ROOT / "dist" / "CollegeTimetable" / "CollegeTimetable.exe"
        if exe_dir.exists():
            print(f"\n✓ Executable built (onedir): {exe_dir}")
            exe = exe_dir
        else:
            print("\n✗ Executable not found in dist/")
            sys.exit(1)

    # 5. Try Inno Setup
    print("\n--- Checking for Inno Setup ---")
    iscc = shutil.which("ISCC") or shutil.which("iscc")
    # Common paths
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    ]
    iss_path = ROOT / "installer" / "CollegeTimetableSetup.iss"
    if not iscc:
        for c in candidates:
            if Path(c).exists():
                iscc = c
                break
    if iscc and iss_path.exists():
        print(f"Found Inno Setup: {iscc}")
        print("Building installer...")
        run(f'"{iscc}" "{iss_path}"')
        installer = ROOT / "CollegeTimetableSetup.exe"
        if installer.exists():
            size_mb = installer.stat().st_size / (1024*1024)
            print(f"\n✓ Installer built: {installer} ({size_mb:.1f} MB)")
        else:
            print("Installer not found after ISCC")
    else:
        if not iscc:
            print("Inno Setup (ISCC) not found. Skipping installer creation.")
            print("To create installer:")
            print("  1. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php")
            print("  2. Run: ISCC installer/CollegeTimetableSetup.iss")
            print(f"\nYou can still distribute the executable: {exe}")
        else:
            print(f"ISS file not found: {iss_path}")

    print("\n" + "="*60)
    print("Build complete!")
    print("="*60)
    print(f"Executable: {exe}")
    installer = ROOT / "CollegeTimetableSetup.exe"
    if installer.exists():
        print(f"Installer: {installer}")
    print("\nTo test the app, run:")
    print(f"  {exe}")
    print("\nUser data is stored in:")
    print("  %APPDATA%/CollegeTimetableManager/timetable.db")

if __name__ == "__main__":
    main()
