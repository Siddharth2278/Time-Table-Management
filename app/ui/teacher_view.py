from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QDialog, QComboBox, QFormLayout, QDialogButtonBox,
    QTabWidget, QTextEdit, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from functools import partial
from app.database import get_session
from app.models import Teacher, TimetableEntry
from app.services.timetable_service import TimetableService
from app.ui.dialogs import TeacherDialog
from app.ui.icons import icon
from app.ui.widgets import page_header, show_toast

STATUS_OK = ("#166534", "#DCFCE7")
STATUS_BAD = ("#991B1B", "#FEE2E2")


class TeacherView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        self.add_btn = QPushButton(" Add Teacher")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setIcon(icon("plus", "#FFFFFF", 16))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(lambda: self.add_teacher())
        layout.addWidget(page_header(
            "Teachers", "Manage faculty and availability.", self.add_btn))

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
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
        self.search.setPlaceholderText("Search teachers...")
        self.search.textChanged.connect(self.load)
        card_layout.addWidget(self.search)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["NAME", "EMAIL", "DEPARTMENT", "DESIGNATION", "STATUS", "ACTIONS"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 96)
        self.table.cellDoubleClicked.connect(
            lambda r, c: self.edit_teacher(self._id_at_row(r)))
        card_layout.addWidget(self.table)

        self.empty_label = QLabel("No teachers yet. Click “Add Teacher” to add your first faculty member.")
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

    @staticmethod
    def _pill(text, colors):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        item.setForeground(QColor(colors[0]))
        item.setBackground(QColor(colors[1]))
        return item

    def load(self):
        session = get_session()
        try:
            q = session.query(Teacher).order_by(Teacher.name)
            search = self.search.text().strip().lower()
            teachers = q.all()
            if search:
                teachers = [t for t in teachers if search in (t.name or "").lower() or search in (t.email or "").lower() or search in (t.department or "").lower()]
            self.table.setRowCount(0)
            self.table.setRowCount(len(teachers))
            mono = QFont("Cascadia Code")
            for r, t in enumerate(teachers):
                self.table.setItem(r, 0, QTableWidgetItem(t.name))
                email_item = QTableWidgetItem(t.email or "")
                email_item.setFont(mono)
                self.table.setItem(r, 1, email_item)
                self.table.setItem(r, 2, QTableWidgetItem(t.department or ""))
                self.table.setItem(r, 3, QTableWidgetItem(t.designation or ""))
                self.table.setItem(
                    r, 4, self._pill(t.status or "", STATUS_OK if t.status == "Active" else STATUS_BAD))
                for c in range(5):
                    self.table.item(r, c).setData(Qt.UserRole, t.id)
                cell = QWidget()
                row_layout = QHBoxLayout(cell)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(4)
                edit = QPushButton()
                edit.setObjectName("RowButton")
                edit.setIcon(icon("pencil", "#8A94A0", 16))
                edit.setToolTip("Edit")
                edit.setCursor(Qt.PointingHandCursor)
                edit.clicked.connect(partial(self.edit_teacher, t.id))
                row_layout.addWidget(edit)
                delete = QPushButton()
                delete.setObjectName("RowButtonDanger")
                delete.setIcon(icon("trash", "#D6544C", 16))
                delete.setToolTip("Delete")
                delete.setCursor(Qt.PointingHandCursor)
                delete.clicked.connect(partial(self.delete_teacher, t.id))
                row_layout.addWidget(delete)
                row_layout.addStretch()
                self.table.setCellWidget(r, 5, cell)
            self.count_label.setText(
                f"{len(teachers)} teacher{'s' if len(teachers) != 1 else ''}")
            self.empty_label.setVisible(len(teachers) == 0)
        finally:
            session.close()

    def add_teacher(self):
        dlg = TeacherDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                t = Teacher(**data)
                session.add(t)
                session.commit()
                show_toast(self, "Teacher added.")
                self.load()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def edit_teacher(self, tid=None):
        if tid is None:
            tid = self._selected_id()
        if not tid:
            QMessageBox.warning(self, "Select", "Please select a teacher to edit.")
            return
        session = get_session()
        try:
            teacher = session.query(Teacher).filter(Teacher.id == tid).first()
            if not teacher:
                return
            dlg = TeacherDialog(self, teacher)
            session.expunge(teacher)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    t2 = s2.query(Teacher).filter(Teacher.id == tid).first()
                    for k, v in data.items():
                        setattr(t2, k, v)
                    s2.commit()
                    show_toast(self, "Teacher updated.")
                    self.load()
                except Exception as e:
                    s2.rollback()
                    QMessageBox.critical(self, "Error", str(e))
                finally:
                    s2.close()
            return
        except Exception as e:
            try:
                session.close()
            except Exception:
                pass
            QMessageBox.critical(self, "Error", str(e))

    def delete_teacher(self, tid=None):
        if tid is None:
            tid = self._selected_id()
        if not tid:
            QMessageBox.warning(self, "Select", "Please select a teacher to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this teacher? Assigned lectures will prevent deletion if they exist.\n\nDelete?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            cnt = session.query(TimetableEntry).filter(TimetableEntry.teacher_id == tid).count()
            if cnt > 0:
                QMessageBox.critical(self, "Cannot Delete", f"This teacher has {cnt} scheduled lecture(s). Delete or reassign those lectures first.")
                return
            t = session.query(Teacher).filter(Teacher.id == tid).first()
            if t:
                session.delete(t)
                session.commit()
                show_toast(self, "Teacher deleted.")
                self.load()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def view_timetable(self, tid=None):
        if tid is None:
            tid = self._selected_id()
        if not tid:
            QMessageBox.warning(self, "Select", "Please select a teacher to view timetable.")
            return
        session = get_session()
        try:
            teacher = session.query(Teacher).filter(Teacher.id == tid).first()
            entries = TimetableService.get_teacher_timetable(session, tid)
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Timetable - {teacher.name if teacher else ''}")
            dlg.setMinimumSize(720, 400)
            layout = QVBoxLayout(dlg)
            info = QLabel(f"Teacher: {teacher.name if teacher else ''} | Total Lectures: {len(entries)}")
            info.setObjectName("SectionTitle")
            layout.addWidget(info)
            tbl = QTableWidget(len(entries), 5)
            tbl.setHorizontalHeaderLabels(["DAY", "TIME", "SEMESTER", "SUBJECT", "ROOM"])
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.setAlternatingRowColors(True)
            tbl.verticalHeader().setVisible(False)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for r, e in enumerate(sorted(entries, key=lambda x: (x.day.sort_order if x.day else 0, x.start_time))):
                tbl.setItem(r, 0, QTableWidgetItem(e.day.name if e.day else ""))
                tbl.setItem(r, 1, QTableWidgetItem(f"{e.start_time}-{e.end_time}"))
                tbl.setItem(r, 2, QTableWidgetItem(e.semester.name if e.semester else ""))
                tbl.setItem(r, 3, QTableWidgetItem(f"{e.subject.code if e.subject else ''} - {e.subject.name if e.subject else ''}"))
                tbl.setItem(r, 4, QTableWidgetItem(f"{e.room.name if e.room else ''} ({e.room.room_number if e.room else ''})"))
            layout.addWidget(tbl)
            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            layout.addWidget(btns)
            dlg.exec()
        finally:
            session.close()
