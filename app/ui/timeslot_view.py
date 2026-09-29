from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QGridLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from functools import partial
from app.database import get_session
from app.models import TimeSlot, WorkingDay
from app.ui.dialogs import TimeSlotDialog
from app.ui.icons import icon
from app.ui.widgets import Switch, page_header, show_toast

PILL_CLASS = ("#166534", "#DCFCE7")
PILL_BREAK = ("#92400E", "#FEF3C7")


class TimeSlotView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        self.add_btn = QPushButton(" Add Slot")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setIcon(icon("plus", "#FFFFFF", 16))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(lambda: self.add_slot())
        layout.addWidget(page_header(
            "Time Slots", "Working days, custom durations and breaks.", self.add_btn))

        self.days_group = QGroupBox("WORKING DAYS")
        days_layout = QGridLayout(self.days_group)
        days_layout.setSpacing(8)
        self.day_checks = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for idx, d in enumerate(days):
            cb = Switch(d)
            cb.stateChanged.connect(self.on_day_toggled)
            self.day_checks[d] = cb
            days_layout.addWidget(cb, idx // 4, idx % 4)
        layout.addWidget(self.days_group)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        top.addWidget(self.count_label)
        top.addStretch()
        card_layout.addLayout(top)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["TIME", "LABEL", "TYPE", "ACTIONS"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 96)
        self.table.cellDoubleClicked.connect(
            lambda r, c: self.edit_slot(self._id_at_row(r)))
        card_layout.addWidget(self.table)

        self.empty_label = QLabel("No time slots yet. Click “Add Slot” to define your first period.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setWordWrap(True)
        card_layout.addWidget(self.empty_label)

        info = QLabel("Breaks cannot overlap lectures. Slots are global (all working days). Supports 30 / 45 / 60 / 90 / 120 min durations.")
        info.setObjectName("Muted")
        info.setWordWrap(True)
        card_layout.addWidget(info)
        layout.addWidget(card)

    def refresh(self):
        self.load_days()
        self.load_slots()

    def _id_at_row(self, row):
        item = self.table.item(row, 0)
        if item is None:
            return None
        try:
            return int(item.data(Qt.UserRole))
        except (TypeError, ValueError):
            return None

    def load_days(self):
        session = get_session()
        try:
            days = session.query(WorkingDay).all()
            for d in days:
                if d.name in self.day_checks:
                    self.day_checks[d.name].blockSignals(True)
                    self.day_checks[d.name].setChecked(d.is_enabled)
                    self.day_checks[d.name].blockSignals(False)
        finally:
            session.close()

    def on_day_toggled(self):
        session = get_session()
        try:
            for name, cb in self.day_checks.items():
                day = session.query(WorkingDay).filter(WorkingDay.name == name).first()
                if day:
                    day.is_enabled = cb.isChecked()
            session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def load_slots(self):
        session = get_session()
        try:
            slots = session.query(TimeSlot).order_by(TimeSlot.start_time).all()
            self.table.setRowCount(0)
            self.table.setRowCount(len(slots))
            mono = QFont("Cascadia Code")
            for r, s in enumerate(slots):
                time_item = QTableWidgetItem(f"{s.start_time} - {s.end_time}")
                time_item.setFont(mono)
                self.table.setItem(r, 0, time_item)
                self.table.setItem(r, 1, QTableWidgetItem(s.label or ""))
                if s.is_break:
                    type_item = QTableWidgetItem(s.break_name or "Break")
                    type_item.setForeground(QColor(PILL_BREAK[0]))
                    type_item.setBackground(QColor(PILL_BREAK[1]))
                else:
                    type_item = QTableWidgetItem("Class")
                    type_item.setForeground(QColor(PILL_CLASS[0]))
                    type_item.setBackground(QColor(PILL_CLASS[1]))
                type_item.setTextAlignment(Qt.AlignCenter)
                bold = QFont()
                bold.setBold(True)
                type_item.setFont(bold)
                self.table.setItem(r, 2, type_item)
                for c in range(3):
                    self.table.item(r, c).setData(Qt.UserRole, s.id)
                cell = QWidget()
                row_layout = QHBoxLayout(cell)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(4)
                edit = QPushButton()
                edit.setObjectName("RowButton")
                edit.setIcon(icon("pencil", "#8A94A0", 16))
                edit.setToolTip("Edit")
                edit.setCursor(Qt.PointingHandCursor)
                edit.clicked.connect(partial(self.edit_slot, s.id))
                row_layout.addWidget(edit)
                delete = QPushButton()
                delete.setObjectName("RowButtonDanger")
                delete.setIcon(icon("trash", "#D6544C", 16))
                delete.setToolTip("Delete")
                delete.setCursor(Qt.PointingHandCursor)
                delete.clicked.connect(partial(self.delete_slot, s.id))
                row_layout.addWidget(delete)
                row_layout.addStretch()
                self.table.setCellWidget(r, 3, cell)
            self.count_label.setText(f"{len(slots)} slot{'s' if len(slots) != 1 else ''}")
            self.empty_label.setVisible(len(slots) == 0)
        finally:
            session.close()

    def _selected_id(self):
        return self._id_at_row(self.table.currentRow())

    def add_slot(self):
        dlg = TimeSlotDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                slot = TimeSlot(**data)
                session.add(slot)
                session.commit()
                show_toast(self, "Time slot added.")
                self.load_slots()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def edit_slot(self, sid=None):
        if sid is None:
            sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a slot to edit.")
            return
        session = get_session()
        try:
            slot = session.query(TimeSlot).filter(TimeSlot.id == sid).first()
            if not slot:
                return
            dlg = TimeSlotDialog(self, slot)
            session.expunge(slot)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    s = s2.query(TimeSlot).filter(TimeSlot.id == sid).first()
                    for k, v in data.items():
                        setattr(s, k, v)
                    s2.commit()
                    show_toast(self, "Time slot updated.")
                    self.load_slots()
                except Exception as e:
                    s2.rollback()
                    QMessageBox.critical(self, "Error", str(e))
                finally:
                    s2.close()
        except Exception as e:
            try:
                session.close()
            except Exception:
                pass
            QMessageBox.critical(self, "Error", str(e))

    def delete_slot(self, sid=None):
        if sid is None:
            sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a slot to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this time slot?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            slot = session.query(TimeSlot).filter(TimeSlot.id == sid).first()
            if slot:
                session.delete(slot)
                session.commit()
                show_toast(self, "Time slot deleted.")
                self.load_slots()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
