from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt
from app.database import get_session
from app.models import Subject, Semester, Teacher, TimetableEntry
from app.ui.dialogs import SubjectDialog
from app.services.conflict_service import ConflictService

class SubjectView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel("Subjects")
        title.setObjectName("PageTitle")
        top.addWidget(title)
        top.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by code, name...")
        self.search.setMinimumWidth(260)
        self.search.textChanged.connect(self.load)
        top.addWidget(self.search)
        self.sem_filter = QComboBox()
        self.sem_filter.addItem("All Semesters", None)
        # sems populated in refresh
        self.sem_filter.currentIndexChanged.connect(self.load)
        top.addWidget(self.sem_filter)
        layout.addLayout(top)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("＋ Add Subject")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_subject)
        btns.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_subject)
        btns.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_subject)
        btns.addWidget(self.del_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Code", "Name", "Semester", "Type", "Req/Wk", "Duration", "Teacher"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.cellDoubleClicked.connect(lambda r,c: self.edit_subject())
        layout.addWidget(self.table)

        # Info about weekly requirement
        self.info = QLabel("")
        self.info.setObjectName("PageSubtitle")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

    def refresh(self):
        # Populate sem filter
        session = get_session()
        try:
            sems = session.query(Semester).order_by(Semester.id).all()
            cur = self.sem_filter.currentData()
            self.sem_filter.blockSignals(True)
            self.sem_filter.clear()
            self.sem_filter.addItem("All Semesters", None)
            for s in sems:
                self.sem_filter.addItem(s.name, s.id)
            if cur is not None:
                idx = self.sem_filter.findData(cur)
                if idx >= 0:
                    self.sem_filter.setCurrentIndex(idx)
            self.sem_filter.blockSignals(False)
        finally:
            session.close()
        self.load()

    def load(self):
        session = get_session()
        try:
            q = session.query(Subject).order_by(Subject.code)
            search = self.search.text().strip().lower()
            sem_filter = self.sem_filter.currentData()
            subjects = q.all()
            if sem_filter is not None:
                subjects = [s for s in subjects if s.semester_id == sem_filter]
            if search:
                subjects = [s for s in subjects if search in (s.code or "").lower() or search in (s.name or "").lower()]
            self.table.setRowCount(len(subjects))
            for r, s in enumerate(subjects):
                # For weekly tracking, calculate scheduled/required
                scheduled = session.query(TimetableEntry).filter(TimetableEntry.subject_id==s.id).count()
                self.table.setItem(r, 0, QTableWidgetItem(str(s.id)))
                self.table.setItem(r, 1, QTableWidgetItem(s.code))
                self.table.setItem(r, 2, QTableWidgetItem(s.name))
                sem_name = s.semester.name if s.semester else f"Sem {s.semester_id}"
                self.table.setItem(r, 3, QTableWidgetItem(sem_name))
                self.table.setItem(r, 4, QTableWidgetItem(s.subject_type))
                req_item = QTableWidgetItem(f"{scheduled}/{s.required_lectures_per_week}")
                from PySide6.QtGui import QColor as _QC
                if scheduled < s.required_lectures_per_week:
                    req_item.setForeground(_QC("#D97706"))
                elif scheduled == s.required_lectures_per_week:
                    req_item.setForeground(_QC("#059669"))
                else:
                    req_item.setForeground(_QC("#DC2626"))
                self.table.setItem(r, 5, QTableWidgetItem(f"{scheduled}/{s.required_lectures_per_week}"))
                self.table.setItem(r, 6, QTableWidgetItem(f"{s.lecture_duration} mins"))
                teacher_name = s.assigned_teacher.name if s.assigned_teacher else "-"
                self.table.setItem(r, 7, QTableWidgetItem(teacher_name))
                for c in range(8):
                    it = self.table.item(r, c)
                    it.setData(Qt.UserRole, s.id)
            # Update info
            total_req = sum(s.required_lectures_per_week for s in subjects)
            total_sched = sum(session.query(TimetableEntry).filter(TimetableEntry.subject_id==s.id).count() for s in subjects)
            self.info.setText(f"Showing {len(subjects)} subjects | Total Required: {total_req} | Scheduled: {total_sched} | Remaining: {max(0, total_req-total_sched)}")
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

    def add_subject(self):
        session = get_session()
        try:
            dlg = SubjectDialog(self, session=session)
            # dialog will close session on close, so need to handle carefully
            # Instead create without passing session
            dlg2 = SubjectDialog(self)
            session.close()
            if dlg2.exec():
                data = dlg2.get_data()
                s2 = get_session()
                try:
                    # Check duplicate code
                    exists = s2.query(Subject).filter(Subject.code==data["code"]).first()
                    if exists:
                        QMessageBox.critical(self, "Error", f"Subject code {data['code']} already exists.")
                        return
                    sub = Subject(**data)
                    s2.add(sub)
                    s2.commit()
                    QMessageBox.information(self, "Success", "Subject added.")
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
        finally:
            try:
                dlg.session.close()
            except:
                pass

    def edit_subject(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a subject to edit.")
            return
        session = get_session()
        try:
            subj = session.query(Subject).filter(Subject.id==sid).first()
            if not subj:
                return
            # Need to keep data, close session before dialog
            session.expunge(subj)
            session.close()
            dlg = SubjectDialog(self, subject=subj)
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    # Check code duplicate if changed
                    exists = s2.query(Subject).filter(Subject.code==data["code"], Subject.id!=sid).first()
                    if exists:
                        QMessageBox.critical(self, "Error", f"Subject code {data['code']} already exists.")
                        return
                    sub2 = s2.query(Subject).filter(Subject.id==sid).first()
                    for k,v in data.items():
                        setattr(sub2, k, v)
                    s2.commit()
                    QMessageBox.information(self, "Success", "Subject updated.")
                    self.load()
                except Exception as e:
                    s2.rollback()
                    QMessageBox.critical(self, "Error", str(e))
                finally:
                    s2.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            try:
                session.close()
            except:
                pass

    def delete_subject(self):
        sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a subject to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this subject?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            cnt = session.query(TimetableEntry).filter(TimetableEntry.subject_id==sid).count()
            if cnt > 0:
                QMessageBox.critical(self, "Cannot Delete", f"This subject has {cnt} scheduled lecture(s). Delete those lectures first.")
                return
            sub = session.query(Subject).filter(Subject.id==sid).first()
            if sub:
                session.delete(sub)
                session.commit()
                QMessageBox.information(self, "Deleted", "Subject deleted.")
                self.load()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
