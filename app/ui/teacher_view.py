from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QDialog, QComboBox, QFormLayout, QDialogButtonBox,
    QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import Teacher, TimetableEntry
from app.services.timetable_service import TimetableService
from app.ui.dialogs import TeacherDialog

class TeacherView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        top = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)
        title = QLabel("Teachers")
        title.setObjectName("PageTitle")
        title_col.addWidget(title)
        sub = QLabel("Manage faculty and availability.")
        sub.setObjectName("PageSubtitle")
        title_col.addWidget(sub)
        top.addLayout(title_col)
        top.addStretch()
        self.add_btn = QPushButton("＋ Add Teacher")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_teacher)
        top.addWidget(self.add_btn)
        layout.addLayout(top)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search teacher by name, email, department...")
        self.search.textChanged.connect(self.load)
        layout.addWidget(self.search)

        btns = QHBoxLayout()
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_teacher)
        btns.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_teacher)
        btns.addWidget(self.del_btn)
        self.view_btn = QPushButton("View Timetable")
        self.view_btn.setObjectName("SecondaryButton")
        self.view_btn.clicked.connect(self.view_timetable)
        btns.addWidget(self.view_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Email", "Department", "Designation", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.cellDoubleClicked.connect(lambda r,c: self.edit_teacher())
        layout.addWidget(self.table)

    def refresh(self):
        self.load()

    def load(self):
        session = get_session()
        try:
            q = session.query(Teacher).order_by(Teacher.name)
            search = self.search.text().strip().lower()
            teachers = q.all()
            if search:
                teachers = [t for t in teachers if search in (t.name or "").lower() or search in (t.email or "").lower() or search in (t.department or "").lower()]
            self.table.setRowCount(len(teachers))
            for r, t in enumerate(teachers):
                self.table.setItem(r, 0, QTableWidgetItem(str(t.id)))
                self.table.setItem(r, 1, QTableWidgetItem(t.name))
                self.table.setItem(r, 2, QTableWidgetItem(t.email or ""))
                self.table.setItem(r, 3, QTableWidgetItem(t.department or ""))
                self.table.setItem(r, 4, QTableWidgetItem(t.designation or ""))
                status_item = QTableWidgetItem(t.status or "")
                from PySide6.QtGui import QColor as _QC
                if t.status == "Active":
                    status_item.setForeground(_QC("#059669"))
                else:
                    status_item.setForeground(_QC("#DC2626"))
                self.table.setItem(r, 5, status_item)
                for c in range(6):
                    it = self.table.item(r, c)
                    it.setData(Qt.UserRole, t.id)
        finally:
            session.close()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item:
            return int(item.text())
        return None

    def add_teacher(self):
        dlg = TeacherDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                t = Teacher(**data)
                session.add(t)
                session.commit()
                QMessageBox.information(self, "Success", "Teacher added.")
                self.load()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def edit_teacher(self):
        tid = self._selected_id()
        if not tid:
            QMessageBox.warning(self, "Select", "Please select a teacher to edit.")
            return
        session = get_session()
        try:
            teacher = session.query(Teacher).filter(Teacher.id==tid).first()
            if not teacher:
                return
            # need to detach before dialog closes session
            dlg = TeacherDialog(self, teacher)
            # keep session alive until dialog done? dialog doesn't need session
            session.expunge(teacher)
            session.close()
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    t2 = s2.query(Teacher).filter(Teacher.id==tid).first()
                    for k,v in data.items():
                        setattr(t2, k, v)
                    s2.commit()
                    QMessageBox.information(self, "Success", "Teacher updated.")
                    self.load()
                except Exception as e:
                    s2.rollback()
                    QMessageBox.critical(self, "Error", str(e))
                finally:
                    s2.close()
            else:
                # dialog cancelled, session already closed
                pass
            return
        except Exception as e:
            try:
                session.close()
            except:
                pass
            QMessageBox.critical(self, "Error", str(e))

    def delete_teacher(self):
        tid = self._selected_id()
        if not tid:
            QMessageBox.warning(self, "Select", "Please select a teacher to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this teacher? Assigned lectures will prevent deletion if they exist.\n\nDelete?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            # Check if teacher has timetable entries
            cnt = session.query(TimetableEntry).filter(TimetableEntry.teacher_id==tid).count()
            if cnt > 0:
                QMessageBox.critical(self, "Cannot Delete", f"This teacher has {cnt} scheduled lecture(s). Delete or reassign those lectures first.")
                return
            t = session.query(Teacher).filter(Teacher.id==tid).first()
            if t:
                session.delete(t)
                session.commit()
                QMessageBox.information(self, "Deleted", "Teacher deleted.")
                self.load()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def view_timetable(self):
        tid = self._selected_id()
        if not tid:
            QMessageBox.warning(self, "Select", "Please select a teacher to view timetable.")
            return
        session = get_session()
        try:
            teacher = session.query(Teacher).filter(Teacher.id==tid).first()
            entries = TimetableService.get_teacher_timetable(session, tid)
            # Show dialog with table
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Timetable - {teacher.name if teacher else ''}")
            dlg.setMinimumSize(720, 400)
            layout = QVBoxLayout(dlg)
            info = QLabel(f"Teacher: {teacher.name if teacher else ''} | Total Lectures: {len(entries)}")
            info.setObjectName("SectionTitle")
            layout.addWidget(info)
            tbl = QTableWidget(len(entries), 5)
            tbl.setHorizontalHeaderLabels(["Day", "Time", "Semester", "Subject", "Room"])
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.setAlternatingRowColors(True)
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
