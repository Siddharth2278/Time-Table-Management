from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QComboBox, QDialog, QVBoxLayout as VBox,
    QTableWidget as Tbl, QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from functools import partial
from app.database import get_session
from app.models import Room, TimetableEntry
from app.ui.dialogs import RoomDialog
from app.services.timetable_service import TimetableService
from app.ui.icons import icon
from app.ui.widgets import page_header, show_toast

STATUS_OK = ("#166534", "#DCFCE7")
STATUS_BAD = ("#991B1B", "#FEE2E2")


class RoomView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        self.add_btn = QPushButton(" Add Room / Lab")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setIcon(icon("plus", "#FFFFFF", 16))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(lambda: self.add_room())
        layout.addWidget(page_header(
            "Rooms & Labs", "Classrooms, laboratories and halls with capacity.", self.add_btn))

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Classroom", "Laboratory", "Seminar Hall"])
        self.type_filter.setMinimumWidth(160)
        self.type_filter.currentTextChanged.connect(self.load)
        toolbar.addWidget(self.type_filter)
        self.view_btn = QPushButton("View Timetable")
        self.view_btn.setObjectName("SecondaryButton")
        self.view_btn.setCursor(Qt.PointingHandCursor)
        self.view_btn.clicked.connect(lambda: self.view_timetable())
        toolbar.addWidget(self.view_btn)
        layout.addLayout(toolbar)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search rooms...")
        self.search.textChanged.connect(self.load)
        card_layout.addWidget(self.search)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["NAME", "ROOM NO", "TYPE", "STATUS", "ACTIONS"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 96)
        self.table.cellDoubleClicked.connect(
            lambda r, c: self.edit_room(self._id_at_row(r)))
        card_layout.addWidget(self.table)

        self.empty_label = QLabel("No rooms yet. Click “Add Room / Lab” to add your first room.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setWordWrap(True)
        card_layout.addWidget(self.empty_label)
        layout.addWidget(card)

    def refresh(self):
        self.load()

    def _id_at_row(self, row):
        item = self.table.item(row, 0)
        if item is None:
            return None
        try:
            return int(item.data(Qt.UserRole))
        except (TypeError, ValueError):
            return None

    def _selected_id(self):
        return self._id_at_row(self.table.currentRow())

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
            self.table.setRowCount(0)
            self.table.setRowCount(len(rooms))
            mono = QFont("Cascadia Code")
            for r, room in enumerate(rooms):
                self.table.setItem(r, 0, QTableWidgetItem(room.name))
                num_item = QTableWidgetItem(room.room_number)
                num_item.setFont(mono)
                self.table.setItem(r, 1, num_item)
                self.table.setItem(r, 2, QTableWidgetItem(room.type))
                status_item = QTableWidgetItem(room.status)
                status_item.setTextAlignment(Qt.AlignCenter)
                font = QFont()
                font.setBold(True)
                status_item.setFont(font)
                if room.status == "Available":
                    status_item.setForeground(QColor(STATUS_OK[0]))
                    status_item.setBackground(QColor(STATUS_OK[1]))
                else:
                    status_item.setForeground(QColor(STATUS_BAD[0]))
                    status_item.setBackground(QColor(STATUS_BAD[1]))
                self.table.setItem(r, 3, status_item)
                for c in range(4):
                    self.table.item(r, c).setData(Qt.UserRole, room.id)
                cell = QWidget()
                row_layout = QHBoxLayout(cell)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(4)
                edit = QPushButton()
                edit.setObjectName("RowButton")
                edit.setIcon(icon("pencil", "#8A94A0", 16))
                edit.setToolTip("Edit")
                edit.setCursor(Qt.PointingHandCursor)
                edit.clicked.connect(partial(self.edit_room, room.id))
                row_layout.addWidget(edit)
                delete = QPushButton()
                delete.setObjectName("RowButtonDanger")
                delete.setIcon(icon("trash", "#D6544C", 16))
                delete.setToolTip("Delete")
                delete.setCursor(Qt.PointingHandCursor)
                delete.clicked.connect(partial(self.delete_room, room.id))
                row_layout.addWidget(delete)
                row_layout.addStretch()
                self.table.setCellWidget(r, 4, cell)
            self.count_label.setText(f"{len(rooms)} room{'s' if len(rooms) != 1 else ''}")
            self.empty_label.setVisible(len(rooms) == 0)
        finally:
            session.close()

    def add_room(self):
        dlg = RoomDialog(self)
        if dlg.exec():
            data = dlg.get_data()
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
                show_toast(self, "Room / lab added.")
                self.load()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                try:
                    session.close()
                except Exception:
                    pass

    def edit_room(self, rid=None):
        if rid is None:
            rid = self._selected_id()
        if not rid:
            QMessageBox.warning(self, "Select", "Please select a room to edit.")
            return
        session = get_session()
        try:
            room = session.query(Room).filter(Room.id == rid).first()
            if not room:
                return
            dlg = RoomDialog(self, room)
            session.expunge(room)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                chk = get_session()
                try:
                    dup2 = chk.query(Room).filter(Room.name.ilike(data["name"].strip()), Room.id != rid).first()
                    if dup2:
                        QMessageBox.critical(self, "Duplicate Not Allowed", f"Another room already has name '{data['name']}' (ID {dup2.id}). Same name not allowed.")
                        chk.close()
                        return
                    chk.close()
                except Exception:
                    try:
                        chk.close()
                    except Exception:
                        pass
                s2 = get_session()
                try:
                    r2 = s2.query(Room).filter(Room.id == rid).first()
                    for k, v in data.items():
                        setattr(r2, k, v)
                    s2.commit()
                    show_toast(self, "Room / lab updated.")
                    self.load()
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

    def delete_room(self, rid=None):
        if rid is None:
            rid = self._selected_id()
        if not rid:
            QMessageBox.warning(self, "Select", "Please select a room to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this room/lab?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            cnt = session.query(TimetableEntry).filter(TimetableEntry.room_id == rid).count()
            if cnt > 0:
                QMessageBox.critical(self, "Cannot Delete", f"This room has {cnt} scheduled lecture(s). Delete those lectures first.")
                return
            room = session.query(Room).filter(Room.id == rid).first()
            if room:
                session.delete(room)
                session.commit()
                show_toast(self, "Room / lab deleted.")
                self.load()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def view_timetable(self, rid=None):
        if rid is None:
            rid = self._selected_id()
        if not rid:
            QMessageBox.warning(self, "Select", "Please select a room to view timetable.")
            return
        session = get_session()
        try:
            room = session.query(Room).filter(Room.id == rid).first()
            entries = TimetableService.get_room_timetable(session, rid)
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Room Timetable - {room.name if room else ''}")
            dlg.setMinimumSize(720, 400)
            layout = VBox(dlg)
            info = QLabel(f"Room: {room.name if room else ''} ({room.room_number if room else ''}) | Lectures: {len(entries)}")
            info.setObjectName("SectionTitle")
            layout.addWidget(info)
            tbl = Tbl(len(entries), 5)
            tbl.setHorizontalHeaderLabels(["DAY", "TIME", "SEMESTER", "SUBJECT", "TEACHER"])
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.setAlternatingRowColors(True)
            tbl.verticalHeader().setVisible(False)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for r, e in enumerate(sorted(entries, key=lambda x: (x.day.sort_order if x.day else 0, x.start_time))):
                tbl.setItem(r, 0, QTableWidgetItem(e.day.name if e.day else ""))
                tbl.setItem(r, 1, QTableWidgetItem(f"{e.start_time}-{e.end_time}"))
                tbl.setItem(r, 2, QTableWidgetItem(e.semester.name if e.semester else ""))
                tbl.setItem(r, 3, QTableWidgetItem(f"{e.subject.code if e.subject else ''} - {e.subject.name if e.subject else ''}"))
                tbl.setItem(r, 4, QTableWidgetItem(e.teacher.name if e.teacher else ""))
            layout.addWidget(tbl)
            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            layout.addWidget(btns)
            dlg.exec()
        finally:
            session.close()
