from PySide6.QtCore import Qt, QPoint, QMimeData, Signal
from PySide6.QtGui import QColor, QDrag
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QGraphicsDropShadowEffect


class DropZone(QFrame):
    clicked = Signal(int, int)
    drop_requested = Signal(int, int, int)

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
            self.setStyleSheet(
                "QFrame#DropZone { border: 2px solid #4F46E5; border-radius: 8px; background: #EEF2FF; }"
            )
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

    def reset_style(self):
        if self.dark_mode:
            self.setStyleSheet("QFrame#DropZone { border: 1px solid #2A3A5C; border-radius: 8px; background: #141F38; }")
        else:
            self.setStyleSheet("QFrame#DropZone { border: 1px solid #E2E8F0; border-radius: 8px; background: #FFFFFF; }")

    def set_theme(self, dark_mode):
        self.dark_mode = dark_mode
        self.reset_style()

    def set_drop_feedback(self, valid):
        if valid:
            self.setStyleSheet(
                "QFrame#DropZone { border: 2px solid #059669; border-radius: 8px; background: #ECFDF5; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#DropZone { border: 2px solid #DC2626; border-radius: 8px; background: #FEF2F2; }"
            )


class LectureCard(QFrame):
    ACCENTS = {
        "Theory": ("#EFF6FF", "#2563EB"),
        "Practical": ("#EEF2FF", "#4F46E5"),
        "Lab": ("#FFFBEB", "#D97706"),
        "Tutorial": ("#F5F3FF", "#7C3AED"),
    }

    def __init__(self, entry, row, column, color, parent=None):
        super().__init__(parent)
        self.entry_id = entry.id
        self.row = row
        self.column = column
        self.setObjectName("LectureCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumHeight(66)
        lecture_type = getattr(entry, "lecture_type", "Theory") or "Theory"
        self.lecture_type = lecture_type
        self._dark_mode = False
        self._apply_style()
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(15, 23, 42, 28))
        self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 7, 7)
        layout.setSpacing(2)
        subject = QLabel(f"{entry.subject.code if entry.subject else ''}  {entry.subject.name if entry.subject else 'Untitled'}")
        self.subject_label = subject
        subject.setStyleSheet(self._label_style("#F8FAFC", "#0F172A", "800", "11.5px"))
        subject.setWordWrap(True)
        teacher = QLabel(entry.teacher.name if entry.teacher else "Unassigned teacher")
        self.teacher_label = teacher
        teacher.setStyleSheet(self._label_style("#CBD5E1", "#475569", "600", "10.5px"))
        room = QLabel(f"{entry.room.name if entry.room else 'No room'}  \u00b7  {entry.start_time}-{entry.end_time}")
        self.room_label = room
        room.setStyleSheet(self._label_style("#94A3B8", "#64748B", "500", "10px"))
        layout.addWidget(subject)
        layout.addWidget(teacher)
        layout.addWidget(room)
        self._drag_start = QPoint()

    def _label_style(self, dark_color, light_color, weight, size):
        color = dark_color if self._dark_mode else light_color
        return f"color: {color}; font-size: {size}; font-weight: {weight}; background: transparent; border: none;"

    def _apply_style(self):
        bg, accent = self.ACCENTS.get(self.lecture_type, ("#EFF6FF", "#2563EB"))
        if self._dark_mode:
            bg = {"#EFF6FF": "#172554", "#EEF2FF": "#1E1B4B", "#FFFBEB": "#422006", "#F5F3FF": "#2E1065"}.get(bg, "#172554")
            border = "#334155"
        else:
            border = "#E2E8F0"
        self._base_style = (
            f"QFrame#LectureCard {{ background: {bg}; border: 1px solid {border}; "
            f"border-left: 4px solid {accent}; border-radius: 8px; padding: 6px; }} "
            f"QFrame#LectureCard:hover {{ border: 1px solid {accent}; border-left: 4px solid {accent}; }}"
        )
        self.setStyleSheet(self._base_style)
        if hasattr(self, "subject_label"):
            self.subject_label.setStyleSheet(self._label_style("#F8FAFC", "#0F172A", "800", "11.5px"))
            self.teacher_label.setStyleSheet(self._label_style("#CBD5E1", "#475569", "600", "10.5px"))
            self.room_label.setStyleSheet(self._label_style("#94A3B8", "#64748B", "500", "10px"))

    def set_theme(self, dark_mode):
        self._dark_mode = dark_mode
        self._apply_style()

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
        self._apply_grid_style()

    def _apply_grid_style(self):
        if self.dark_mode:
            self.setStyleSheet("QFrame#TimetableGrid { background: #0F172A; border: 1px solid #22304D; border-radius: 12px; }")
        else:
            self.setStyleSheet("QFrame#TimetableGrid { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; }")

    def set_theme(self, dark_mode):
        self.dark_mode = dark_mode
        self._apply_grid_style()
        for card in self.cards.values():
            card.set_theme(dark_mode)

    def clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.zones.clear()
        self.cards.clear()
        self.selected_entry_id = None
        self.selected_slot = (-1, -1)

    @staticmethod
    def _norm(t: str) -> str:
        return str(t or "").strip()

    def populate(self, days, times, entries):
        self.clear_grid()
        self.days = days
        self.times = times
        headers = ["TIME"] + [day.name.upper() for day in days]
        for column, label in enumerate(headers):
            header = QLabel(label)
            header.setAlignment(Qt.AlignCenter)
            if self.dark_mode:
                header.setStyleSheet("color: #E0E7FF; background: #1E1B4B; border: 1px solid #3730A3; border-radius: 8px; padding: 10px 5px; font-size: 10.5px; font-weight: 800;")
            else:
                header.setStyleSheet("color: #312E81; background: #EEF2FF; border: 1px solid #E0E7FF; border-radius: 8px; padding: 10px 5px; font-size: 10.5px; font-weight: 800;")
            self.grid.addWidget(header, 0, column)
        for row, (start, end) in enumerate(times, start=1):
            label = QLabel(f"{start}\n{end}")
            label.setAlignment(Qt.AlignCenter)
            if self.dark_mode:
                label.setStyleSheet("color: #CBD5E1; background: #141F38; border: 1px solid #22304D; border-radius: 8px; padding: 8px 4px; font-size: 10.5px; font-weight: 700;")
            else:
                label.setStyleSheet("color: #475569; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 4px; font-size: 10.5px; font-weight: 700;")
            self.grid.addWidget(label, row, 0)
            for column, _day in enumerate(days, start=1):
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
                lecture_type = entry.lecture_type if hasattr(entry, 'lecture_type') else "Theory"
                colors_map = {"Theory": "#EFF6FF", "Practical": "#EEF2FF", "Lab": "#FFFBEB", "Tutorial": "#F5F3FF"}
                card = LectureCard(entry, row, column, colors_map.get(lecture_type, "#EFF6FF"), zone)
                card.set_theme(self.dark_mode)
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
            if card.entry_id == entry_id:
                card.setStyleSheet(card._base_style + " QFrame#LectureCard { border: 2px solid #4F46E5; }")
            else:
                card.setStyleSheet(card._base_style)

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
