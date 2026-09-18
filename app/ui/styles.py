APP_QSS = """
/* ===== MODERN LIGHT THEME ===== */
QMainWindow {
    background-color: #F1F5F9;
}
QWidget {
    color: #0F172A;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
QWidget#Sidebar {
    background-color: #0F172A;
    border: none;
}
QWidget#Sidebar QPushButton {
    text-align: left;
    padding: 9px 12px;
    border: none;
    border-radius: 8px;
    color: #94A3B8;
    font-size: 13px;
    font-weight: 500;
    margin: 1px 4px;
}
QWidget#Sidebar QPushButton:hover {
    background-color: #1E293B;
    color: #F1F5F9;
}
QWidget#Sidebar QPushButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}
QWidget#Header {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QLabel#HeaderTitle {
    font-size: 17px;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.3px;
}
QLabel#HeaderSub {
    font-size: 12px;
    color: #64748B;
    font-weight: 500;
}
/* Buttons - high contrast, not washed white */
QPushButton {
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton#PrimaryButton {
    background-color: #1E293B;
    color: #FFFFFF;
    border: 1px solid #0F172A;
    padding: 9px 18px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#PrimaryButton:hover {
    background-color: #0F172A;
    border: 1px solid #020617;
}
QPushButton#PrimaryButton:pressed {
    background-color: #020617;
}
QPushButton#PrimaryButton:disabled {
    background-color: #94A3B8;
    color: #F8FAFC;
    border: 1px solid #94A3B8;
}
QPushButton#PrimaryButton:focus {
    border: 1px solid #3B82F6;
}
QPushButton#SecondaryButton {
    background-color: #F8FAFC;
    color: #0F172A;
    border: 1.5px solid #CBD5E1;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#SecondaryButton:hover {
    background-color: #EFF6FF;
    border: 1.5px solid #93C5FD;
    color: #0F172A;
}
QPushButton#SecondaryButton:pressed {
    background-color: #DBEAFE;
    border: 1.5px solid #60A5FA;
}
QPushButton#SecondaryButton:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border: 1.5px solid #E2E8F0;
}
QPushButton#SecondaryButton:focus {
    border: 1.5px solid #2563EB;
}
QPushButton#DangerButton {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
    padding: 8px 16px;
    font-weight: 700;
}
QPushButton#DangerButton:hover {
    background-color: #B91C1C;
    border: 1px solid #991B1B;
}
QPushButton#DangerButton:pressed {
    background-color: #991B1B;
}
QPushButton#DangerButton:disabled {
    background-color: #FECACA;
    color: #7F1D1D;
    border: 1px solid #FECACA;
}
QPushButton#DangerButton:focus {
    border: 1px solid #F87171;
}
/* Tables - crisp, not washed */
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    gridline-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    selection-background-color: #EFF6FF;
    selection-color: #1E3A8A;
    color: #1E293B;
    font-size: 13px;
}
QTableWidget::item {
    padding: 10px 8px;
    color: #1E293B;
    border-bottom: 1px solid #F1F5F9;
}
QTableWidget::item:selected {
    background-color: #DBEAFE;
    color: #1E3A8A;
    font-weight: 600;
}
QHeaderView::section {
    background-color: #0F172A;
    color: #FFFFFF;
    padding: 10px 8px;
    border: none;
    border-right: 1px solid #1E293B;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QHeaderView::section:vertical {
    background-color: #F8FAFC;
    color: #64748B;
    border-right: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
    font-weight: 600;
    font-size: 11px;
}
QHeaderView::section:first {
    border-top-left-radius: 10px;
}
QHeaderView::section:last {
    border-top-right-radius: 10px;
    border-right: none;
}
QTableCornerButton::section {
    background-color: #0F172A;
    border: none;
    border-top-left-radius: 10px;
}
QLineEdit, QComboBox, QSpinBox, QTimeEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #0F172A;
    selection-background-color: #2563EB;
    selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus {
    border: 1.5px solid #2563EB;
    background-color: #FFFFFF;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QTimeEdit:hover {
    border: 1.5px solid #94A3B8;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748B;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #0F172A;
    selection-background-color: #EFF6FF;
    selection-color: #1E3A8A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
}
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px;
    padding-top: 20px;
    font-weight: 700;
    font-size: 13px;
    color: #0F172A;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 4px 10px;
    background-color: #0F172A;
    color: #FFFFFF;
    border-radius: 6px;
    font-size: 12px;
}
QProgressBar {
    border: none;
    border-radius: 8px;
    text-align: center;
    background-color: #E2E8F0;
    height: 20px;
    color: #0F172A;
    font-weight: 700;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #3B82F6);
    border-radius: 8px;
}
QLabel#Card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 14px;
    color: #0F172A;
}
QLabel#StatValue {
    font-size: 28px;
    font-weight: 900;
    color: #0F172A;
    letter-spacing: -0.5px;
}
QLabel#StatLabel {
    font-size: 11px;
    color: #64748B;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
QTabWidget::pane {
    border: 1px solid #CBD5E1;
    background: #FFFFFF;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    padding: 10px 18px;
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-bottom: 1px solid #CBD5E1;
    border-radius: 8px 8px 0 0;
    margin-right: 4px;
    color: #475569;
    font-weight: 600;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #0F172A;
    font-weight: 700;
    border-bottom: 1px solid #FFFFFF;
}
QTabBar::tab:!selected:hover {
    background: #E2E8F0;
    color: #1E293B;
}
QScrollBar:vertical {
    background: #F1F5F9;
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QToolTip {
    background-color: #0F172A;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* App shell refinements */
QMainWindow { background: #EEF2F6; }
QWidget#Sidebar { background: #132A3A; border-right: 1px solid #0D1F2B; }
QWidget#Sidebar QPushButton { min-height: 38px; padding: 9px 12px; border-radius: 6px; color: #AFC1CC; margin: 2px 3px; }
QWidget#Sidebar QPushButton:hover { background: #1E4154; color: #FFFFFF; }
QWidget#Sidebar QPushButton:checked { background: #1F8A70; color: #FFFFFF; border-left: 3px solid #F2B880; padding-left: 9px; }
QWidget#Header { background: #FFFFFF; border-bottom: 1px solid #D7E0E7; }
QLabel#HeaderTitle { font-size: 18px; font-weight: 800; color: #132A3A; }
QLabel#HeaderSub { color: #70808B; font-size: 12px; }
QPushButton { min-height: 34px; border-radius: 6px; padding: 7px 14px; }
QPushButton#PrimaryButton { background: #1F8A70; border: 1px solid #176B57; color: #FFFFFF; }
QPushButton#PrimaryButton:hover { background: #176B57; }
QPushButton#SecondaryButton { background: #FFFFFF; border: 1px solid #B8C7D0; color: #274554; }
QPushButton#SecondaryButton:hover { background: #E8F3F0; border-color: #6BB19D; }
QPushButton#DangerButton { background: #C94D4D; border: 1px solid #A53B3B; color: #FFFFFF; }
QPushButton#DangerButton:hover { background: #A53B3B; }
QTableWidget { border: 1px solid #D3DEE5; border-radius: 8px; background: #FFFFFF; alternate-background-color: #F7FAFB; selection-background-color: #D9EEE8; selection-color: #163D34; }
QHeaderView::section { background: #23485A; color: #FFFFFF; padding: 10px 8px; font-size: 11px; font-weight: 700; border: none; }
QGroupBox { border: 1px solid #D3DEE5; border-radius: 8px; background: #FFFFFF; padding: 18px 14px 14px; }
QGroupBox::title { background: #23485A; color: #FFFFFF; border-radius: 4px; padding: 4px 9px; left: 12px; }
QDialog { background: #F7FAFB; }
QDialog QLabel { color: #29424F; }
QDialogButtonBox QPushButton { min-width: 88px; }
QMessageBox { background: #FFFFFF; }
QMessageBox QLabel { color: #172F3D; font-size: 13px; }
QProgressBar::chunk { background: #1F8A70; }
QToolTip { background: #132A3A; color: #FFFFFF; border: 1px solid #416477; }
"""

