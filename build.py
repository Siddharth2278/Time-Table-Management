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

def app_version():
    """Single source of truth: app/__init__.py. Falls back to 1.0.0."""
    try:
        text = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return "1.0.0"

def stamp_installer_version(version):
    """Sync the Inno Setup script version with the app version."""
    iss = ROOT / "installer" / "CollegeTimetableSetup.iss"
    try:
        text = iss.read_text(encoding="utf-8")
    except OSError:
        print("ISS file not found, skipping version stamp")
        return
    import re
    updated, count = re.subn(
        r'(#define MyAppVersion\s+)"[^"]*"', rf'\1"{version}"', text, count=1)
    if count:
        iss.write_text(updated, encoding="utf-8")
        print(f"Stamped installer version: {version}")
    else:
        print("WARNING: could not find MyAppVersion in ISS script")

def verify_packaged_runtime():
    """Pre-build check: sklearn/joblib importable + spec covers frozen imports."""
    print("\n--- Verifying packaged runtime imports ---")
    try:
        import sklearn  # noqa: F401
        import joblib  # noqa: F401
        import scipy  # noqa: F401
        import numpy  # noqa: F401
        print(f"sklearn {sklearn.__version__}, joblib {joblib.__version__} available")
    except ImportError as e:
        print(f"Missing trained-model runtime dependency: {e}")
        sys.exit(1)
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: F401
        print("HistGradientBoostingClassifier import OK")
    except ImportError as e:
        print(f"sklearn HGB unavailable: {e}")
        sys.exit(1)
    spec_text = (ROOT / "CollegeTimetable.spec").read_text(encoding="utf-8")
    for needle in ("trainable_model", "training_dataset", "model_store",
                   "sklearn", "scipy", "joblib", "numpy"):
        if needle not in spec_text:
            print(f"WARNING: spec missing '{needle}'")
            sys.exit(1)
    print("Spec covers trained-model runtime")


def verify_no_bundled_user_data():
    """Installer must never ship a college-specific model or database."""
    print("\n--- Verifying no pretrained user data bundled ---")
    for name in ("model.joblib", "timetable.db",
                 "timetable_learning_profile.json", "training_rows.jsonl"):
        hits = [p for p in
                ((ROOT / "assets").rglob(name) if (ROOT / "assets").exists() else [])
                if "baseline_agent" not in p.parts]
        if hits:
            print(f"Refusing to bundle user data file: {hits[0]}")
            sys.exit(1)
    spec_text = (ROOT / "CollegeTimetable.spec").read_text(encoding="utf-8")
    for name in ("model.joblib", "timetable.db", "timetable_agent_model"):
        # datas= lines must not reference user data; comments mentioning
        # APPDATA are fine.
        for line in spec_text.splitlines():
            if "datas=" in line or "Source" in line:
                if name in line:
                    print(f"Spec must not bundle '{name}': {line}")
                    sys.exit(1)
    print("No pretrained model/DB bundled")


