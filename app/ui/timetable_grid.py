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
        self.setStyleSheet("QFrame#DropZone { background: #141F2B; border: 1px solid #2A3B4C; border-radius: 6px; }")

    def mousePressEvent(self, event):
        self.clicked.emit(self.row, self.column)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-timetable-entry"):
            event.acceptProposedAction()
            self.setStyleSheet("QFrame#DropZone { background: #E4F4EF; border: 2px solid #58B59D; border-radius: 6px; }")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.reset_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        try:
            entry_id = int(bytes(event.mimeData().data("application/x-timetable-entry")).decode())
        except (TypeError, ValueError):
            event.ignore()
            return
        self.drop_requested.emit(entry_id, self.row, self.column)
        self.reset_style()
        event.acceptProposedAction()

    def reset_style(self):
        self.setStyleSheet("QFrame#DropZone { background: #141F2B; border: 1px solid #2A3B4C; border-radius: 6px; }")


class LectureCard(QFrame):
    def __init__(self, entry, row, column, color, parent=None):
        super().__init__(parent)
        self.entry_id = entry.id
        self.row = row
        self.column = column
        self.setObjectName("LectureCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumHeight(66)
        self.setStyleSheet(f"QFrame#LectureCard {{ background: {color}; border: 1px solid #FFFFFF; border-left: 4px solid #1F8A70; border-radius: 8px; }} QFrame#LectureCard:hover {{ border: 1px solid #1F8A70; }}")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(25, 55, 70, 35))
        self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 7, 7)
        layout.setSpacing(2)
        subject = QLabel(f"{entry.subject.code if entry.subject else ''}  {entry.subject.name if entry.subject else 'Untitled'}")
        subject.setStyleSheet("color: #173A35; font-weight: 800; font-size: 11px; background: transparent;")
        subject.setWordWrap(True)
        teacher = QLabel(entry.teacher.name if entry.teacher else "Unassigned teacher")
        teacher.setStyleSheet("color: #386156; font-size: 10px; background: transparent;")
        room = QLabel(f"{entry.room.name if entry.room else 'No room'}  ·  {entry.start_time}-{entry.end_time}")
        room.setStyleSheet("color: #52746A; font-size: 9px; background: transparent;")
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
        self.setStyleSheet("QFrame#TimetableGrid { background: #0F1722; border: 1px solid #2A3B4C; border-radius: 12px; }")

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
            header.setStyleSheet("background: #23485A; color: #FFFFFF; border-radius: 6px; padding: 10px 5px; font-size: 10px; font-weight: 800;")
            self.grid.addWidget(header, 0, column)
        for row, (start, end) in enumerate(times, start=1):
            label = QLabel(f"{start}\n{end}")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #9CB0BE; background: #1B2A38; border-radius: 6px; padding: 8px 4px; font-size: 10px; font-weight: 700;")
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
            colors = {"Theory": "#DDF3EC", "Practical": "#E3EEFB", "Lab": "#FFF0D8", "Tutorial": "#EEE7FA"}
            card = LectureCard(entry, row, column, colors.get(entry.lecture_type, "#E7F0F3"), zone)
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
            if valid:
                zone.setStyleSheet("QFrame#DropZone { background: #E4F4EF; border: 2px solid #58B59D; border-radius: 6px; }")
            else:
                zone.setStyleSheet("QFrame#DropZone { background: #FFF1F2; border: 2px solid #E57373; border-radius: 6px; }")
