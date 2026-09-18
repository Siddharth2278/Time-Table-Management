from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import TimeSlot, WorkingDay
from app.ui.dialogs import TimeSlotDialog

class TimeSlotView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        title = QLabel("Time Slots & Working Days")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #1E2A3A;")
        layout.addWidget(title)

        # Working days group
        self.days_group = QGroupBox("Working Days (enable/disable)")
        days_layout = QGridLayout(self.days_group)
        self.day_checks = {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for idx, d in enumerate(days):
            cb = QCheckBox(d)
            cb.stateChanged.connect(self.on_day_toggled)
            self.day_checks[d] = cb
            days_layout.addWidget(cb, idx // 4, idx % 4)
        layout.addWidget(self.days_group)

        # Time slots
        header = QHBoxLayout()
        header.addWidget(QLabel("Time Slots (configure custom durations & breaks)"))
        header.addStretch()
        self.add_btn = QPushButton("＋ Add Slot")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_slot)
        header.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_slot)
        header.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_slot)
        header.addWidget(self.del_btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Time Range", "Label", "Break", "Break Name"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.cellDoubleClicked.connect(lambda r,c: self.edit_slot())
        layout.addWidget(self.table)

        info = QLabel("Break periods cannot overlap with lectures. All slots are global (apply to all working days). Supports 30/45/60/90/120 min durations.")
        info.setStyleSheet("color: #64748B; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

    def refresh(self):
        self.load_days()
        self.load_slots()

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
        # Save immediately
        session = get_session()
        try:
            for name, cb in self.day_checks.items():
                day = session.query(WorkingDay).filter(WorkingDay.name==name).first()
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
            self.table.setRowCount(len(slots))
            for r, s in enumerate(slots):
                self.table.setItem(r, 0, QTableWidgetItem(str(s.id)))
                self.table.setItem(r, 1, QTableWidgetItem(f"{s.start_time}-{s.end_time}"))
                self.table.setItem(r, 2, QTableWidgetItem(s.label or ""))
                br = QTableWidgetItem("Yes" if s.is_break else "No")
                if s.is_break:
                    br.setForeground(Qt.red)
                self.table.setItem(r, 3, br)
                self.table.setItem(r, 4, QTableWidgetItem(s.break_name or ""))
                for c in range(5):
                    self.table.item(r, c).setData(Qt.UserRole, s.id)
        finally:
            session.close()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def add_slot(self):
        dlg = TimeSlotDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                # Check overlap with existing slots? Allow but breaks overlapping lectures will be caught at lecture creation
                slot = TimeSlot(**data)
                session.add(slot)
                session.commit()
                QMessageBox.information(self, "Success", "Time slot added.")
                self.load_slots()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def edit_slot(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a slot to edit.")
            return
        session = get_session()
        try:
            slot = session.query(TimeSlot).filter(TimeSlot.id==sid).first()
            if not slot:
                return
            dlg = TimeSlotDialog(self, slot)
            session.expunge(slot)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    s = s2.query(TimeSlot).filter(TimeSlot.id==sid).first()
                    for k,v in data.items():
                        setattr(s, k, v)
                    s2.commit()
                    QMessageBox.information(self, "Success", "Time slot updated.")
                    self.load_slots()
                except Exception as e:
                    s2.rollback()
                    QMessageBox.critical(self, "Error", str(e))
                finally:
                    s2.close()
        except Exception as e:
            try:
                session.close()
            except:
                pass
            QMessageBox.critical(self, "Error", str(e))

    def delete_slot(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a slot to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this time slot?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            slot = session.query(TimeSlot).filter(TimeSlot.id==sid).first()
            if slot:
                session.delete(slot)
                session.commit()
                QMessageBox.information(self, "Deleted", "Time slot deleted.")
                self.load_slots()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
