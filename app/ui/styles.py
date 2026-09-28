"""Institutional theme for College Timetable Manager.

Swiss-design institutional: stark white canvas, sharp 2px borders,
Inter for UI/data, Roboto Slab for headers. Explicit colors only
(Qt QSS has no var()).
"""

FONT_UI = "'Inter', 'Segoe UI', system-ui, sans-serif"
FONT_HEAD = "'Playfair Display', Georgia, serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, monospace"

# Institutional palette — 1:1 with web archival SaaS
NAVY = "#1C355E"
NAVY2 = "#16294A"
CRIMSON = "#DC2626"
CRIMSON_DARK = "#991B1B"
EMERALD = "#059669"
EMERALD_DARK = "#065F46"
PAPER = "#FFFFFF"
CANVAS = "#F8FAFC"
GRID_LINE = "#CBD5E1"

# Shared accent (kept for checked nav)
INDIGO = "#1C355E"
INDIGO_HOVER = "#16294A"
INDIGO_SOFT = "#DBEAFE"
SIDEBAR_BG = "#1C355E"
SIDEBAR_BG2 = "#16294A"


def _common() -> str:
    return f"""
    * {{
        font-family: {FONT_UI};
        font-size: 13px;
    }}
    QLabel#PageTitle, QLabel#HeaderTitle {{
        font-family: {FONT_HEAD};
    }}
    QLabel#StatValue, QLabel#StatusPill {{
        font-family: {FONT_MONO};
    }}
    QToolTip {{
        background-color: #111827;
        color: #F9FAFB;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    QScrollArea#PageScroll {{
        border: none;
        background: #FAF9F6;
    }}
    QScrollArea#PageScroll > QWidget > QWidget {{
        background: #FAF9F6;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: #C3CAD6;
        border-radius: 5px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #9AA5B8; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: #C3CAD6;
        border-radius: 5px;
        min-width: 32px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

    /* Page headings — theme-specific color set below, shared sizing here */
    QLabel#PageTitle {{
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.4px;
    }}
    QLabel#PageSubtitle {{
        font-size: 12.5px;
        font-weight: 500;
    }}
    QLabel#SectionTitle {{
        font-size: 14px;
        font-weight: 700;
    }}
    QLabel#StatValue {{
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.6px;
    }}
    QLabel#StatLabel {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.7px;
    }}
    QFrame#ContentCard {{
        border: 2px solid {GRID_LINE};
        border-radius: 2px;
        padding: 14px;
    }}
    QFrame#StatCard {{
        border: 2px solid {GRID_LINE};
        border-radius: 2px;
        padding: 12px;
    }}
    """


def _sidebar_qss() -> str:
    # 1:1 with web: indigo sidebar, white/75 items, white active, mono section headers.
    return f"""
    QWidget#Sidebar {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid {SIDEBAR_BG2};
    }}
    QLabel#SidebarBrand {{
        color: #FFFFFF;
        font-size: 15px;
        font-weight: 600;
        letter-spacing: -0.2px;
        padding: 0px;
        background: transparent;
        border: none;
    }}
    QLabel#SidebarSub {{
        color: rgba(255, 255, 255, 0.6);
        font-size: 11px;
        font-weight: 500;
        padding: 0px;
        background: transparent;
        border: none;
    }}
    QLabel#SidebarSection {{
        color: rgba(255, 255, 255, 0.5);
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 1px;
        padding: 10px 12px 4px 12px;
        background: transparent;
        border: none;
    }}
    QWidget#Sidebar QPushButton {{
        text-align: left;
        padding: 10px 12px;
        border: none;
        border-radius: 2px;
        color: rgba(255, 255, 255, 0.75);
        font-size: 13px;
        font-weight: 500;
        margin: 2px 8px;
        min-height: 40px;
        background: transparent;
    }}
    QWidget#Sidebar QPushButton:hover {{
        background-color: rgba(255, 255, 255, 0.1);
        color: #FFFFFF;
    }}
    QWidget#Sidebar QPushButton:checked {{
        background-color: #FFFFFF;
        color: #1C355E;
        font-weight: 600;
    }}
    QLabel#SidebarFoot {{
        color: rgba(255, 255, 255, 0.6);
        font-size: 10px;
        padding: 10px 12px;
        background: transparent;
        border: none;
    }}
    """


