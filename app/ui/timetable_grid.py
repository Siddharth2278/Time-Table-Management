from PySide6.QtCore import Qt, QPoint, QMimeData, Signal
from PySide6.QtGui import QColor, QDrag
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QGraphicsDropShadowEffect


def _polish(widget):
    try:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
    except Exception:
        pass


class DropZone(QFrame):
    clicked = Signal(int, int)
    drop_requested = Signal(int, int, int)

    STATES = ("", "drop", "ok", "bad")

    def __init__(self, row, column, parent=None):
        super().__init__(parent)
        self.row = row
        self.column = column
        self.setAcceptDrops(True)
        self.setMinimumHeight(78)
        self.setObjectName("DropZone")
        self.dark_mode = False
        self.reset_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.row, self.column)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-timetable-entry"):
            event.acceptProposedAction()
            self.set_state("drop")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.reset_style()
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-timetable-entry"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Emit the dragged entry and target cell to the timetable view."""
        if not event.mimeData().hasFormat("application/x-timetable-entry"):
            event.ignore()
            return
        try:
            entry_id = int(bytes(event.mimeData().data("application/x-timetable-entry")).decode())
        except (TypeError, ValueError):
            event.ignore()
            self.reset_style()
            return
        self.drop_requested.emit(entry_id, self.row, self.column)
        self.reset_style()
        event.acceptProposedAction()

    def set_state(self, state: str):
        self.setProperty("state", state if state in self.STATES else "")
        _polish(self)

    def reset_style(self):
        self.set_state("")

    def set_theme(self, dark_mode):
        self.dark_mode = dark_mode
        _polish(self)

    def set_drop_feedback(self, valid):
        self.set_state("ok" if valid else "bad")


class LectureCard(QFrame):
    def __init__(self, entry, row, column, parent=None):
        super().__init__(parent)
        self.entry_id = entry.id
        self.row = row
        self.column = column
        self.setObjectName("LectureCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumHeight(66)
        lecture_type = getattr(entry, "lecture_type", "Theory") or "Theory"
        self.lecture_type = lecture_type
        self.setProperty("ltype", lecture_type)
        self.setProperty("conflict", False)
        self.setProperty("selected", False)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 36))
        self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(2)
        self.code_label = QLabel(entry.subject.code if entry.subject and entry.subject.code else "")
        self.code_label.setObjectName("CardCode")
        self.code_label.setWordWrap(True)
        self.title_label = QLabel(entry.subject.name if entry.subject and entry.subject.name else "Untitled")
        self.title_label.setObjectName("CardTitle")
        self.title_label.setWordWrap(True)
        self.teacher_label = QLabel(entry.teacher.name if entry.teacher else "Unassigned teacher")
        self.teacher_label.setObjectName("CardMeta")
        self.teacher_label.setWordWrap(True)
        room = entry.room.name if entry.room else "No room"
        self.time_label = QLabel(f"{room}  •  {entry.start_time}-{entry.end_time}")
        self.time_label.setObjectName("CardTime")
        self.time_label.setWordWrap(True)
        layout.addWidget(self.code_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.teacher_label)
        layout.addWidget(self.time_label)
        self._drag_start = QPoint()
        _polish(self)

    def set_conflict(self, value: bool):
        self.setProperty("conflict", bool(value))
        _polish(self)

    def set_selected(self, value: bool):
        self.setProperty("selected", bool(value))
        _polish(self)

    def _grid(self):
        w = self.parentWidget()
        while w is not None and not hasattr(w, "card_selected"):
            w = w.parentWidget() if hasattr(w, "parentWidget") else None
        return w

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            g = self._grid()
            if g is not None:
                g.card_selected(self.entry_id)
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
        g = self._grid()
        if g is not None and hasattr(g, "emit_card_double_click"):
            g.emit_card_double_click(self.entry_id)
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
        self.dark_mode = False

    def set_theme(self, dark_mode):
        # Colors come from the application QSS; just re-polish everything.
        self.dark_mode = dark_mode
        _polish(self)
        for card in self.cards.values():
            _polish(card)
        for zone in self.zones.values():
            _polish(zone)

    def clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                try:
                    widget.hide()
                    widget.setParent(None)
                except Exception:
                    pass
                widget.deleteLater()
        self.zones.clear()
        self.cards.clear()
        self.selected_entry_id = None
        self.selected_slot = (-1, -1)

    @staticmethod
    def _norm(t: str) -> str:
        return str(t or "").strip()

    def populate(self, days, times, entries, breaks=None, conflict_ids=None):
        self.clear_grid()
        self.days = days
        self.times = times
        breaks = breaks or {}
        conflict_ids = set(conflict_ids or [])
        norm_breaks = {(self._norm(a), self._norm(b)): n for (a, b), n in breaks.items()}
        corner = QLabel("DAY ↓ TIME →")
        corner.setObjectName("GridCorner")
        corner.setAlignment(Qt.AlignCenter)
        self.grid.addWidget(corner, 0, 0)
        headers = [day.name.upper() for day in days]
        for column, label in enumerate(headers, start=1):
            header = QLabel(label)
            header.setObjectName("GridHead")
            header.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(header, 0, column)
        for row, (start, end) in enumerate(times, start=1):
            label = QLabel(f"{start}\n{end}")
            label.setObjectName("GridTime")
            label.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(label, row, 0)
            is_break = (self._norm(start), self._norm(end)) in norm_breaks
            for column, _day in enumerate(days, start=1):
                if is_break:
                    bname = str(norm_breaks.get((self._norm(start), self._norm(end)), "Break")).upper()
                    blabel = QLabel(bname)
                    blabel.setObjectName("BreakCell")
                    blabel.setAlignment(Qt.AlignCenter)
                    self.grid.addWidget(blabel, row, column)
                    continue
                zone = DropZone(row - 1, column - 1, self)
                zone.set_theme(self.dark_mode)
                zone.clicked.connect(self.slot_clicked)
                zone.drop_requested.connect(self.drop_requested)
                self.zones[(row - 1, column - 1)] = zone
                self.grid.addWidget(zone, row, column)
                self.grid.setColumnStretch(column, 1)
            self.grid.setRowMinimumHeight(row, 78)
        self.grid.setColumnMinimumWidth(0, 80)
        for entry in entries:
            try:
                key = (self._norm(entry.start_time), self._norm(entry.end_time))
                norm_times = [(self._norm(a), self._norm(b)) for a, b in times]
                row = norm_times.index(key)
                column = next(index for index, day in enumerate(days) if day.id == entry.day_id)
            except (ValueError, StopIteration, AttributeError):
                continue
            zone = self.zones.get((row, column))
            if zone is None:
                continue
            try:
                card = LectureCard(entry, row, column, zone)
                if entry.id in conflict_ids:
                    card.set_conflict(True)
                lay = zone.layout()
                if lay is None:
                    lay = QVBoxLayout(zone)
                    lay.setContentsMargins(3, 3, 3, 3)
                else:
                    # Stacked conflict: keep both visible, do not orphan
                    pass
                lay.addWidget(card)
                self.cards[entry.id] = card
            except Exception:
                continue

    def card_selected(self, entry_id):
        self.selected_entry_id = entry_id
        for card in self.cards.values():
            card.set_selected(card.entry_id == entry_id)

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