def verify_baseline_package():
    """Validate assets/baseline_agent when present; enforce pre-trained builds."""
    import os
    baseline = ROOT / "assets" / "baseline_agent"
    manifest = baseline / "manifest.json"
    required = os.environ.get("REQUIRE_BASELINE", "").strip() == "1"
    if not manifest.exists():
        if required:
            print("REQUIRE_BASELINE=1 but assets/baseline_agent/manifest.json is missing.")
            sys.exit(1)
        print("Baseline: none bundled (fresh-install starts untrained).")
        return
    try:
        from app.services.local_agent.baseline import validate_baseline_dir
        info = validate_baseline_dir(baseline)
    except Exception as e:
        print(f"Baseline validation FAILED: {e}")
        sys.exit(1)
    print(f"Baseline OK: backend={info.get('backend', '?')}, "
          f"lectures={info.get('lectures', '?')}, "
          f"trained={info.get('trained_at', '-')}")


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
    version = app_version()
    print(f"App version: {version} (from app/__init__.py)")

    # 1. Clean
    for p in [ROOT / "build", ROOT / "dist", ROOT / "__pycache__"]:
        if p.exists():
            print(f"Cleaning {p}")
            shutil.rmtree(p, ignore_errors=True)
    for p in ROOT.rglob("*.spec"):
        # keep our spec
        if p.name != "CollegeTimetable.spec":
            p.unlink(missing_ok=True)

    # 1b. Sync installer version before anything consumes it
    stamp_installer_version(version)

    # 1c. Pre-build guards: trained-model runtime + no bundled user data
    verify_packaged_runtime()
    verify_no_bundled_user_data()
    verify_baseline_package()

    # 2. Ensure dependencies
    print("\n--- Installing dependencies ---")
    run(f"{sys.executable} -m pip install -r requirements.txt --quiet")

    # 2b. Post-install re-verify (frozen build will use these exact wheels)
    verify_packaged_runtime()

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
        print(f"\nExecutable built: {exe} ({size_mb:.1f} MB)")
    else:
        # Try alternative location for onedir
        exe_dir = ROOT / "dist" / "CollegeTimetable" / "CollegeTimetable.exe"
        if exe_dir.exists():
            print(f"\nExecutable built (onedir): {exe_dir}")
            exe = exe_dir
        else:
            print("\nExecutable not found in dist/")
            sys.exit(1)

    # 4b. Smoke-test the freshly built executable (starts GUI headless)
    print("\n--- Smoke-testing executable ---")
    try:
        env = dict(os.environ)
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        probe = subprocess.run(
            [str(exe), "--smoke-test"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=180,
            env=env)
        out = (probe.stdout or "").strip()
        # Windowed executables may swallow stdout; exit code is authoritative.
        if out:
            print(out.splitlines()[-1:])
        if probe.returncode != 0:
            print("Smoke test output:")
            print(probe.stdout)
            print(probe.stderr)
            print("Executable smoke test FAILED")
            sys.exit(1)
        print("Executable smoke test passed")
    except subprocess.TimeoutExpired:
        print("Executable smoke test timed out")
        sys.exit(1)
    except OSError as e:
        # Enterprise Application Control (e.g. WinError 4551) can block
        # running a freshly built unsigned exe on the build machine itself.
        # The exe is still valid for distribution; report and continue to
        # the installer step instead of failing the whole build.
        print(f"Executable smoke test could not run ({e}).")
        print("This is an OS execution policy on the build PC, not a build "
              "failure: the exe was produced and source tests already passed.")
        print("Continuing to installer build; verify the exe on a target PC.")

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
    exe_mb = exe.stat().st_size / (1024*1024) if exe.exists() else 0
    exe_bytes = exe.stat().st_size if exe.exists() else 0
    print(f"Executable: {exe} ({exe_mb:.1f} MB, {exe_bytes} bytes)")
    installer = ROOT / "CollegeTimetableSetup.exe"
    if (ROOT / "dist" / "CollegeTimetableSetup.exe").exists():
        installer = ROOT / "dist" / "CollegeTimetableSetup.exe"
    if installer.exists():
        ins_mb = installer.stat().st_size / (1024*1024)
        print(f"Installer: {installer} ({ins_mb:.1f} MB, {installer.stat().st_size} bytes)")
    else:
        print(f"Installer: not built (ISCC missing) — distribute {exe}")
        installer = None
    print(f"Version: {version} (app/__init__.py + installer stamped)")
    print(f"Dependencies in exe: PySide6, SQLAlchemy, openpyxl, reportlab, "
          f"scikit-learn {__import__('sklearn').__version__}, "
          f"scipy, numpy, joblib (see CollegeTimetable.spec hiddenimports)")
    print("Installer behavior: Program Files (or user dir), data stays in "
          "%APPDATA%\\CollegeTimetableManager\\, Start Menu shortcut, "
          "optional desktop icon, uninstall preserves user data unless Yes.")
    print("User data (per-PC, never bundled):")
    print("  %APPDATA%\\CollegeTimetableManager\\timetable.db")
    print("  %APPDATA%\\CollegeTimetableManager\\timetable_learning_profile.json")
    print("  %APPDATA%\\CollegeTimetableManager\\timetable_agent_model\\model.joblib")
    print("  %APPDATA%\\CollegeTimetableManager\\timetable_agent_model\\metadata.json")
    print("  %APPDATA%\\CollegeTimetableManager\\timetable_agent_model\\training_rows.jsonl")
    print("Ollama required: NO (optional localhost planner only). "
          "Offline generation: YES (trained model + solver, no network).")

if __name__ == "__main__":
    main()
