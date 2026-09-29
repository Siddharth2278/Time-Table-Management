"""Shared presentational kit: page headers, toggle switch, toasts.

No business logic here — views keep their existing service calls.
"""
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QStyle, QStyleOptionButton,
    QVBoxLayout, QWidget,
)


def page_header(title: str, subtitle: str = "", action=None) -> QWidget:
    """Web-style PageHeader: title + subtitle left, action widget right."""
    box = QWidget()
    box.setObjectName("PageHeaderBox")
    outer = QHBoxLayout(box)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(12)
    col = QWidget()
    inner = QVBoxLayout(col)
    inner.setContentsMargins(0, 0, 0, 0)
    inner.setSpacing(2)
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    inner.addWidget(title_label)
    if subtitle:
        sub_label = QLabel(subtitle)
        sub_label.setObjectName("PageSubtitle")
        sub_label.setWordWrap(True)
        inner.addWidget(sub_label)
    outer.addWidget(col, 1)
    if action is not None:
        outer.addWidget(action, 0, Qt.AlignBottom)
    return box


class Switch(QCheckBox):
    """Fluent toggle switch. Same API/signals as QCheckBox (stateChanged etc.)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("Switch")
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        base = super().sizeHint()
        return QSize(max(46, base.width()), max(24, base.height()))

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            opt = QStyleOptionButton()
            self.initStyleOption(opt)
            enabled = opt.state & QStyle.State_Enabled
            checked = self.isChecked()
            # Track geometry: fixed 40x22 at left, vertically centered.
            track_w, track_h = 40, 22
            y = (self.height() - track_h) // 2
            if checked:
                track = QColor("#5B8CFF" if enabled else "#3E5B99")
            else:
                track = QColor("#3A4654" if enabled else "#2A323C")
            path = QPainterPath()
            path.addRoundedRect(0, y, track_w, track_h, track_h / 2, track_h / 2)
            painter.fillPath(path, track)
            knob_d = 16
            knob_x = (track_w - knob_d - 3) if checked else 3
            painter.setBrush(QColor("#FFFFFF" if enabled else "#8A94A0"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(knob_x, y + 3, knob_d, knob_d)
            # Label text to the right of the track, in the themed ink color
            # (a hardcoded white is invisible on light surfaces).
            if self.text():
                painter.setPen(QColor("#F4F7FA" if _SWITCH_DARK else "#1E293B")
                               if enabled else QColor("#8A94A0"))
                painter.drawText(track_w + 10, 0, self.width() - track_w - 10, self.height(),
                                 Qt.AlignLeft | Qt.AlignVCenter, self.text())
        finally:
            painter.end()


_SWITCH_DARK = True


def set_switch_theme(dark: bool):
    """Tell Switch widgets which theme is active (QSS colors are invisible to paint code)."""
    global _SWITCH_DARK
    _SWITCH_DARK = bool(dark)


_TOAST_COLORS = {
    "success": "#32D583",
    "danger": "#F04438",
    "info": "#5B8CFF",
    "warning": "#F5B942",
}


def show_toast(parent, text: str, kind: str = "success", ms: int = 2600):
    """Small floating confirmation. Fire-and-forget; never blocks like QMessageBox."""
    try:
        window = parent.window() if hasattr(parent, "window") else None
        dot = _TOAST_COLORS.get(kind, _TOAST_COLORS["success"])
        toast = QLabel(text, window)
        toast.setObjectName("Toast")
        toast.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        toast.setAttribute(Qt.WA_ShowWithoutActivating)
        toast.setStyleSheet(
            "QLabel#Toast {"
            " background: #171D26; color: #F4F7FA;"
            " border: 1px solid #27313D; border-left: 3px solid " + dot + ";"
            " border-radius: 8px; padding: 10px 16px;"
            " font-size: 13px; font-weight: 600; }"
        )
        toast.adjustSize()
        if window is not None:
            geo = window.geometry()
            x = geo.x() + (geo.width() - toast.width()) // 2
            y = geo.y() + geo.height() - toast.height() - 48
            toast.move(max(geo.x() + 16, x), max(geo.y() + 16, y))
        toast.show()
        QTimer.singleShot(ms, toast.deleteLater)
    except Exception:
        pass