def _light_qss() -> str:
    return _common() + _sidebar_qss() + f"""
    QMainWindow, QWidget#AppRoot {{
        background-color: #FAF9F6;
    }}
    QWidget#ContentArea {{
        background-color: #FAF9F6;
    }}
    /* Header */
    QWidget#Header {{
        background-color: #FFFFFF;
        border-bottom: 1px solid #DEDCD3;
    }}
    QLabel#HeaderTitle {{
        font-family: {FONT_HEAD};
        font-size: 19px;
        font-weight: 700;
        color: #111110;
        letter-spacing: -0.3px;
        background: transparent;
    }}
    QLabel#HeaderSub {{
        font-size: 12px;
        color: #64748B;
        font-weight: 500;
        background: transparent;
    }}
    QLabel#StatusPill {{
        color: #047857;
        font-weight: 700;
        font-size: 11.5px;
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 14px;
        padding: 5px 12px;
    }}
    QPushButton#IconButton {{
        background: #F1F5F9;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        color: #334155;
        font-size: 15px;
        min-height: 32px;
    }}
    QPushButton#IconButton:hover {{
        background: #E2E8F0;
        color: #111110;
    }}
    QLabel#PageTitle {{ color: #111110; background: transparent; font-family: {FONT_HEAD}; }}
    QLabel#PageSubtitle {{ color: #64748B; background: transparent; }}
    QLabel#SectionTitle {{ color: #1E293B; background: transparent; font-family: {FONT_HEAD}; }}
    QLabel#StatValue {{ color: #111110; background: transparent; }}
    QLabel#StatLabel {{ color: #64748B; background: transparent; }}
    QFrame#ContentCard {{
        background-color: #FFFFFF;
        border: 2px solid #DEDCD3;
    }}
    QFrame#StatCard {{
        background-color: #FFFFFF;
        border: 2px solid #DEDCD3;
    }}
    QFrame#Card {{
        background-color: #FFFFFF;
        border: 1px solid #DEDCD3;
        border-radius: 2px;
        padding: 14px;
    }}
    /* Buttons — sharp institutional */
    QPushButton {{
        min-height: 44px;
        border-radius: 2px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton#PrimaryButton {{
        background-color: {INDIGO};
        border: 2px solid {INDIGO_HOVER};
        color: #FFFFFF;
    }}
    QPushButton#PrimaryButton:hover {{ background-color: {INDIGO_HOVER}; }}
    QPushButton#PrimaryButton:pressed {{ background-color: #3730A3; }}
    QPushButton#SecondaryButton {{
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        color: #1E293B;
    }}
    QPushButton#SecondaryButton:hover {{
        background-color: {INDIGO_SOFT};
        border-color: {INDIGO};
        color: {INDIGO_HOVER};
    }}
    QPushButton#DangerButton {{
        background-color: {CRIMSON};
        border: 2px solid {CRIMSON_DARK};
        color: #FFFFFF;
    }}
    QPushButton#DangerButton:hover {{ background-color: {CRIMSON_DARK}; }}
    /* Tables — precise borders, mobile touch rows */
    QTableWidget {{
        background-color: #FFFFFF;
        alternate-background-color: #F8FAFC;
        gridline-color: {GRID_LINE};
        border: 1px solid #DEDCD3;
        border-radius: 2px;
        selection-background-color: #DBEAFE;
        selection-color: #111110;
        color: #111110;
        font-size: 13px;
    }}
    QTableWidget::item {{
        padding: 12px 8px;
        color: #111110;
        border-bottom: 1px solid {GRID_LINE};
    }}
    QTableWidget::item:selected {{
        background-color: #DBEAFE;
        color: #1C355E;
        font-weight: 600;
    }}
    QHeaderView::section {{
        background-color: #F3F1EA;
        color: #57534E;
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid #DEDCD3;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.6px;
    }}
    QTableCornerButton::section {{
        background-color: #F3F1EA;
        border: none;
    }}
    /* Inputs */
    QLineEdit, QComboBox, QSpinBox, QTimeEdit, QTextEdit {{
        background-color: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        color: #111110;
        selection-background-color: {INDIGO};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QTextEdit:focus {{
        border: 2px solid {INDIGO};
        background-color: #FFFFFF;
    }}
    QLineEdit::placeholder {{ color: #94A3B8; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #64748B;
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #FFFFFF;
        color: #111110;
        selection-background-color: {INDIGO_SOFT};
        selection-color: {INDIGO_HOVER};
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 4px;
        outline: none;
    }}
    /* Group boxes */
    QGroupBox {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        margin-top: 16px;
        padding: 16px;
        padding-top: 22px;
        font-weight: 700;
        font-size: 13px;
        color: #111110;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 4px 12px;
        background-color: {INDIGO};
        color: #FFFFFF;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
    }}
    /* Progress */
    QProgressBar {{
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        text-align: center;
        background-color: #F1F5F9;
        height: 20px;
        color: #1E293B;
        font-weight: 700;
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background-color: {INDIGO};
        border-radius: 7px;
    }}
    /* Tabs */
    QTabWidget::pane {{
        border: 1px solid #E2E8F0;
        background: #FFFFFF;
        border-radius: 12px;
        top: -1px;
    }}
    QTabBar::tab {{
        padding: 10px 18px;
        background: #F1F5F9;
        border: 1px solid #E2E8F0;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
        color: #64748B;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: #FFFFFF;
        color: {INDIGO_HOVER};
        font-weight: 700;
        border-bottom: 2px solid {INDIGO};
    }}
    /* Dialogs + message boxes — always light & readable */
    QDialog {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
    }}
    QDialog QLabel {{ color: #1E293B; }}
    QMessageBox {{
        background-color: #FFFFFF;
    }}
    QMessageBox QLabel {{
        color: #111110;
        font-size: 13px;
    }}
    QMessageBox QPushButton {{
        min-width: 86px;
    }}
    QCheckBox {{
        color: #1E293B;
        spacing: 8px;
        font-weight: 500;
    }}
    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
        border-radius: 5px;
        border: 1.5px solid #CBD5E1;
        background: #FFFFFF;
    }}
    QCheckBox::indicator:checked {{
        background: {INDIGO};
        border-color: {INDIGO_HOVER};
    }}
    QLabel {{
        color: #1E293B;
    }}
    """


