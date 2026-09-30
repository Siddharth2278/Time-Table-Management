from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget
)
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import TeacherAvailability, RoomAvailability
from app.ui.dialogs import AvailabilityDialog
from app.ui.modals import ask, info, warn, error
from app.ui.widgets import show_toast


class AvailabilityView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        title = QLabel("Availability")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #132A3A;")
        layout.addWidget(title)
        sub = QLabel("Mark teacher or room/lab periods as unavailable. Timetable validation blocks lectures that overlap these periods.")
        sub.setStyleSheet("color: #64748B; font-size: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        self.teacher_table = self._make_table("Teacher")
        self.room_table = self._make_table("Room/Lab")
        self.tabs.addTab(self.teacher_table, "Teachers")
        self.tabs.addTab(self.room_table, "Rooms & Labs")
        self.tabs.currentChanged.connect(lambda _: self.load_current())
        layout.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()
        self.add_btn = QPushButton("＋ Add Unavailability")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_current)
        buttons.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_current)
        buttons.addWidget(self.edit_btn)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_btn.clicked.connect(self.delete_current)
        buttons.addWidget(self.delete_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _make_table(self, entity_label):
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["ID", entity_label, "Day", "Time", "Reason"])
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 60)
        table.verticalHeader().setVisible(False)
        table.cellDoubleClicked.connect(lambda _row, _column: self.edit_current())
        return table

    def refresh(self):
        self.load_current()

    def load_current(self):
        if self.tabs.currentIndex() == 0:
            self.load_teacher()
        else:
            self.load_room()

    def _fill_table(self, table, records, label_getter):
        table.clearContents()
        table.setRowCount(len(records) or 1)
        for row, availability in enumerate(records):
            values = [str(availability.id), label_getter(availability), availability.day.name if availability.day else str(availability.day_id), f"{availability.start_time}-{availability.end_time}", availability.reason or ""]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, availability.id)
                table.setItem(row, column, item)
        if not records:
            empty = QTableWidgetItem("No unavailable periods configured.")
            empty.setForeground(Qt.gray)
            table.setItem(0, 1, empty)
            table.setSpan(0, 1, 1, 4)

    def load_teacher(self):
        session = get_session()
        try:
            records = session.query(TeacherAvailability).order_by(TeacherAvailability.teacher_id).all()
            self._fill_table(self.teacher_table, records, lambda item: item.teacher.name if item.teacher else str(item.teacher_id))
        finally:
            session.close()

    def load_room(self):
        session = get_session()
        try:
            records = session.query(RoomAvailability).order_by(RoomAvailability.room_id).all()
            self._fill_table(self.room_table, records, lambda item: item.room.name if item.room else str(item.room_id))
        finally:
            session.close()

    def _selected_id(self):
        table = self.teacher_table if self.tabs.currentIndex() == 0 else self.room_table
        row = table.currentRow()
        if row < 0 or not table.item(row, 0):
            return None
        value = table.item(row, 0).text()
        return int(value) if value.isdigit() else None

    def add_current(self):
        is_teacher = self.tabs.currentIndex() == 0
        dialog = AvailabilityDialog(self, is_teacher=is_teacher)
        if dialog.exec():
            data = dialog.get_data()
            session = get_session()
            try:
                model = TeacherAvailability if is_teacher else RoomAvailability
                field = "teacher_id" if is_teacher else "room_id"
                session.add(model(**{field: data["entity_id"], "day_id": data["day_id"], "start_time": data["start_time"], "end_time": data["end_time"], "is_unavailable": True, "reason": data["reason"]}))
                session.commit()
                self.load_current()
                show_toast(self, "Unavailable period saved.")
            except Exception as exc:
                session.rollback()
                error(self, "Error", str(exc))
            finally:
                session.close()

    def edit_current(self):
        is_teacher = self.tabs.currentIndex() == 0
        record_id = self._selected_id()
        if not record_id:
            warn(self, "Select", "Please select an unavailable period to edit.")
            return
        model = TeacherAvailability if is_teacher else RoomAvailability
        field = "teacher_id" if is_teacher else "room_id"
        session = get_session()
        try:
            record = session.query(model).filter(model.id == record_id).first()
            if not record:
                return
            dialog = AvailabilityDialog(self, existing=record, is_teacher=is_teacher)
            session.expunge(record)
        finally:
            session.close()
        if dialog.exec():
            data = dialog.get_data()
            session = get_session()
            try:
                record = session.query(model).filter(model.id == record_id).first()
                setattr(record, field, data["entity_id"])
                record.day_id = data["day_id"]
                record.start_time = data["start_time"]
                record.end_time = data["end_time"]
                record.reason = data["reason"]
                session.commit()
                self.load_current()
            except Exception as exc:
                session.rollback()
                error(self, "Error", str(exc))
            finally:
                session.close()

    def delete_current(self):
        record_id = self._selected_id()
        if not record_id:
            warn(self, "Select", "Please select an unavailable period to delete.")
            return
        if not ask(self, "Confirm", "Delete this unavailable period?", ok_text="Delete", destructive=True):
            return
        model = TeacherAvailability if self.tabs.currentIndex() == 0 else RoomAvailability
        session = get_session()
        try:
            record = session.query(model).filter(model.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                self.load_current()
        except Exception as exc:
            session.rollback()
            error(self, "Error", str(exc))
        finally:
            session.close()