# Dark theme - polished
DARK_QSS = """
QMainWindow {
    background-color: #020617;
}
QWidget {
    color: #E2E8F0;
    font-family: 'Segoe UI', sans-serif;
}
QWidget#Sidebar {
    background-color: #020617;
    border-right: 1px solid #1E293B;
}
QWidget#Sidebar QPushButton {
    text-align: left;
    padding: 9px 12px;
    border: none;
    border-radius: 8px;
    color: #64748B;
    font-size: 13px;
    font-weight: 500;
    margin: 1px 4px;
}
QWidget#Sidebar QPushButton:hover {
    background-color: #1E293B;
    color: #F1F5F9;
}
QWidget#Sidebar QPushButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}
QWidget#Header {
    background-color: #0F172A;
    border-bottom: 1px solid #1E293B;
}
QLabel#HeaderTitle {
    font-size: 17px;
    font-weight: 800;
    color: #F8FAFC;
}
QLabel#HeaderSub {
    font-size: 12px;
    color: #94A3B8;
}
QPushButton#PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    padding: 9px 18px;
    font-weight: 700;
}
QPushButton#PrimaryButton:hover {
    background-color: #1D4ED8;
}
QPushButton#SecondaryButton {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1.5px solid #334155;
    padding: 8px 16px;
}
QPushButton#SecondaryButton:hover {
    background-color: #334155;
    border: 1.5px solid #475569;
}
QPushButton#DangerButton {
    background-color: #1E293B;
    color: #FCA5A5;
    border: 1.5px solid #7F1D1D;
    padding: 7px 14px;
}
QPushButton#DangerButton:hover {
    background-color: #450A0A;
    color: #FEF2F2;
}
QTableWidget {
    background-color: #0F172A;
    alternate-background-color: #020617;
    gridline-color: #1E293B;
    border: 1px solid #1E293B;
    border-radius: 10px;
    selection-background-color: #1E3A8A;
    selection-color: #FFFFFF;
    color: #E2E8F0;
}
QTableWidget::item {
    padding: 10px 8px;
    color: #E2E8F0;
    border-bottom: 1px solid #1E293B;
}
QTableWidget::item:selected {
    background-color: #1E40AF;
    color: #FFFFFF;
}
QHeaderView::section {
    background-color: #020617;
    color: #94A3B8;
    padding: 10px 8px;
    border: none;
    border-right: 1px solid #1E293B;
    font-weight: 700;
    font-size: 11px;
}
QLineEdit, QComboBox, QSpinBox, QTimeEdit {
    background-color: #0F172A;
    border: 1.5px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F1F5F9;
    selection-background-color: #2563EB;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1.5px solid #3B82F6;
}
QComboBox QAbstractItemView {
    background-color: #0F172A;
    color: #F1F5F9;
    selection-background-color: #1E3A8A;
    border: 1px solid #334155;
}
QGroupBox {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px;
    padding-top: 20px;
    color: #F1F5F9;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 4px 10px;
    background-color: #2563EB;
    color: #FFFFFF;
    border-radius: 6px;
}
QProgressBar {
    border: none;
    background-color: #1E293B;
    border-radius: 8px;
    height: 20px;
    color: #E2E8F0;
}
QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 8px;
}
QLabel#Card {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 14px;
    color: #E2E8F0;
}
QLabel#StatValue {
    font-size: 28px;
    font-weight: 900;
    color: #F8FAFC;
}
QLabel#StatLabel {
    font-size: 11px;
    color: #64748B;
    font-weight: 700;
}
QTabWidget::pane {
    border: 1px solid #1E293B;
    background: #0F172A;
    border-radius: 10px;
}
QTabBar::tab {
    padding: 10px 18px;
    background: #020617;
    border: 1px solid #1E293B;
    color: #64748B;
    border-radius: 8px 8px 0 0;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #0F172A;
    color: #F1F5F9;
    font-weight: 700;
    border-bottom: 1px solid #0F172A;
}
"""

def get_theme_qss(theme: str) -> str:
    if theme == "dark":
        return DARK_QSS
    return APP_QSS
