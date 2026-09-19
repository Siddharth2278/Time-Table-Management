COLOR_BG_LIGHT = "#F8FAFC"
COLOR_BG_DARK = "#0F172A"
COLOR_SURFACE_LIGHT = "#FFFFFF"
COLOR_SURFACE_DARK = "#1E293B"
COLOR_PRIMARY = "#1E293B"
COLOR_PRIMARY_LIGHT = "#F1F5F9"
COLOR_ACCENT = "#3B82F6"
COLOR_ACCENT_HOVER = "#2563EB"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_ERROR = "#EF4444"
COLOR_INFO = "#64748B"
COLOR_TEXT_LIGHT = "#0F172A"
COLOR_TEXT_DARK = "#E2E8F0"
COLOR_TEXT_MUTED = "#94A3B8"
COLOR_BORDER_LIGHT = "#CBD5E1"
COLOR_BORDER_DARK = "#334155"
COLOR_RISK = "#DC2626"
COLOR_CARD_LIGHT = "#FFFFFF"
COLOR_CARD_DARK = "#1E293B"
COLOR_GRID_LIGHT = "#E2E8F0"
COLOR_GRID_DARK = "#1E293B"

FONT_PRIMARY = "'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif"
FONT_SIZE = 13
FONT_SIZE_SMALL = 11
FONT_SIZE_LARGE = 18
FONT_WEIGHT_NORMAL = 500
FONT_WEIGHT_MEDIUM = 600
FONT_WEIGHT_BOLD = 700
FONT_WEIGHT_EXTRA_BOLD = 800

def _base_widget_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QWidget {{
            color: {COLOR_TEXT_DARK};
            font-family: {FONT_PRIMARY};
            font-size: {FONT_SIZE}px;
        }}
        """
    return f"""
        QWidget {{
            color: {COLOR_TEXT_LIGHT};
            font-family: {FONT_PRIMARY};
            font-size: {FONT_SIZE}px;
        }}
        """

def _sidebar_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QWidget#Sidebar {{
            background-color: {COLOR_SURFACE_DARK};
            border-right: 1px solid {COLOR_BORDER_DARK};
        }}
        QWidget#Sidebar QPushButton {{
            text-align: left;
            padding: 9px 12px;
            border: none;
            border-radius: 8px;
            color: {COLOR_TEXT_MUTED};
            font-size: {FONT_SIZE}px;
            font-weight: {FONT_WEIGHT_MEDIUM};
            margin: 1px 4px;
            min-height: 38px;
        }}
        QWidget#Sidebar QPushButton:hover {{
            background-color: #334155;
            color: {COLOR_TEXT_DARK};
        }}
        QWidget#Sidebar QPushButton:checked {{
            background-color: {COLOR_ACCENT};
            color: #FFFFFF;
            font-weight: {FONT_WEIGHT_BOLD};
            border-left: 3px solid {COLOR_ACCENT};
        }}
        QWidget#Sidebar QLabel {{
            color: {COLOR_TEXT_MUTED};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 4px 8px;
        }}
        """
    return f"""
        QWidget#Sidebar {{
            background-color: {COLOR_SURFACE_LIGHT};
            border-right: 1px solid {COLOR_BORDER_LIGHT};
        }}
        QWidget#Sidebar QPushButton {{
            text-align: left;
            padding: 9px 12px;
            border: none;
            border-radius: 8px;
            color: {COLOR_TEXT_MUTED};
            font-size: {FONT_SIZE}px;
            font-weight: {FONT_WEIGHT_MEDIUM};
            margin: 1px 4px;
            min-height: 38px;
        }}
        QWidget#Sidebar QPushButton:hover {{
            background-color: {COLOR_PRIMARY_LIGHT};
            color: {COLOR_TEXT_LIGHT};
        }}
        QWidget#Sidebar QPushButton:checked {{
            background-color: {COLOR_PRIMARY};
            color: #FFFFFF;
            font-weight: {FONT_WEIGHT_BOLD};
        }}
        QWidget#Sidebar QLabel {{
            color: {COLOR_TEXT_MUTED};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 4px 8px;
        }}
        """

