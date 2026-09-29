"""Fluent dark-first theme + light companion for College Timetable Manager.

Centralized QSS: views use object names + dynamic properties only,
no per-widget random stylesheets.

Dark (default):  bg #0B0F14 / surface #11161D / secondary #171D26 /
                 border #27313D / text #F4F7FA / muted #9AA6B2
Light (photos):  bg #FAF9F6 / surface #FFFFFF / secondary #F3F1EA /
                 border #DEDCD3 / text #111110 / muted #6B7280
Accents:         blue #5B8CFF / green #32D583 / amber #F5B942 / red #F04438
"""

FONT_UI = "'Segoe UI', 'Inter', system-ui, sans-serif"
FONT_MONO = "'Cascadia Code', 'JetBrains Mono', Consolas, monospace"


def _common() -> str:
    return f"""
    * {{
        font-family: {FONT_UI};
        font-size: 13px;
    }}
    QLabel#PageTitle {{
        font-size: 24px;
        font-weight: 700;
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
        font-family: {FONT_MONO};
        font-size: 24px;
        font-weight: 600;
    }}
    QLabel#StatLabel {{
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#Muted {{
        font-size: 12px;
    }}
    QLabel#Mono {{
        font-family: {FONT_MONO};
        font-size: 12px;
    }}
    QLabel#EmptyState {{
        font-size: 13px;
        font-weight: 500;
        padding: 18px;
        qproperty-alignment: AlignCenter;
    }}
    QToolTip {{
        padding: 6px 10px;
        font-size: 12px;
    }}
    QScrollArea#PageScroll {{
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        border-radius: 5px;
        min-height: 32px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        border-radius: 5px;
        min-width: 32px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    """


def _sidebar() -> str:
    return """
    QLabel#SidebarBrand {
        font-size: 15px;
        font-weight: 700;
        background: transparent;
        border: none;
    }
    QLabel#SidebarSub {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        background: transparent;
        border: none;
    }
    QLabel#SidebarSection {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 12px 14px 4px 14px;
        background: transparent;
        border: none;
    }
    QWidget#Sidebar QPushButton#NavButton {
        text-align: left;
        padding: 0px 12px;
        border: none;
        border-left: 3px solid transparent;
        border-radius: 0px;
        font-size: 13px;
        font-weight: 500;
        margin: 1px 8px 1px 0px;
        min-height: 40px;
        background: transparent;
    }
    QWidget#Sidebar QPushButton#NavButton:hover {
        background-color: rgba(255, 255, 255, 0.06);
    }
    QWidget#Sidebar QPushButton#NavButton:checked {
        font-weight: 700;
        border-left: 3px solid #5B8CFF;
    }
    QLabel#SidebarFoot {
        font-family: %s;
        font-size: 10px;
        padding: 10px 14px;
        background: transparent;
        border: none;
    }
    """ % FONT_MONO


