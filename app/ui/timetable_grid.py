from PySide6.QtCore import Qt, QPoint, QMimeData, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QGraphicsDropShadowEffect


class DropZone(QFrame):
    clicked = Signal(int, int)
    drop_requested = Signal(int, int, int)

    def __init__(self, row, column, parent=None):
        super().__init__(parent)
        self.row = row
        self.column = column
        self.setAcceptDrops(True)
        self.setMinimumHeight(76)
        self.setObjectName("DropZone")
        # Theme colors - will be styled via global QSS, but keep fallback
        self.setStyleSheet("QFrame#DropZone { border: 1px solid var(--border-light); border-radius: 6px; }")

    def mousePressEvent(self, event):
        self.clicked.emit(self.row, self.column)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-timetable-entry"):
            event.acceptProposedAction()
            # Feedback handled by QSS hover state; add temporary class if needed
            self.setStyleSheet("QFrame#DropZone { border: 2px solid var(--accent); border-radius: 6px; background: var(--bg-primary-light); }")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.reset_style()
        super().dragLeaveEvent(event)

    def reset_style(self):
        self.setStyleSheet("QFrame#DropZone { border: 1px solid var(--border-light); border-radius: 6px; }")

    def set_drop_feedback(self, valid):
        if valid:
            self.setStyleSheet("QFrame#DropZone { border: 2px solid var(--success); border-radius: 6px; background: var(--bg-success-light); }")
        else:
            self.setStyleSheet("QFrame#DropZone { border: 2px solid var(--error); border-radius: 6px; background: var(--bg-error-light); }")


class LectureCard(QFrame):
    def __init__(self, entry, row, column, color, parent=None):
        super().__init__(parent)
        self.entry_id = entry.id
        self.row = row
        self.column = column
        self.setObjectName("LectureCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumHeight(66)
        # Theme-aware base style; specific colors from QSS variables
        self.setStyleSheet(
            "QFrame#LectureCard { border-radius: 8px; padding: 6px; } "
            "QFrame#LectureCard:hover { border: 1px solid var(--accent); }"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(25, 55, 70, 35))
        self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 7, 7)
        layout.setSpacing(2)
        subject = QLabel(f"{entry.subject.code if entry.subject else ''}  {entry.subject.name if entry.subject else 'Untitled'}")
        subject.setStyleSheet("color: var(--text-primary); font-weight: 800; font-size: 11px; background: transparent;")
        subject.setWordWrap(True)
        teacher = QLabel(entry.teacher.name if entry.teacher else "Unassigned teacher")
        teacher.setStyleSheet("color: var(--text-muted); font-size: 10px; background: transparent;")
        room = QLabel(f"{entry.room.name if entry.room else 'No room'}  ·  {entry.start_time}-{entry.end_time}")
        room.setStyleSheet("color: var(--text-muted); font-size: 9px; background: transparent;")
        layout.addWidget(subject)
        layout.addWidget(teacher)
        layout.addWidget(room)
        self._drag_start = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            self.parentWidget().parentWidget().card_selected(self.entry_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 8:
            return
        mime = QMimeData()
        mime.setData("application/x-timetable-entry", str(self.entry_id).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

    def mouseDoubleClickEvent(self, event):
        self.parentWidget().parentWidget().emit_card_double_click(self.entry_id)
        super().mouseDoubleClickEvent(event)


class TimetableGridWidget(QFrame):
    card_double_clicked = Signal(int)
    drop_requested = Signal(int, int, int)
    slot_clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("TimetableGrid")
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(10, 10, 10, 10)
        self.grid.setSpacing(6)
        self.days = []
        self.times = []
        self.zones = {}
        self.cards = {}
        self.selected_entry_id = None
        self.selected_slot = (-1, -1)
        # Base grid styling via QSS; minimal inline for initial state
        self.setStyleSheet("QFrame#TimetableGrid { border-radius: 12px; }")

    def clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.zones.clear()
        self.cards.clear()

    def populate(self, days, times, entries):
        self.clear_grid()
        self.days = days
        self.times = times
        headers = ["TIME"] + [day.name.upper() for day in days]
        for column, label in enumerate(headers):
            header = QLabel(label)
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet(
                "color: var(--text-primary); background: var(--bg-primary-light); "
                "border-radius: 6px; padding: 10px 5px; font-size: 10px; font-weight: 800;"
            )
            self.grid.addWidget(header, 0, column)
        for row, (start, end) in enumerate(times, start=1):
            label = QLabel(f"{start}\n{end}")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                "color: var(--text-muted); background: var(--bg-secondary-light); "
                "border-radius: 6px; padding: 8px 4px; font-size: 10px; font-weight: 700;"
            )
            self.grid.addWidget(label, row, 0)
            for column, _day in enumerate(days, start=1):
                zone = DropZone(row - 1, column - 1, self)
                zone.clicked.connect(self.slot_clicked)
                zone.drop_requested.connect(self.drop_requested)
                self.zones[(row - 1, column - 1)] = zone
                self.grid.addWidget(zone, row, column)
                self.grid.setColumnStretch(column, 1)
            self.grid.setRowMinimumHeight(row, 76)
        self.grid.setColumnMinimumWidth(0, 78)
        for entry in entries:
            try:
                row = times.index((entry.start_time, entry.end_time))
                column = next(index for index, day in enumerate(days) if day.id == entry.day_id)
            except (ValueError, StopIteration):
                continue
            zone = self.zones[(row, column)]
            lecture_type = entry.lecture_type if hasattr(entry, 'lecture_type') else "Theory"
            colors_map = {"Theory": "#DDF3EC", "Practical": "#E3EEFB", "Lab": "#FFF0D8", "Tutorial": "#EEE7FA"}
            card = LectureCard(entry, row, column, colors_map.get(lecture_type, "#E7F0F3"), zone)
            zone.layout = QVBoxLayout(zone)
            zone.layout.setContentsMargins(3, 3, 3, 3)
            zone.layout.addWidget(card)
            self.cards[entry.id] = card

    def card_selected(self, entry_id):
        self.selected_entry_id = entry_id
        for card in self.cards.values():
            card.setProperty("selected", card.entry_id == entry_id)
            card.style().unpolish(card)
            card.style().polish(card)

    def emit_card_double_click(self, entry_id):
        self.selected_entry_id = entry_id
        self.card_double_clicked.emit(entry_id)

    def select_slot(self, row, column):
        self.selected_slot = (row, column)
        self.slot_clicked.emit(row, column)

    def set_drop_feedback(self, row, column, valid):
        zone = self.zones.get((row, column))
        if zone:
            zone.set_drop_feedback(valid)