def _header_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QWidget#Header {{
            background-color: {COLOR_SURFACE_DARK};
            border-bottom: 1px solid {COLOR_BORDER_DARK};
        }}
        QLabel#HeaderTitle {{
            font-size: {FONT_SIZE_LARGE}px;
            font-weight: {FONT_WEIGHT_EXTRA_BOLD};
            color: {COLOR_TEXT_DARK};
            letter-spacing: -0.3px;
        }}
        QLabel#HeaderSub {{
            font-size: 12px;
            color: {COLOR_TEXT_MUTED};
            font-weight: {FONT_WEIGHT_MEDIUM};
        }}
        QPushButton {{
            min-height: 34px;
            border-radius: 6px;
            padding: 7px 14px;
            font-weight: {FONT_WEIGHT_MEDIUM};
        }}
        QPushButton#PrimaryButton {{
            background: {COLOR_ACCENT};
            border: 1px solid {COLOR_ACCENT_HOVER};
            color: #FFFFFF;
        }}
        QPushButton#PrimaryButton:hover {{
            background: {COLOR_ACCENT_HOVER};
        }}
        QPushButton#SecondaryButton {{
            background: {COLOR_SURFACE_LIGHT};
            border: 1.5px solid {COLOR_BORDER_LIGHT};
            color: {COLOR_TEXT_LIGHT};
        }}
        QPushButton#SecondaryButton:hover {{
            background: {COLOR_PRIMARY_LIGHT};
            border-color: {COLOR_ACCENT};
            color: {COLOR_TEXT_LIGHT};
        }}
        QPushButton#DangerButton {{
            background: {COLOR_ERROR};
            color: #FFFFFF;
            border: 1px solid {COLOR_RISK};
        }}
        QPushButton#DangerButton:hover {{
            background: {COLOR_RISK};
            border-color: {COLOR_RISK};
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QWidget#Header {{
            background-color: {COLOR_SURFACE_LIGHT};
            border-bottom: 1px solid {COLOR_BORDER_LIGHT};
        }}
        QLabel#HeaderTitle {{
            font-size: {FONT_SIZE_LARGE}px;
            font-weight: {FONT_WEIGHT_EXTRA_BOLD};
            color: {COLOR_TEXT_LIGHT};
            letter-spacing: -0.3px;
        }}
        QLabel#HeaderSub {{
            font-size: 12px;
            color: {COLOR_TEXT_MUTED};
            font-weight: {FONT_WEIGHT_MEDIUM};
        }}
        QPushButton {{
            min-height: 34px;
            border-radius: 6px;
            padding: 7px 14px;
            font-weight: {FONT_WEIGHT_MEDIUM};
        }}
        QPushButton#PrimaryButton {{
            background: {COLOR_PRIMARY};
            color: #FFFFFF;
            border: 1px solid {COLOR_TEXT_LIGHT};
        }}
        QPushButton#PrimaryButton:hover {{
            background: {COLOR_TEXT_LIGHT};
        }}
        QPushButton#SecondaryButton {{
            background: {COLOR_SURFACE_LIGHT};
            border: 1.5px solid {COLOR_BORDER_LIGHT};
            color: {COLOR_TEXT_LIGHT};
        }}
        QPushButton#SecondaryButton:hover {{
            background: {COLOR_PRIMARY_LIGHT};
            border-color: {COLOR_PRIMARY};
            color: {COLOR_TEXT_LIGHT};
        }}
        QPushButton#DangerButton {{
            background: {COLOR_ERROR};
            color: #FFFFFF;
            border: 1px solid {COLOR_RISK};
        }}
        QPushButton#DangerButton:hover {{
            background: {COLOR_RISK};
            border-color: {COLOR_RISK};
        }}
        """ + _base_widget_qss(theme)

def _table_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QTableWidget {{
            background-color: {COLOR_SURFACE_DARK};
            alternate-background-color: {COLOR_SURFACE_DARK};
            gridline-color: {COLOR_BORDER_DARK};
            border: 1px solid {COLOR_BORDER_DARK};
            border-radius: 10px;
            selection-background-color: {COLOR_ACCENT};
            selection-color: #FFFFFF;
            color: {COLOR_TEXT_DARK};
        }}
        QTableWidget::item {{
            padding: 10px 8px;
            color: {COLOR_TEXT_DARK};
            border-bottom: 1px solid {COLOR_BORDER_DARK};
        }}
        QTableWidget::item:selected {{
            background-color: {COLOR_ACCENT};
            color: #FFFFFF;
            font-weight: 600;
        }}
        QHeaderView::section {{
            background-color: {COLOR_SURFACE_DARK};
            color: {COLOR_TEXT_MUTED};
            padding: 10px 8px;
            border: none;
            border-right: 1px solid {COLOR_BORDER_DARK};
            font-weight: {FONT_WEIGHT_BOLD};
            font-size: {FONT_SIZE_SMALL}px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        QHeaderView::section:first {{
            border-top-left-radius: 10px;
        }}
        QHeaderView::section:last {{
            border-top-right-radius: 10px;
            border-right: none;
        }}
        QTableCornerButton::section {{
            background-color: {COLOR_SURFACE_DARK};
            border: none;
            border-top-left-radius: 10px;
        }}
        """
    return f"""
        QTableWidget {{
            background-color: {COLOR_SURFACE_LIGHT};
            alternate-background-color: {COLOR_CARD_LIGHT};
            gridline-color: {COLOR_BORDER_LIGHT};
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-radius: 10px;
            selection-background-color: {COLOR_PRIMARY};
            selection-color: {COLOR_TEXT_LIGHT};
            color: {COLOR_TEXT_LIGHT};
        }}
        QTableWidget::item {{
            padding: 10px 8px;
            color: {COLOR_TEXT_LIGHT};
            border-bottom: 1px solid {COLOR_BORDER_LIGHT};
        }}
        QTableWidget::item:selected {{
            background-color: {COLOR_PRIMARY};
            color: #FFFFFF;
            font-weight: 600;
        }}
        QHeaderView::section {{
            background-color: {COLOR_PRIMARY};
            color: #FFFFFF;
            padding: 10px 8px;
            border: none;
            border-right: 1px solid {COLOR_TEXT_LIGHT};
            font-weight: {FONT_WEIGHT_BOLD};
            font-size: {FONT_SIZE_SMALL}px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        QHeaderView::section:first {{
            border-top-left-radius: 10px;
        }}
        QHeaderView::section:last {{
            border-top-right-radius: 10px;
            border-right: none;
        }}
        QTableCornerButton::section {{
            background-color: {COLOR_PRIMARY};
            border: none;
            border-top-left-radius: 10px;
        }}
        """