def _dark() -> str:
    return _common() + _sidebar() + """
    QMainWindow, QWidget#AppRoot { background-color: #0B0F14; }
    QWidget#ContentArea { background-color: #0B0F14; }
    QWidget#Header {
        background-color: #11161D;
        border-bottom: 1px solid #27313D;
    }
    QWidget#Sidebar {
        background-color: #11161D;
        border-right: 1px solid #27313D;
    }
    QLabel#SidebarBrand { color: #F4F7FA; }
    QLabel#SidebarSub { color: #9AA6B2; }
    QLabel#SidebarSection { color: #5F6E7E; }
    QWidget#Sidebar QPushButton#NavButton { color: #9AA6B2; }
    QWidget#Sidebar QPushButton#NavButton:hover { color: #F4F7FA; }
    QWidget#Sidebar QPushButton#NavButton:checked {
        color: #F4F7FA;
        background-color: rgba(91, 140, 255, 0.12);
    }
    QLabel#SidebarFoot { color: #5F6E7E; }
    QScrollArea#PageScroll { background: #0B0F14; }
    QScrollArea#PageScroll > QWidget > QWidget { background: #0B0F14; }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #2E3947; }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #3D4A5C; }
    QLabel#HeaderTitle { font-size: 17px; font-weight: 700; color: #F4F7FA; background: transparent; }
    QLabel#HeaderSub { font-size: 12px; color: #9AA6B2; background: transparent; }
    QLabel#StatusPill {
        color: #32D583; font-weight: 700; font-size: 11.5px;
        background: rgba(50, 213, 131, 0.12);
        border: 1px solid rgba(50, 213, 131, 0.35);
        border-radius: 14px; padding: 5px 12px;
    }
    QPushButton#IconButton {
        background: #171D26; border: 1px solid #27313D; border-radius: 6px;
        color: #F4F7FA; font-size: 15px; min-height: 32px; min-width: 32px;
    }
    QPushButton#IconButton:hover { background: #1F2733; border-color: #3A4654; }
    QLabel#PageTitle { color: #F4F7FA; background: transparent; }
    QLabel#PageSubtitle { color: #9AA6B2; background: transparent; }
    QLabel#SectionTitle { color: #F4F7FA; background: transparent; }
    QLabel#StatValue { color: #F4F7FA; background: transparent; }
    QLabel#StatLabel { color: #9AA6B2; background: transparent; }
    QLabel#Muted { color: #9AA6B2; background: transparent; }
    QLabel#Mono { color: #C7D2DE; background: transparent; }
    QLabel#EmptyState {
        color: #9AA6B2; background: transparent;
        border: 1px dashed #27313D; border-radius: 8px;
    }
    QLabel { color: #F4F7FA; }
    QFrame#Card {
        background-color: #11161D; border: 1px solid #27313D;
        border-radius: 8px; padding: 16px;
    }
    QFrame#StatCard {
        background-color: #11161D; border: 1px solid #27313D;
        border-radius: 8px; padding: 14px;
    }
    QLabel#BadgeIndigo, QLabel#BadgeGreen, QLabel#BadgeAmber, QLabel#BadgeRose {
        font-size: 17px; font-weight: 700; border: none; border-radius: 6px;
    }
    QLabel#BadgeIndigo { background: rgba(91, 140, 255, 0.16); color: #8FB0FF; }
    QLabel#BadgeGreen { background: rgba(50, 213, 131, 0.14); color: #32D583; }
    QLabel#BadgeAmber { background: rgba(245, 185, 66, 0.16); color: #F5B942; }
    QLabel#BadgeRose { background: rgba(240, 68, 56, 0.14); color: #F0665E; }
    QPushButton {
        min-height: 32px; border-radius: 6px; padding: 6px 14px;
        font-weight: 600; font-size: 13px;
    }
    QPushButton#PrimaryButton {
        background-color: #5B8CFF; border: none; color: #FFFFFF; min-height: 36px;
    }
    QPushButton#PrimaryButton:hover { background-color: #4A7BE8; }
    QPushButton#PrimaryButton:pressed { background-color: #3D6BD1; }
    QPushButton#PrimaryButton:disabled { background-color: #2A3442; color: #5F6E7E; }
    QPushButton#SecondaryButton {
        background-color: #171D26; border: 1px solid #27313D; color: #F4F7FA;
    }
    QPushButton#SecondaryButton:hover { background-color: #1F2733; border-color: #3A4654; }
    QPushButton#DangerButton { background-color: #F04438; border: none; color: #FFFFFF; }
    QPushButton#DangerButton:hover { background-color: #D63A30; }
    QPushButton#RowButton {
        background: transparent; border: none; border-radius: 6px;
        color: #9AA6B2; min-height: 28px; min-width: 28px; padding: 4px;
    }
    QPushButton#RowButton:hover { background: rgba(255, 255, 255, 0.08); color: #F4F7FA; }
    QPushButton#RowButtonDanger {
        background: transparent; border: none; border-radius: 6px;
        color: #F0665E; min-height: 28px; min-width: 28px; padding: 4px;
    }
    QPushButton#RowButtonDanger:hover { background: rgba(240, 68, 56, 0.14); }
    QLineEdit, QComboBox, QSpinBox, QTimeEdit, QTextEdit {
        background-color: #0B0F14; border: 1px solid #27313D; border-radius: 6px;
        padding: 8px 12px; font-size: 13px; color: #F4F7FA;
        selection-background-color: #5B8CFF; selection-color: #FFFFFF;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QTextEdit:focus {
        border: 1px solid #5B8CFF;
    }
    QLineEdit::placeholder { color: #5F6E7E; }
    QComboBox::drop-down { border: none; width: 26px; }
    QComboBox::down-arrow {
        image: none; border-left: 5px solid transparent;
        border-right: 5px solid transparent; border-top: 6px solid #9AA6B2; margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        background-color: #171D26; color: #F4F7FA;
        selection-background-color: rgba(91, 140, 255, 0.25);
        selection-color: #FFFFFF; border: 1px solid #27313D; padding: 4px; outline: none;
    }
    QTableWidget {
        background-color: transparent; alternate-background-color: rgba(255, 255, 255, 0.02);
        gridline-color: #1E2631; border: none; border-radius: 0px;
        selection-background-color: rgba(91, 140, 255, 0.18);
        selection-color: #F4F7FA; color: #F4F7FA; font-size: 13px; outline: none;
    }
    QTableWidget::item { padding: 10px 8px; border-bottom: 1px solid #1E2631; }
    QTableWidget::item:selected { background-color: rgba(91, 140, 255, 0.18); }
    QHeaderView::section {
        background-color: transparent; color: #9AA6B2; padding: 8px;
        border: none; border-bottom: 1px solid #27313D;
        font-weight: 700; font-size: 11px;
    }
    QTableCornerButton::section { background-color: transparent; border: none; }
    QGroupBox {
        background-color: #11161D; border: 1px solid #27313D; border-radius: 8px;
        margin-top: 14px; padding: 16px; padding-top: 20px;
        font-weight: 700; font-size: 13px; color: #F4F7FA;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 14px; padding: 2px 10px;
        color: #9AA6B2; font-size: 11px; font-weight: 700;
    }
    QProgressBar {
        border: none; border-radius: 4px; text-align: center;
        background-color: #1E2631; height: 16px; color: #F4F7FA;
        font-weight: 700; font-size: 10px;
    }
    QProgressBar::chunk { background-color: #5B8CFF; border-radius: 4px; }
    QTabWidget::pane { border: 1px solid #27313D; background: #11161D; border-radius: 8px; top: -1px; }
    QTabBar::tab {
        padding: 8px 16px; background: transparent; border: none;
        border-bottom: 2px solid transparent; margin-right: 4px;
        color: #9AA6B2; font-weight: 600;
    }
    QTabBar::tab:selected { color: #F4F7FA; border-bottom: 2px solid #5B8CFF; }
    QDialog { background-color: #11161D; border: 1px solid #27313D; }
    QDialog QLabel { color: #F4F7FA; }
    QMessageBox { background-color: #11161D; }
    QMessageBox QLabel { color: #F4F7FA; font-size: 13px; }
    QMessageBox QPushButton { min-width: 86px; }
    QCheckBox { color: #F4F7FA; spacing: 8px; background: transparent; }
    QCheckBox::indicator {
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid #3A4654; background: #0B0F14;
    }
    QCheckBox::indicator:checked { background: #5B8CFF; border-color: #5B8CFF; }
    QCheckBox#Switch { background: transparent; spacing: 0px; }
    QCheckBox#Switch::indicator { width: 0px; height: 0px; border: none; background: transparent; }
    QToolTip { background-color: #1F2733; color: #F4F7FA; border: 1px solid #3A4654; border-radius: 6px; }
    /* Banners */
    QLabel#HelpBody {
        font-size: 12.5px; padding: 2px 0;
        color: #C7D2DE; background: transparent; border: none;
    }
    QLabel#BannerOk {
        color: #32D583; font-weight: 600; font-size: 12.5px;
        background: rgba(50, 213, 131, 0.08);
        border: 1px solid rgba(50, 213, 131, 0.30); border-radius: 8px; padding: 12px;
    }
    QLabel#BannerErr {
        color: #F0665E; font-weight: 600; font-size: 12.5px;
        background: rgba(240, 68, 56, 0.08);
        border: 1px solid rgba(240, 68, 56, 0.35); border-radius: 8px; padding: 12px;
    }
    QLabel#InfoBar {
        color: #9AA6B2; font-size: 11.5px;
        background: #11161D; border: 1px solid #27313D; border-radius: 8px; padding: 10px;
    }
    QLabel#FormatPreview {
        color: #9AA6B2; font-size: 12px; background: #11161D;
        border: 1px dashed #27313D; border-radius: 8px; padding: 6px;
        qproperty-alignment: AlignCenter;
    }
    /* Timetable */
    QFrame#TimetableGrid {
        background: #11161D; border: 1px solid #27313D; border-radius: 8px;
    }
    QLabel#GridCorner, QLabel#GridHead {
        color: #9AA6B2; background: #171D26;
        border: 1px solid #1E2631; border-radius: 4px; padding: 8px 4px;
        font-size: 11px; font-weight: 700;
    }
    QLabel#GridTime {
        font-family: %s; color: #F4F7FA; background: #171D26;
        border: 1px solid #1E2631; border-radius: 4px; padding: 8px 4px;
        font-size: 11px; font-weight: 500;
    }
    QLabel#BreakCell {
        font-family: %s; color: #5F6E7E; background: #141A23;
        border: 1px solid #1E2631; border-radius: 4px; padding: 8px 4px;
        font-size: 10px; font-weight: 600;
    }
    QFrame#DropZone {
        border: 1px solid #1E2631; border-radius: 6px; background: transparent;
    }
    QFrame#DropZone:hover { border: 1px solid #3A4654; background: rgba(91, 140, 255, 0.06); }
    QFrame#DropZone[state="drop"] { border: 2px solid #5B8CFF; background: rgba(91, 140, 255, 0.10); }
    QFrame#DropZone[state="ok"] { border: 2px solid #32D583; background: rgba(50, 213, 131, 0.10); }
    QFrame#DropZone[state="bad"] { border: 2px solid #F04438; background: rgba(240, 68, 56, 0.10); }
    QFrame#LectureCard {
        background: #1A2230; border: 1px solid #27313D;
        border-left: 4px solid #5B8CFF; border-radius: 8px; padding: 6px;
    }
    QFrame#LectureCard:hover { border: 1px solid #3A4654; border-left: 4px solid #5B8CFF; }
    QFrame#LectureCard[ltype="Practical"] { border-left-color: #9D7BFF; }
    QFrame#LectureCard[ltype="Lab"] { border-left-color: #F5B942; }
    QFrame#LectureCard[ltype="Tutorial"] { border-left-color: #32D583; }
    QFrame#LectureCard[conflict="true"] {
        border: 1px solid #F04438; border-left: 4px solid #F04438;
        background: rgba(240, 68, 56, 0.10);
    }
    QFrame#LectureCard[selected="true"] { border: 1px solid #5B8CFF; }
    QLabel#CardCode { font-family: %s; font-size: 12px; font-weight: 700; color: #F4F7FA; background: transparent; border: none; }
    QLabel#CardTitle { font-size: 11.5px; font-weight: 600; color: #C7D2DE; background: transparent; border: none; }
    QLabel#CardMeta { font-size: 10.5px; color: #9AA6B2; background: transparent; border: none; }
    QLabel#CardTime { font-family: %s; font-size: 10.5px; color: #9AA6B2; background: transparent; border: none; }
    /* Semester cards */
    QFrame#SemCard { background: #11161D; border: 1px solid #27313D; border-top: 4px solid #5B8CFF; border-radius: 8px; }
    QFrame#SemCard:hover { border: 1px solid #3A4654; border-top: 4px solid #5B8CFF; background: #141B25; }
    QFrame#SemCard[tone="green"] { border-top-color: #32D583; }
    QFrame#SemCard[tone="amber"] { border-top-color: #F5B942; }
    QFrame#SemCard[tone="red"] { border-top-color: #F04438; }
    QFrame#SemCard[tone="violet"] { border-top-color: #9D7BFF; }
    QLabel#SemTitle { font-size: 16px; font-weight: 700; color: #F4F7FA; background: transparent; border: none; }
    QLabel#SemSub { font-size: 11px; color: #9AA6B2; background: transparent; border: none; }
    QLabel#SemDetail { font-size: 11px; color: #C7D2DE; background: transparent; border: none; }
    QLabel#SemHint { font-size: 11px; color: #5B8CFF; font-weight: 700; background: transparent; border: none; }
    """ % (FONT_MONO, FONT_MONO, FONT_MONO, FONT_MONO)


