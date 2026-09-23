"""Modern premium theme for College Timetable Manager.

Design goals:
- No CSS variables (Qt QSS does not support var()) — every color is explicit.
- Sidebar is ALWAYS dark navy so white text is always readable.
- Content area: clean light theme by default, polished dark theme optional.
- High-contrast body text: dark slate on light, soft white on dark. Never white-on-white.
"""

FONT_PRIMARY = "'Segoe UI', 'Inter', system-ui, sans-serif"

# Shared accent
INDIGO = "#4F46E5"
INDIGO_HOVER = "#4338CA"
INDIGO_SOFT = "#EEF2FF"
SIDEBAR_BG = "#0C1326"
SIDEBAR_BG2 = "#111C34"


def _common() -> str:
    return f"""
    * {{
        font-family: {FONT_PRIMARY};
        font-size: 13px;
    }}
    QToolTip {{
        background-color: #111827;
        color: #F9FAFB;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
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
        border-radius: 12px;
        padding: 14px;
    }}
    QFrame#StatCard {{
        border-radius: 12px;
        padding: 12px;
    }}
    """


def _sidebar_qss() -> str:
    # Sidebar is identical in both themes: dark navy, always readable.
    return f"""
    QWidget#Sidebar {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid #1E2A44;
    }}
    QLabel#SidebarBrand {{
        color: #FFFFFF;
        font-size: 14.5px;
        font-weight: 800;
        letter-spacing: -0.2px;
        padding: 0px;
        background: transparent;
        border: none;
    }}
    QLabel#SidebarSub {{
        color: #7C8DB0;
        font-size: 11px;
        font-weight: 600;
        padding: 0px;
        background: transparent;
        border: none;
    }}
    QLabel#SidebarSection {{
        color: #64748B;
        font-size: 10.5px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 10px 12px 4px 12px;
        background: transparent;
        border: none;
    }}
    QWidget#Sidebar QPushButton {{
        text-align: left;
        padding: 10px 12px;
        border: none;
        border-radius: 10px;
        color: #A9B7D0;
        font-size: 13px;
        font-weight: 600;
        margin: 2px 8px;
        min-height: 36px;
        background: transparent;
    }}
    QWidget#Sidebar QPushButton:hover {{
        background-color: #1A2540;
        color: #FFFFFF;
    }}
    QWidget#Sidebar QPushButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {INDIGO}, stop:1 #7C3AED);
        color: #FFFFFF;
        font-weight: 700;
    }}
    QLabel#SidebarFoot {{
        color: #5B6B8C;
        font-size: 10px;
        padding: 10px 12px;
        background: transparent;
        border: none;
    }}
    """


def _light_qss() -> str:
    return _common() + _sidebar_qss() + f"""
    QMainWindow, QWidget#AppRoot {{
        background-color: #EDF1F7;
    }}
    QWidget#ContentArea {{
        background-color: #EDF1F7;
    }}
    /* Header */
    QWidget#Header {{
        background-color: #FFFFFF;
        border-bottom: 1px solid #E2E8F0;
    }}
    QLabel#HeaderTitle {{
        font-size: 17px;
        font-weight: 800;
        color: #0F172A;
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
        color: #0F172A;
    }}
    QLabel#PageTitle {{ color: #0F172A; background: transparent; }}
    QLabel#PageSubtitle {{ color: #64748B; background: transparent; }}
    QLabel#SectionTitle {{ color: #1E293B; background: transparent; }}
    QLabel#StatValue {{ color: #0F172A; background: transparent; }}
    QLabel#StatLabel {{ color: #64748B; background: transparent; }}
    QFrame#ContentCard {{
        background-color: #FFFFFF;
        border: 1px solid #DCE4EF;
    }}
    QFrame#StatCard {{
        background-color: #FFFFFF;
        border: 1px solid #DCE4EF;
    }}
    QFrame#Card {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 14px;
    }}
    /* Buttons */
    QPushButton {{
        min-height: 34px;
        border-radius: 8px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton#PrimaryButton {{
        background-color: {INDIGO};
        border: 1px solid {INDIGO_HOVER};
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
        background-color: #DC2626;
        border: 1px solid #B91C1C;
        color: #FFFFFF;
    }}
    QPushButton#DangerButton:hover {{ background-color: #B91C1C; }}
    /* Tables */
    QTableWidget {{
        background-color: #FFFFFF;
        alternate-background-color: #F8FAFC;
        gridline-color: #E2E8F0;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        selection-background-color: #E0E7FF;
        selection-color: #1E1B4B;
        color: #0F172A;
        font-size: 13px;
    }}
    QTableWidget::item {{
        padding: 9px 8px;
        color: #0F172A;
        border-bottom: 1px solid #F1F5F9;
    }}
    QTableWidget::item:selected {{
        background-color: #E0E7FF;
        color: #1E1B4B;
        font-weight: 600;
    }}
    QHeaderView::section {{
        background-color: #F1F5F9;
        color: #475569;
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid #E2E8F0;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.6px;
    }}
    QTableCornerButton::section {{
        background-color: #F1F5F9;
        border: none;
    }}
    /* Inputs */
    QLineEdit, QComboBox, QSpinBox, QTimeEdit, QTextEdit {{
        background-color: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        color: #0F172A;
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
        color: #0F172A;
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
        color: #0F172A;
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
        color: #0F172A;
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