def _input_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QLineEdit, QComboBox, QSpinBox, QTimeEdit {{
            background-color: {COLOR_SURFACE_DARK};
            border: 1.5px solid {COLOR_BORDER_DARK};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: {FONT_SIZE}px;
            color: {COLOR_TEXT_DARK};
            selection-background-color: {COLOR_ACCENT};
            selection-color: white;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus {{
            border: 1.5px solid {COLOR_ACCENT};
            background-color: {COLOR_SURFACE_DARK};
        }}
        QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QTimeEdit:hover {{
            border: 1.5px solid {COLOR_BORDER_DARK};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 28px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {COLOR_TEXT_MUTED};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLOR_SURFACE_DARK};
            color: {COLOR_TEXT_DARK};
            selection-background-color: {COLOR_ACCENT};
            selection-color: #FFFFFF;
            border: 1px solid {COLOR_BORDER_DARK};
            border-radius: 8px;
            padding: 4px;
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QLineEdit, QComboBox, QSpinBox, QTimeEdit {{
            background-color: {COLOR_SURFACE_LIGHT};
            border: 1.5px solid {COLOR_BORDER_LIGHT};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: {FONT_SIZE}px;
            color: {COLOR_TEXT_LIGHT};
            selection-background-color: {COLOR_PRIMARY};
            selection-color: #FFFFFF;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus {{
            border: 1.5px solid {COLOR_PRIMARY};
            background-color: {COLOR_SURFACE_LIGHT};
        }}
        QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QTimeEdit:hover {{
            border: 1.5px solid {COLOR_BORDER_LIGHT};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 28px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5x solid transparent;
            border-top: 6px solid {COLOR_TEXT_MUTED};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLOR_SURFACE_LIGHT};
            color: {COLOR_TEXT_LIGHT};
            selection-background-color: {COLOR_PRIMARY};
            selection-color: #FFFFFF;
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-radius: 8px;
            padding: 4px;
        }}
        """ + _base_widget_qss(theme)

def _groupbox_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QGroupBox {{
            background-color: {COLOR_SURFACE_DARK};
            border: 1px solid {COLOR_BORDER_DARK};
            border-radius: 12px;
            margin-top: 14px;
            padding: 16px;
            padding-top: 20px;
            font-weight: {FONT_WEIGHT_BOLD};
            font-size: 13px;
            color: {COLOR_TEXT_DARK};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 4px 10px;
            background-color: {COLOR_ACCENT};
            color: #FFFFFF;
            border-radius: 6px;
            font-size: 12px;
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QGroupBox {{
            background-color: {COLOR_SURFACE_LIGHT};
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-radius: 12px;
            margin-top: 14px;
            padding: 16px;
            padding-top: 20px;
            font-weight: {FONT_WEIGHT_BOLD};
            font-size: 13px;
            color: {COLOR_TEXT_LIGHT};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 4px 10px;
            background-color: {COLOR_PRIMARY};
            color: #FFFFFF;
            border-radius: 6px;
            font-size: 12px;
        }}
        """ + _base_widget_qss(theme)

def _progressbar_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QProgressBar {{
            border: none;
            border-radius: 8px;
            text-align: center;
            background-color: {COLOR_BORDER_DARK};
            height: 20px;
            color: {COLOR_TEXT_DARK};
            font-weight: 700;
            font-size: 11px;
        }}
        QProgressBar::chunk {{
            background-color: {COLOR_ACCENT};
            border-radius: 8px;
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QProgressBar {{
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-radius: 8px;
            text-align: center;
            background-color: {COLOR_CARD_LIGHT};
            height: 20px;
            color: {COLOR_TEXT_LIGHT};
            font-weight: 700;
            font-size: 11px;
        }}
        QProgressBar::chunk {{
            background-color: {COLOR_PRIMARY};
            border-radius: 8px;
        }}
        """ + _base_widget_qss(theme)

def _scrollbar_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QScrollBar:vertical {{
            background: {COLOR_SURFACE_DARK};
            width: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLOR_BORDER_DARK};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLOR_TEXT_MUTED};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {COLOR_SURFACE_DARK};
            height: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {COLOR_BORDER_DARK};
            border-radius: 5px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {COLOR_TEXT_MUTED};
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QScrollBar:vertical {{
            background: {COLOR_BG_LIGHT};
            width: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLOR_BORDER_LIGHT};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLOR_BORDER_LIGHT};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {COLOR_BG_LIGHT};
            height: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {COLOR_BORDER_LIGHT};
            border-radius: 5px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {COLOR_BORDER_LIGHT};
        }}
        """

def _tabbar_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QTabWidget::pane {{
            border: 1px solid {COLOR_BORDER_DARK};
            background: {COLOR_SURFACE_DARK};
            border-radius: 10px;
            top: -1px;
        }}
        QTabBar::tab {{
            padding: 10px 18px;
            background: {COLOR_SURFACE_DARK};
            border: 1px solid {COLOR_BORDER_DARK};
            border-bottom: 1px solid {COLOR_BORDER_DARK};
            border-radius: 8px 8px 0 0;
            margin-right: 4px;
            color: {COLOR_TEXT_MUTED};
            font-weight: {FONT_WEIGHT_MEDIUM};
            font-size: {FONT_SIZE}px;
        }}
        QTabBar::tab:selected {{
            background: {COLOR_SURFACE_LIGHT};
            color: {COLOR_TEXT_DARK};
            font-weight: {FONT_WEIGHT_BOLD};
            border-bottom: 1px solid #FFFFFF;
        }}
        QTabBar::tab:!selected:hover {{
            background: #334155;
            color: {COLOR_TEXT_DARK};
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QTabWidget::pane {{
            border: 1px solid {COLOR_BORDER_LIGHT};
            background: {COLOR_SURFACE_LIGHT};
            border-radius: 10px;
            top: -1px;
        }}
        QTabBar::tab {{
            padding: 10px 18px;
            background: {COLOR_SURFACE_LIGHT};
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            border-radius: 8px 8px 0 0;
            margin-right: 4px;
            color: {COLOR_TEXT_MUTED};
            font-weight: {FONT_WEIGHT_MEDIUM};
            font-size: {FONT_SIZE}px;
        }}
        QTabBar::tab:selected {{
            background: #FFFFFF;
            color: {COLOR_TEXT_LIGHT};
            font-weight: {FONT_WEIGHT_BOLD};
            border-bottom: 1px solid #FFFFFF;
        }}
        QTabBar::tab:!selected:hover {{
            background: {COLOR_PRIMARY_LIGHT};
            color: {COLOR_TEXT_LIGHT};
        }}
        """

def _tooltip_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QToolTip {{
            background-color: {COLOR_SURFACE_DARK};
            color: {COLOR_TEXT_DARK};
            border: none;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QToolTip {{
            background-color: {COLOR_PRIMARY_LIGHT};
            color: {COLOR_TEXT_LIGHT};
            border: none;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        """

def _card_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QFrame#Card {{
            background-color: {COLOR_CARD_DARK};
            border: 1px solid {COLOR_BORDER_DARK};
            border-radius: 12px;
            padding: 14px;
            color: {COLOR_TEXT_DARK};
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QFrame#Card {{
            background-color: {COLOR_CARD_LIGHT};
            border: 1px solid {COLOR_BORDER_LIGHT};
            border-radius: 12px;
            padding: 14px;
            color: {COLOR_TEXT_LIGHT};
        }}
        """

def _statlabel_qss(theme: str) -> str:
    if theme == "dark":
        return f"""
        QLabel#StatValue {{
            font-size: 28px;
            font-weight: 900;
            color: {COLOR_TEXT_DARK};
            letter-spacing: -0.5px;
        }}
        QLabel#StatLabel {{
            font-size: 11px;
            color: {COLOR_TEXT_MUTED};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }}
        """ + _base_widget_qss(theme)
    return f"""
        QLabel#StatValue {{
            font-size: 28px;
            font-weight: 900;
            color: {COLOR_TEXT_LIGHT};
            letter-spacing: -0.5px;
        }}
        QLabel#StatLabel {{
            font-size: 11px;
            color: {COLOR_TEXT_MUTED};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }}
        """ + _base_widget_qss(theme)

_APP_QSS = """
/* ===== MODERN PROFESSIONAL THEME (LIGHT) ===== */
""" + _base_widget_qss("light") + _sidebar_qss("light") + _header_qss("light") + _table_qss("light") + _input_qss("light") + _groupbox_qss("light") + _progressbar_qss("light") + _scrollbar_qss("light") + _tabbar_qss("light") + _tooltip_qss("light") + _card_qss("light") + _statlabel_qss("light")

_DARK_QSS = """
/* ===== POLISHED DARK THEME ===== */
""" + _base_widget_qss("dark") + _sidebar_qss("dark") + _header_qss("dark") + _table_qss("dark") + _input_qss("dark") + _groupbox_qss("dark") + _progressbar_qss("dark") + _scrollbar_qss("dark") + _tabbar_qss("dark") + _tooltip_qss("dark") + _card_qss("dark") + _statlabel_qss("dark")

def get_theme_qss(theme: str) -> str:
    if theme == "dark":
        return _DARK_QSS
    return _APP_QSS