from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import TeacherAvailability, Teacher, WorkingDay
from app.ui.dialogs import AvailabilityDialog

class AvailabilityView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        title = QLabel("Teacher Availability")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        layout.addWidget(title)
        sub = QLabel("Mark when a teacher is unavailable (e.g., leave, meeting). Room availability is automatic — if a room is booked for a lecture, the system will block overlapping bookings and show a conflict.")
        sub.setStyleSheet("color: #64748B; font-size: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("＋ Add Teacher Unavailability")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_teacher_avail)
        btns.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_teacher_avail)
        btns.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_teacher_avail)
        btns.addWidget(self.del_btn)
        btns.addStretch()
        hint = QLabel("Room is auto-checked — no need to mark room unavailability.")
        hint.setStyleSheet("color: #64748B; font-size: 11px;")
        btns.addWidget(hint)
        layout.addLayout(btns)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Teacher", "Day", "Time", "Reason"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh(self):
        self.load_teacher()

    def load_teacher(self):
        session = get_session()
        try:
            avs = session.query(TeacherAvailability).order_by(TeacherAvailability.teacher_id).all()
            self.table.setRowCount(len(avs))
            for r, av in enumerate(avs):
                self.table.setItem(r, 0, QTableWidgetItem(str(av.id)))
                self.table.setItem(r, 1, QTableWidgetItem(av.teacher.name if av.teacher else str(av.teacher_id)))
                self.table.setItem(r, 2, QTableWidgetItem(av.day.name if av.day else str(av.day_id)))
                self.table.setItem(r, 3, QTableWidgetItem(f"{av.start_time}-{av.end_time}"))
                self.table.setItem(r, 4, QTableWidgetItem(av.reason or ""))
                for c in range(5):
                    it = self.table.item(r, c)
                    if it:
                        it.setData(Qt.UserRole, av.id)
            if len(avs) == 0:
                self.table.setRowCount(1)
                empty = QTableWidgetItem("No teacher unavailability — all teachers are available. Add only if needed.")
                empty.setFlags(empty.flags() & ~Qt.ItemIsEditable)
                empty.setForeground(Qt.gray)
                self.table.setItem(0, 1, empty)
                self.table.setSpan(0, 1, 1, 4)
        finally:
            session.close()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        try:
            return int(item.text()) if item and item.text().isdigit() else None
        except:
            return None

    def add_teacher_avail(self):
        dlg = AvailabilityDialog(self, is_teacher=True)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                av = TeacherAvailability(teacher_id=data["entity_id"], day_id=data["day_id"], start_time=data["start_time"], end_time=data["end_time"], is_unavailable=True, reason=data["reason"])
                session.add(av)
                session.commit()
                QMessageBox.information(self, "Added", "Teacher unavailability marked. Timetable will block this slot.")
                self.load_teacher()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()
                try:
                    dlg.session.close()
                except:
                    pass

    def edit_teacher_avail(self):
        aid = self._selected_id()
        if not aid:
            QMessageBox.warning(self, "Select", "Please select an entry to edit.")
            return
        session = get_session()
        try:
            av = session.query(TeacherAvailability).filter(TeacherAvailability.id==aid).first()
            if not av:
                return
            dlg = AvailabilityDialog(self, existing=av, is_teacher=True)
            session.expunge(av)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    av2 = s2.query(TeacherAvailability).filter(TeacherAvailability.id==aid).first()
                    av2.teacher_id = data["entity_id"]
                    av2.day_id = data["day_id"]
                    av2.start_time = data["start_time"]
                    av2.end_time = data["end_time"]
                    av2.reason = data["reason"]
                    s2.commit()
                    QMessageBox.information(self, "Updated", "Updated.")
                    self.load_teacher()
                except Exception as e:
                    s2.rollback()
                    QMessageBox.critical(self, "Error", str(e))
                finally:
                    s2.close()
                    try:
                        dlg.session.close()
                    except:
                        pass
        except Exception as e:
            try:
                session.close()
            except:
                pass
            QMessageBox.critical(self, "Error", str(e))

    def delete_teacher_avail(self):
        aid = self._selected_id()
        if not aid:
            QMessageBox.warning(self, "Select", "Please select an entry to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this unavailability?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            av = session.query(TeacherAvailability).filter(TeacherAvailability.id==aid).first()
            if av:
                session.delete(av)
                session.commit()
                self.load_teacher()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
