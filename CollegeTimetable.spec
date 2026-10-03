# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Trained-model runtime: HistGradientBoostingClassifier pulls compiled
# submodules dynamically (tree splits, boosters, utils) plus scipy/numpy.
# Narrow collects keep the frozen train → save → reload → generate path
# working without bloating the build (never collect all of sklearn/scipy:
# that drags in tests, matplotlib and pandas and stalls PyInstaller).
# NOTE: user data (timetable.db, learned profile, trained model.joblib)
# lives in %APPDATA% and is NEVER bundled into the installer.
try:
    from PyInstaller.utils.hooks import collect_submodules
    _sklearn_extra = (
        collect_submodules('sklearn.ensemble')
        + collect_submodules('sklearn.tree')
        + collect_submodules('sklearn.utils')
        + collect_submodules('sklearn.preprocessing')
        + collect_submodules('joblib')
    )
    # Drop test/helper packages that sometimes ride along with collects.
    _sklearn_extra = [m for m in _sklearn_extra
                      if '.test' not in m and not m.endswith('.test')
                      and 'test_common' not in m and 'conftest' not in m]
except Exception:
    _sklearn_extra = []

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[('assets/logo.svg', 'assets')],
    hiddenimports=[
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        'app.models',
        'app.database',
        'app.utils.helpers',
        'app.services.conflict_service',
        'app.services.timetable_service',
        'app.services.export_service',
        'app.services.backup_service',
        'app.services.intelligence',
        'app.services.intelligence.timetable_agent',
        'app.services.intelligence.timetable_optimizer',
        'app.services.intelligence.candidate_generator',
        'app.services.intelligence.reference_analyzer',
        'app.services.intelligence.requirement_analyzer',
        'app.services.intelligence.pattern_extractor',
        'app.services.intelligence.subject_role_mapper',
        'app.services.intelligence.timetable_template',
        'app.services.intelligence.timetable_scorer',
        'app.services.intelligence.generation_result',
        'app.services.intelligence.structural_analyzer',
        'app.services.local_agent',
        'app.services.local_agent.agent',
        'app.services.local_agent.model_client',
        'app.services.local_agent.model_store',
        'app.services.local_agent.netpolicy',
        'app.services.local_agent.pattern_store',
        'app.services.local_agent.planner',
        'app.services.local_agent.requirements',
        'app.services.local_agent.schemas',
        'app.services.local_agent.timetable_learner',
        'app.services.local_agent.trainable_model',
        'app.services.local_agent.training_dataset',
        'app.ui.main_window',
        'app.ui.dashboard',
        'app.ui.timetable_view',
        'app.ui.timetable_grid',
        'app.ui.teacher_view',
        'app.ui.subject_view',
        'app.ui.room_view',
        'app.ui.semester_view',
        'app.ui.timeslot_view',
        'app.ui.settings_view',
        'app.ui.help_view',
        'app.ui.dialogs',
        'app.ui.styles',
        'app.ui.icons',
        'app.ui.widgets',
        'app.ui.animations',
        'app.ui.modals',
        'app.ui.availability_view',
        'app.ui.conflict_view',
        'app.ui.backup_view',
        'app.ui.intelligence_dialog',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'openpyxl',
        'openpyxl.styles',
        'et_xmlfile',
        'reportlab',
        'reportlab.lib.pagesizes',
        'reportlab.lib.colors',
        'reportlab.lib.units',
        'reportlab.lib.styles',
        'reportlab.lib.enums',
        'reportlab.platypus',
        'sklearn',
        'sklearn.ensemble',
        'sklearn.ensemble._hist_gradient_boosting',
        'sklearn.tree',
        'sklearn.utils',
        'sklearn.preprocessing',
        'sklearn.base',
        # HGB runtime deps (hooks cover binaries; names keep modulegraph honest).
        'scipy.sparse',
        'scipy.special',
        'numpy',
        'joblib',
    ] + _sklearn_extra,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pyinstaller', 'tkinter', 'matplotlib', 'pandas',
              'sklearn.tests', 'scipy.tests', 'numpy.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CollegeTimetable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
