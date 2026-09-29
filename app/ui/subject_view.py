from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QComboBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from functools import partial
from app.database import get_session
from app.models import Subject, Semester, Teacher, TimetableEntry
from app.ui.dialogs import SubjectDialog
from app.ui.icons import icon
from app.ui.widgets import page_header, show_toast

TYPE_COLORS = ("#3B4D63", "#E4EAF2")


class SubjectView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        self.add_btn = QPushButton(" Add Subject")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setIcon(icon("plus", "#FFFFFF", 16))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(lambda: self.add_subject())
        layout.addWidget(page_header(
            "Subjects", "Courses linked to semesters, teachers and rooms.", self.add_btn))

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
        self.sem_filter = QComboBox()
        self.sem_filter.addItem("All Semesters", None)
        self.sem_filter.setMinimumWidth(170)
        self.sem_filter.currentIndexChanged.connect(self.load)
        toolbar.addWidget(self.sem_filter)
        layout.addLayout(toolbar)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search subjects...")
        self.search.textChanged.connect(self.load)
        card_layout.addWidget(self.search)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["CODE", "NAME", "SEMESTER", "TYPE", "REQ/WK", "TEACHER", "ACTIONS"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 96)
        self.table.cellDoubleClicked.connect(
            lambda r, c: self.edit_subject(self._id_at_row(r)))
        card_layout.addWidget(self.table)

        self.empty_label = QLabel("No subjects yet. Click “Add Subject” to add your first course.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setWordWrap(True)
        card_layout.addWidget(self.empty_label)

        self.info = QLabel("")
        self.info.setObjectName("Muted")
        self.info.setWordWrap(True)
        card_layout.addWidget(self.info)
        layout.addWidget(card)

    def refresh(self):
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
            q = session.query(Subject).order_by(Subject.code)
            search = self.search.text().strip().lower()
            sem_filter = self.sem_filter.currentData()
            subjects = q.all()
            if sem_filter is not None:
                subjects = [s for s in subjects if s.semester_id == sem_filter]
            if search:
                subjects = [s for s in subjects if search in (s.code or "").lower() or search in (s.name or "").lower()]
            self.table.setRowCount(0)
            self.table.setRowCount(len(subjects))
            mono = QFont("Cascadia Code")
            for r, s in enumerate(subjects):
                scheduled = session.query(TimetableEntry).filter(TimetableEntry.subject_id == s.id).count()
                code_item = QTableWidgetItem(s.code)
                code_item.setFont(mono)
                self.table.setItem(r, 0, code_item)
                self.table.setItem(r, 1, QTableWidgetItem(s.name))
                sem_name = s.semester.name if s.semester else f"Sem {s.semester_id}"
                self.table.setItem(r, 2, QTableWidgetItem(sem_name))
                type_item = QTableWidgetItem(s.subject_type or "")
                type_item.setTextAlignment(Qt.AlignCenter)
                type_item.setForeground(QColor(TYPE_COLORS[0]))
                type_item.setBackground(QColor(TYPE_COLORS[1]))
                self.table.setItem(r, 3, type_item)
                req_item = QTableWidgetItem(f"{scheduled}/{s.required_lectures_per_week}")
                req_item.setFont(mono)
                req_item.setTextAlignment(Qt.AlignCenter)
                if scheduled < s.required_lectures_per_week:
                    req_item.setForeground(QColor("#D97706"))
                elif scheduled == s.required_lectures_per_week:
                    req_item.setForeground(QColor("#22B07D"))
                else:
                    req_item.setForeground(QColor("#E05D52"))
                self.table.setItem(r, 4, req_item)
                teacher_name = s.assigned_teacher.name if s.assigned_teacher else "-"
                self.table.setItem(r, 5, QTableWidgetItem(teacher_name))
                for c in range(6):
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
                edit.clicked.connect(partial(self.edit_subject, s.id))
                row_layout.addWidget(edit)
                delete = QPushButton()
                delete.setObjectName("RowButtonDanger")
                delete.setIcon(icon("trash", "#D6544C", 16))
                delete.setToolTip("Delete")
                delete.setCursor(Qt.PointingHandCursor)
                delete.clicked.connect(partial(self.delete_subject, s.id))
                row_layout.addWidget(delete)
                row_layout.addStretch()
                self.table.setCellWidget(r, 6, cell)
            total_req = sum(s.required_lectures_per_week for s in subjects)
            total_sched = sum(session.query(TimetableEntry).filter(TimetableEntry.subject_id == s.id).count() for s in subjects)
            self.count_label.setText(
                f"{len(subjects)} subject{'s' if len(subjects) != 1 else ''}")
            self.info.setText(
                f"Total Required: {total_req}  •  Scheduled: {total_sched}  •  Remaining: {max(0, total_req - total_sched)}")
            self.empty_label.setVisible(len(subjects) == 0)
        finally:
            session.close()

    def add_subject(self):
        session = get_session()
        try:
            dlg = SubjectDialog(self, session=session)
            dlg2 = SubjectDialog(self)
            session.close()
            if dlg2.exec():
                data = dlg2.get_data()
                s2 = get_session()
                try:
                    exists = s2.query(Subject).filter(Subject.code == data["code"]).first()
                    if exists:
                        QMessageBox.critical(self, "Error", f"Subject code {data['code']} already exists.")
                        return
                    sub = Subject(**data)
                    s2.add(sub)
                    s2.commit()
                    show_toast(self, "Subject added.")
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
        finally:
            try:
                dlg.session.close()
            except Exception:
                pass

    def edit_subject(self, sid=None):
        if sid is None:
            sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a subject to edit.")
            return
        session = get_session()
        try:
            subj = session.query(Subject).filter(Subject.id == sid).first()
            if not subj:
                return
            session.expunge(subj)
            session.close()
            dlg = SubjectDialog(self, subject=subj)
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    exists = s2.query(Subject).filter(Subject.code == data["code"], Subject.id != sid).first()
                    if exists:
                        QMessageBox.critical(self, "Error", f"Subject code {data['code']} already exists.")
                        return
                    sub2 = s2.query(Subject).filter(Subject.id == sid).first()
                    for k, v in data.items():
                        setattr(sub2, k, v)
                    s2.commit()
                    show_toast(self, "Subject updated.")
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
            except Exception:
                pass

    def delete_subject(self, sid=None):
        if sid is None:
            sid = self._selected_id()
        if not sid:
            QMessageBox.warning(self, "Select", "Please select a subject to delete.")
            return
        if QMessageBox.question(self, "Confirm", "Delete this subject?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            cnt = session.query(TimetableEntry).filter(TimetableEntry.subject_id == sid).count()
            if cnt > 0:
                QMessageBox.critical(self, "Cannot Delete", f"This subject has {cnt} scheduled lecture(s). Delete those lectures first.")
                return
            sub = session.query(Subject).filter(Subject.id == sid).first()
            if sub:
                session.delete(sub)
                session.commit()
                show_toast(self, "Subject deleted.")
                self.load()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