def _dark_qss() -> str:
    return _common() + _sidebar_qss() + f"""
    QMainWindow, QWidget#AppRoot {{
        background-color: #0B1220;
    }}
    QWidget#ContentArea {{
        background-color: #0B1220;
    }}
    QWidget#Header {{
        background-color: #111C34;
        border-bottom: 1px solid #22304D;
    }}
    QLabel#HeaderTitle {{
        font-size: 17px;
        font-weight: 800;
        color: #F1F5F9;
        background: transparent;
    }}
    QLabel#HeaderSub {{
        font-size: 12px;
        color: #94A3B8;
        font-weight: 500;
        background: transparent;
    }}
    QLabel#StatusPill {{
        color: #6EE7B7;
        font-weight: 700;
        font-size: 11.5px;
        background: #064E3B;
        border: 1px solid #065F46;
        border-radius: 14px;
        padding: 5px 12px;
    }}
    QPushButton#IconButton {{
        background: #1A2540;
        border: 1px solid #2A3A5C;
        border-radius: 8px;
        color: #E2E8F0;
        font-size: 15px;
        min-height: 32px;
    }}
    QPushButton#IconButton:hover {{ background: #22304D; }}
    QLabel#PageTitle {{ color: #F1F5F9; background: transparent; }}
    QLabel#PageSubtitle {{ color: #94A3B8; background: transparent; }}
    QLabel#SectionTitle {{ color: #E2E8F0; background: transparent; }}
    QLabel#StatValue {{ color: #F1F5F9; background: transparent; }}
    QLabel#StatLabel {{ color: #94A3B8; background: transparent; }}
    QFrame#ContentCard {{
        background-color: #141F38;
        border: 1px solid #22304D;
    }}
    QFrame#StatCard {{
        background-color: #141F38;
        border: 1px solid #22304D;
    }}
    QFrame#Card {{
        background-color: #141F38;
        border: 1px solid #22304D;
        border-radius: 14px;
        padding: 14px;
    }}
    QPushButton {{
        min-height: 34px;
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton#PrimaryButton {{
        background-color: {INDIGO};
        border: 1px solid #6366F1;
        color: #FFFFFF;
    }}
    QPushButton#PrimaryButton:hover {{ background-color: {INDIGO_HOVER}; }}
    QPushButton#SecondaryButton {{
        background-color: #1A2540;
        border: 1px solid #2E3E63;
        color: #E2E8F0;
    }}
    QPushButton#SecondaryButton:hover {{
        background-color: #22304D;
        border-color: #6366F1;
        color: #FFFFFF;
    }}
    QPushButton#DangerButton {{
        background-color: #DC2626;
        border: 1px solid #991B1B;
        color: #FFFFFF;
    }}
    QPushButton#DangerButton:hover {{ background-color: #B91C1C; }}
    QTableWidget {{
        background-color: #141F38;
        alternate-background-color: #182645;
        gridline-color: #22304D;
        border: 1px solid #22304D;
        border-radius: 12px;
        selection-background-color: {INDIGO};
        selection-color: #FFFFFF;
        color: #E2E8F0;
    }}
    QTableWidget::item {{
        padding: 9px 8px;
        color: #E2E8F0;
        border-bottom: 1px solid #1E2A44;
    }}
    QTableWidget::item:selected {{
        background-color: {INDIGO};
        color: #FFFFFF;
        font-weight: 600;
    }}
    QHeaderView::section {{
        background-color: #1A2540;
        color: #94A3B8;
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid #22304D;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.6px;
    }}
    QTableCornerButton::section {{
        background-color: #1A2540;
        border: none;
    }}
    QLineEdit, QComboBox, QSpinBox, QTimeEdit, QTextEdit {{
        background-color: #1A2540;
        border: 1.5px solid #2E3E63;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        color: #F1F5F9;
        selection-background-color: {INDIGO};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QTextEdit:focus {{
        border: 2px solid #6366F1;
    }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #94A3B8;
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #1A2540;
        color: #F1F5F9;
        selection-background-color: {INDIGO};
        selection-color: #FFFFFF;
        border: 1px solid #2E3E63;
        padding: 4px;
        outline: none;
    }}
    QGroupBox {{
        background-color: #141F38;
        border: 1px solid #22304D;
        border-radius: 12px;
        margin-top: 16px;
        padding: 16px;
        padding-top: 22px;
        font-weight: 700;
        font-size: 13px;
        color: #F1F5F9;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 4px 12px;
        background-color: {INDIGO};
        color: #FFFFFF;
        border-radius: 6px;
        font-size: 12px;
    }}
    QProgressBar {{
        border: none;
        border-radius: 8px;
        text-align: center;
        background-color: #22304D;
        height: 20px;
        color: #F1F5F9;
        font-weight: 700;
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background-color: #6366F1;
        border-radius: 8px;
    }}
    QTabWidget::pane {{
        border: 1px solid #22304D;
        background: #141F38;
        border-radius: 12px;
        top: -1px;
    }}
    QTabBar::tab {{
        padding: 10px 18px;
        background: #141F38;
        border: 1px solid #22304D;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
        color: #94A3B8;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: #1A2540;
        color: #FFFFFF;
        font-weight: 700;
        border-bottom: 2px solid #6366F1;
    }}
    QDialog {{ background-color: #141F38; }}
    QDialog QLabel {{ color: #E2E8F0; }}
    QMessageBox {{ background-color: #141F38; }}
    QMessageBox QLabel {{ color: #F1F5F9; font-size: 13px; }}
    QMessageBox QPushButton {{ min-width: 86px; }}
    QCheckBox {{ color: #E2E8F0; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
        border-radius: 5px;
        border: 1.5px solid #3B4D75;
        background: #1A2540;
    }}
    QCheckBox::indicator:checked {{
        background: {INDIGO};
        border-color: #6366F1;
    }}
    QLabel {{
        color: #E2E8F0;
    }}
    """


def get_theme_qss(theme: str) -> str:
    if theme == "dark":
        return _dark_qss()
    return _light_qss()
