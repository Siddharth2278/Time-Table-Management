from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QComboBox, QDialog, QVBoxLayout as VBox, QTableWidget as Tbl, QDialogButtonBox
)
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import Room, TimetableEntry
from app.ui.dialogs import RoomDialog
from app.services.timetable_service import TimetableService

class RoomView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel("Rooms & Laboratories")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: var(--text-primary);")
        top.addWidget(title)
        top.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search rooms/labs...")
        self.search.setMinimumWidth(260)
        self.search.textChanged.connect(self.load)
        top.addWidget(self.search)
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Classroom", "Laboratory", "Seminar Hall"])
        self.type_filter.currentTextChanged.connect(self.load)
        top.addWidget(self.type_filter)
        layout.addLayout(top)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("＋ Add Room/Lab")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_room)
        btns.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_room)
        btns.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_room)
        btns.addWidget(self.del_btn)
        self.view_btn = QPushButton("View Timetable")
        self.view_btn.setObjectName("SecondaryButton")
        self.view_btn.clicked.connect(self.view_timetable)
        btns.addWidget(self.view_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "NAME", "ROOM NO", "TYPE", "STATUS"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        # Alternating row colors use QSS var() values
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(lambda r,c: self.edit_room())
        layout.addWidget(self.table)

    def refresh(self):
        self.load()

    def load(self):
        session = get_session()
        try:
            rooms = session.query(Room).order_by(Room.name).all()
            search = self.search.text().strip().lower()
            ftype = self.type_filter.currentText()
            if ftype != "All Types":
                rooms = [r for r in rooms if r.type == ftype]
            if search:
                rooms = [r for r in rooms if search in (r.name or "").lower() or search in (r.room_number or "").lower()]
            self.table.setRowCount(len(rooms))
            for r, room in enumerate(rooms):
                self.table.setItem(r, 0, QTableWidgetItem(str(room.id)))
                self.table.setItem(r, 1, QTableWidgetItem(room.name))
                self.table.setItem(r, 2, QTableWidgetItem(room.room_number))
                self.table.setItem(r, 3, QTableWidgetItem(room.type))
                status_item = QTableWidgetItem(room.status)
                if room.status == "Available":
                    status_item.setForeground(Qt.darkGreen)
                else:
                    status_item.setForeground(Qt.red)
                self.table.setItem(r, 4, status_item)
                for c in range(5):
                    it = self.table.item(r, c)
                    if it:
                        it.setData(Qt.UserRole, room.id)
        finally:
            session.close()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def add_room(self):
        dlg = RoomDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            # Duplicate exact name check — Lab 1 A vs Lab 1 B allowed, same name not
            session = get_session()
            try:
                dup = session.query(Room).filter(Room.name.ilike(data["name"].strip())).first()
                if dup:
                    QMessageBox.critical(self, "Duplicate Not Allowed", f"Room name '{data['name']}' already exists (ID {dup.id}: {dup.name} - {dup.room_number}).\n\nSame name is not allowed.\nLab 1 A and Lab 1 B are allowed because they are different names.")
                    session.close()
                    return
                room = Room(**data)
                session.add(room)
                session.commit()
                QMessageBox.information(self, "Success", "Room/Lab added.")
                self.load()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                try:
                    session.close()
                except:
                    pass

    def edit_room(self):
        rid = self._selected_id()
        if not rid:
            QMessageBox.warning(self, "Select", "Please select a room to edit.")
            return
        session = get_session()
        try:
            room = session.query(Room).filter(Room.id==rid).first()
            if not room:
                return
            dlg = RoomDialog(self, room)
            session.expunge(room)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                # Duplicate check on edit — exclude self
                chk = get_session()
                try:
                    dup2 = chk.query(Room).filter(Room.name.ilike(data["name"].strip()), Room.id != rid).first()
                    if dup2:
                        QMessageBox.critical(self, "Duplicate Not Allowed", f"Another room already has name '{data['name']}' (ID {dup2.id}). Same name not allowed.")
                        chk.close()
                        return
                    chk.close()
                except:
                    try:
                        chk.close()
                    except:
                        pass
                s2 = get_session()
                try:
                    r2 = s2.query(Room).filter(Room.id==rid).first()
                    for k,v in data.items():
                        setattr(r2, k, v)
                    s2.commit()
                    QMessageBox.information(self, "Success", "Room/Lab updated.")
                    self.load()
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

    def delete_room(self):
        rid = self._selected_id()
        if not rid:
            QMessageBox.warning(self, "Select", "Please select a room to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this room/lab?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            cnt = session.query(TimetableEntry).filter(TimetableEntry.room_id==rid).count()
            if cnt > 0:
                QMessageBox.critical(self, "Cannot Delete", f"This room has {cnt} scheduled lecture(s). Delete those lectures first.")
                return
            room = session.query(Room).filter(Room.id==rid).first()
            if room:
                session.delete(room)
                session.commit()
                QMessageBox.information(self, "Deleted", "Room/Lab deleted.")
                self.load()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def view_timetable(self):
        rid = self._selected_id()
        if not rid:
            QMessageBox.warning(self, "Select", "Please select a room to view timetable.")
            return
        session = get_session()
        try:
            room = session.query(Room).filter(Room.id==rid).first()
            entries = TimetableService.get_room_timetable(session, rid)
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Room Timetable - {room.name if room else ''}")
            dlg.setMinimumSize(720, 400)
            layout = VBox(dlg)
            info = QLabel(f"Room: {room.name if room else ''} ({room.room_number if room else ''}) | Lectures: {len(entries)}")
            info.setStyleSheet("font-weight: 600;")
            layout.addWidget(info)
            tbl = Tbl(len(entries), 5)
            tbl.setHorizontalHeaderLabels(["Day", "Time", "Semester", "Subject", "Teacher"])
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.setAlternatingRowColors(True)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for r, e in enumerate(sorted(entries, key=lambda x: (x.day.sort_order if x.day else 0, x.start_time))):
                tbl.setItem(r, 0, QTableWidgetItem(e.day.name if e.day else ""))
                tbl.setItem(r, 1, QTableWidgetItem(f"{e.start_time}-{e.end_time}"))
                tbl.setItem(r, 2, QTableWidgetItem(e.semester.name if e.semester else ""))
                tbl.setItem(r, 3, QTableWidgetItem(f"{e.subject.code if e.subject else ''} - {e.subject.name if e.subject else ''}"))
                tbl.setItem(r, 4, QTableWidgetItem(e.teacher.name if e.teacher else ""))
            layout.addWidget(tbl)
            btns = QDialogButtonBox(QDialogButtonBox.Close)
            btns.rejected.connect(dlg.reject)
            btns.accepted.connect(dlg.accept)
            layout.addWidget(btns)
            dlg.exec()
        finally:
            session.close()