def _light() -> str:
    return _common() + _sidebar() + """
    QMainWindow, QWidget#AppRoot { background-color: #FAF9F6; }
    QWidget#ContentArea { background-color: #FAF9F6; }
    QWidget#Header { background-color: #FFFFFF; border-bottom: 1px solid #DEDCD3; }
    QWidget#Sidebar { background-color: #1C355E; border-right: 1px solid #16294A; }
    QLabel#SidebarBrand { color: #FFFFFF; }
    QLabel#SidebarSub { color: rgba(255, 255, 255, 0.6); }
    QLabel#SidebarSection { color: rgba(255, 255, 255, 0.5); }
    QWidget#Sidebar QPushButton#NavButton { color: rgba(255, 255, 255, 0.75); }
    QWidget#Sidebar QPushButton#NavButton:hover { color: #FFFFFF; background-color: rgba(255, 255, 255, 0.10); }
    QWidget#Sidebar QPushButton#NavButton:checked {
        color: #1C355E; background-color: #FFFFFF; border-left: 3px solid #1C355E;
    }
    QLabel#SidebarFoot { color: rgba(255, 255, 255, 0.6); }
    QScrollArea#PageScroll { background: #FAF9F6; }
    QScrollArea#PageScroll > QWidget > QWidget { background: #FAF9F6; }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #C3CAD6; }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #9AA5B8; }
    QLabel#HeaderTitle { font-size: 17px; font-weight: 700; color: #111110; background: transparent; }
    QLabel#HeaderSub { font-size: 12px; color: #6B7280; background: transparent; }
    QLabel#StatusPill {
        color: #166534; font-weight: 700; font-size: 11.5px;
        background: #DCFCE7; border: 1px solid #BBF7D0;
        border-radius: 14px; padding: 5px 12px;
    }
    QPushButton#IconButton {
        background: #F1F5F9; border: 1px solid #DEDCD3; border-radius: 6px;
        color: #334155; font-size: 15px; min-height: 32px; min-width: 32px;
    }
    QPushButton#IconButton:hover { background: #E8EDF3; }
    QLabel#PageTitle { color: #111110; background: transparent; }
    QLabel#PageSubtitle { color: #6B7280; background: transparent; }
    QLabel#SectionTitle { color: #111110; background: transparent; }
    QLabel#StatValue { color: #111110; background: transparent; }
    QLabel#StatLabel { color: #6B7280; background: transparent; }
    QLabel#Muted { color: #6B7280; background: transparent; }
    QLabel#Mono { font-family: %s; font-size: 12px; color: #374151; background: transparent; }
    QLabel#EmptyState {
        color: #6B7280; background: transparent;
        border: 1px dashed #DEDCD3; border-radius: 8px;
    }
    QLabel { color: #1E293B; }
    QFrame#Card {
        background-color: #FFFFFF; border: 1px solid #DEDCD3;
        border-radius: 8px; padding: 16px;
    }
    QFrame#StatCard {
        background-color: #FFFFFF; border: 1px solid #DEDCD3;
        border-radius: 8px; padding: 14px;
    }
    QLabel#BadgeIndigo, QLabel#BadgeGreen, QLabel#BadgeAmber, QLabel#BadgeRose {
        font-size: 17px; font-weight: 700; border: none; border-radius: 6px;
    }
    QLabel#BadgeIndigo { background: #E0E7FF; color: #3730A3; }
    QLabel#BadgeGreen { background: #D1FAE5; color: #065F46; }
    QLabel#BadgeAmber { background: #FEF3C7; color: #92400E; }
    QLabel#BadgeRose { background: #FFE4E6; color: #9F1239; }
    QPushButton {
        min-height: 32px; border-radius: 6px; padding: 6px 14px;
        font-weight: 600; font-size: 13px;
    }
    QPushButton#PrimaryButton {
        background-color: #1C355E; border: none; color: #FFFFFF; min-height: 36px;
    }
    QPushButton#PrimaryButton:hover { background-color: #16294A; }
    QPushButton#PrimaryButton:pressed { background-color: #16294A; }
    QPushButton#SecondaryButton {
        background-color: #FFFFFF; border: 1px solid #DEDCD3; color: #111110;
    }
    QPushButton#SecondaryButton:hover { background-color: #F5F5F5; }
    QPushButton#DangerButton { background-color: #9A2C2C; border: none; color: #FFFFFF; }
    QPushButton#DangerButton:hover { background-color: #7C2323; }
    QPushButton#RowButton {
        background: transparent; border: none; border-radius: 6px;
        color: #4B5563; min-height: 28px; min-width: 28px; padding: 4px;
    }
    QPushButton#RowButton:hover { background: #F1F5F9; color: #111110; }
    QPushButton#RowButtonDanger {
        background: transparent; border: none; border-radius: 6px;
        color: #9A2C2C; min-height: 28px; min-width: 28px; padding: 4px;
    }
    QPushButton#RowButtonDanger:hover { background: #FEE2E2; }
    QLineEdit, QComboBox, QSpinBox, QTimeEdit, QTextEdit {
        background-color: #FFFFFF; border: 1px solid #DEDCD3; border-radius: 6px;
        padding: 8px 12px; font-size: 13px; color: #111110;
        selection-background-color: #1C355E; selection-color: #FFFFFF;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus, QTextEdit:focus {
        border: 1px solid #1C355E;
    }
    QLineEdit::placeholder { color: #9CA3AF; }
    QComboBox::drop-down { border: none; width: 26px; }
    QComboBox::down-arrow {
        image: none; border-left: 5px solid transparent;
        border-right: 5px solid transparent; border-top: 6px solid #6B7280; margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF; color: #111110;
        selection-background-color: #EAEFF5; selection-color: #1C355E;
        border: 1px solid #DEDCD3; padding: 4px; outline: none;
    }
    QTableWidget {
        background-color: transparent; alternate-background-color: #FAF9F6;
        gridline-color: #EDEBE3; border: none; border-radius: 0px;
        selection-background-color: #EAEFF5;
        selection-color: #1C355E; color: #111110; font-size: 13px; outline: none;
    }
    QTableWidget::item { padding: 10px 8px; border-bottom: 1px solid #EDEBE3; }
    QTableWidget::item:selected { background-color: #EAEFF5; color: #1C355E; font-weight: 600; }
    QHeaderView::section {
        background-color: #F3F1EA; color: #57534E; padding: 8px;
        border: none; font-weight: 700; font-size: 11px;
    }
    QTableCornerButton::section { background-color: #F3F1EA; border: none; }
    QGroupBox {
        background-color: #FFFFFF; border: 1px solid #DEDCD3; border-radius: 8px;
        margin-top: 14px; padding: 16px; padding-top: 20px;
        font-weight: 700; font-size: 13px; color: #111110;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 14px; padding: 2px 10px;
        color: #6B7280; font-size: 11px; font-weight: 700;
    }
    QProgressBar {
        border: none; border-radius: 4px; text-align: center;
        background-color: #EDEBE3; height: 16px; color: #111110;
        font-weight: 700; font-size: 10px;
    }
    QProgressBar::chunk { background-color: #1C355E; border-radius: 4px; }
    QTabWidget::pane { border: 1px solid #DEDCD3; background: #FFFFFF; border-radius: 8px; top: -1px; }
    QTabBar::tab {
        padding: 8px 16px; background: transparent; border: none;
        border-bottom: 2px solid transparent; margin-right: 4px;
        color: #6B7280; font-weight: 600;
    }
    QTabBar::tab:selected { color: #111110; border-bottom: 2px solid #1C355E; }
    QDialog { background-color: #FFFFFF; border: 1px solid #DEDCD3; }
    QDialog QLabel { color: #1E293B; }
    QMessageBox { background-color: #FFFFFF; }
    QMessageBox QLabel { color: #111110; font-size: 13px; }
    QMessageBox QPushButton { min-width: 86px; }
    QCheckBox { color: #1E293B; spacing: 8px; background: transparent; }
    QCheckBox::indicator {
        width: 16px; height: 16px; border-radius: 4px;
        border: 1px solid #CBD5E1; background: #FFFFFF;
    }
    QCheckBox::indicator:checked { background: #1C355E; border-color: #1C355E; }
    QCheckBox#Switch { background: transparent; spacing: 0px; }
    QCheckBox#Switch::indicator { width: 0px; height: 0px; border: none; background: transparent; }
    QToolTip { background-color: #111827; color: #F9FAFB; border: 1px solid #374151; border-radius: 6px; }
    QLabel#HelpBody {
        font-size: 12.5px; padding: 2px 0;
        color: #374151; background: transparent; border: none;
    }
    QLabel#BannerOk {
        color: #065F46; font-weight: 600; font-size: 12.5px;
        background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 12px;
    }
    QLabel#BannerErr {
        color: #991B1B; font-weight: 600; font-size: 12.5px;
        background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 12px;
    }
    QLabel#InfoBar {
        color: #6B7280; font-size: 11.5px;
        background: #F8FAFC; border: 1px solid #DEDCD3; border-radius: 8px; padding: 10px;
    }
    QLabel#FormatPreview {
        color: #6B7280; font-size: 12px; background: #F8FAFC;
        border: 1px dashed #DEDCD3; border-radius: 8px; padding: 6px;
        qproperty-alignment: AlignCenter;
    }
    QFrame#TimetableGrid { background: #FFFFFF; border: 1px solid #DEDCD3; border-radius: 8px; }
    QLabel#GridCorner, QLabel#GridHead {
        color: #57534E; background: #F3F1EA;
        border: 1px solid #DEDCD3; border-radius: 4px; padding: 8px 4px;
        font-size: 11px; font-weight: 700;
    }
    QLabel#GridTime {
        font-family: %s; color: #111110; background: #FFFFFF;
        border: 1px solid #DEDCD3; border-radius: 4px; padding: 8px 4px;
        font-size: 11px; font-weight: 500;
    }
    QLabel#BreakCell {
        font-family: %s; color: #78716C; background: #F5F5F4;
        border: 1px solid #DEDCD3; border-radius: 4px; padding: 8px 4px;
        font-size: 10px; font-weight: 600;
    }
    QFrame#DropZone { border: 1px solid #EDEBE3; border-radius: 6px; background: transparent; }
    QFrame#DropZone:hover { border: 1px solid #CBD5E1; background: #FAF9F6; }
    QFrame#DropZone[state="drop"] { border: 2px solid #1C355E; background: #EAEFF5; }
    QFrame#DropZone[state="ok"] { border: 2px solid #059669; background: #ECFDF5; }
    QFrame#DropZone[state="bad"] { border: 2px solid #9A2C2C; background: #FEF2F2; }
    QFrame#LectureCard {
        background: #F4F7FB; border: 1px solid #DEDCD3;
        border-left: 4px solid #1C355E; border-radius: 8px; padding: 6px;
    }
    QFrame#LectureCard:hover { border: 1px solid #C3CAD6; border-left: 4px solid #1C355E; }
    QFrame#LectureCard[ltype="Practical"] { border-left-color: #6D28D9; }
    QFrame#LectureCard[ltype="Lab"] { border-left-color: #D97706; }
    QFrame#LectureCard[ltype="Tutorial"] { border-left-color: #059669; }
    QFrame#LectureCard[conflict="true"] {
        border: 1px solid #9A2C2C; border-left: 4px solid #9A2C2C; background: #FEF2F2;
    }
    QFrame#LectureCard[selected="true"] { border: 1px solid #1C355E; }
    QLabel#CardCode { font-family: %s; font-size: 12px; font-weight: 700; color: #111110; background: transparent; border: none; }
    QLabel#CardTitle { font-size: 11.5px; font-weight: 600; color: #374151; background: transparent; border: none; }
    QLabel#CardMeta { font-size: 10.5px; color: #6B7280; background: transparent; border: none; }
    QLabel#CardTime { font-family: %s; font-size: 10.5px; color: #6B7280; background: transparent; border: none; }
    QFrame#SemCard { background: #FFFFFF; border: 1px solid #DEDCD3; border-top: 4px solid #1C355E; border-radius: 8px; }
    QFrame#SemCard:hover { border: 1px solid #C3CAD6; border-top: 4px solid #1C355E; background: #FAF9F6; }
    QFrame#SemCard[tone="green"] { border-top-color: #059669; }
    QFrame#SemCard[tone="amber"] { border-top-color: #D97706; }
    QFrame#SemCard[tone="red"] { border-top-color: #9A2C2C; }
    QFrame#SemCard[tone="violet"] { border-top-color: #6D28D9; }
    QLabel#SemTitle { font-size: 16px; font-weight: 700; color: #111110; background: transparent; border: none; }
    QLabel#SemSub { font-size: 11px; color: #6B7280; background: transparent; border: none; }
    QLabel#SemDetail { font-size: 11px; color: #374151; background: transparent; border: none; }
    QLabel#SemHint { font-size: 11px; color: #1C355E; font-weight: 700; background: transparent; border: none; }
    """ % (FONT_MONO, FONT_MONO, FONT_MONO, FONT_MONO, FONT_MONO)


def get_theme_qss(theme: str) -> str:
    """Return the application stylesheet. Unknown values fall back to dark."""
    if theme == "light":
        return _light()
    return _dark()
