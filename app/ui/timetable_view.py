from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QMenu, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QColor, QAction
from app.database import get_session
from app.models import Semester, WorkingDay, TimetableEntry, TimeSlot, Setting
from app.services.timetable_service import TimetableService
from app.services.conflict_service import ConflictService
from app.services.export_service import export_csv, export_excel, export_pdf
from app.ui.dialogs import LectureDialog, TimeSlotDialog
from app.utils.helpers import time_to_minutes

class TimetableView(QWidget):
    def __init__(self):
        super().__init__()
        self.current_semester_id = None
        self.entries = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        # Top bar
        top = QHBoxLayout()
        title = QLabel("Timetable Builder")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #1E2A3A;")
        top.addWidget(title)
        top.addStretch()
        self.sem_combo = QComboBox()
        self.sem_combo.setMinimumWidth(180)
        self.sem_combo.currentIndexChanged.connect(self.on_semester_changed)
        top.addWidget(QLabel("Semester:"))
        top.addWidget(self.sem_combo)
        layout.addLayout(top)

        # Actions bar
        actions = QHBoxLayout()
        self.add_btn = QPushButton("＋ Add Lecture")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_lecture)
        actions.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_lecture)
        actions.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_lecture)
        actions.addWidget(self.del_btn)
        self.generate_btn = QPushButton("Generate Timetable")
        self.generate_btn.setObjectName("PrimaryButton")
        self.generate_btn.clicked.connect(self.generate_timetable)
        actions.addWidget(self.generate_btn)
        self.format_btn = QPushButton("Format Photo")
        self.format_btn.setObjectName("SecondaryButton")
        self.format_btn.clicked.connect(self.choose_format_photo)
        actions.addWidget(self.format_btn)
        actions.addStretch()
        self.find_btn = QPushButton("Find Available Slot")
        self.find_btn.setObjectName("SecondaryButton")
        self.find_btn.clicked.connect(self.find_available)
        actions.addWidget(self.find_btn)
        # Export
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("SecondaryButton")
        self.export_csv_btn.clicked.connect(lambda: self.export("csv"))
        actions.addWidget(self.export_csv_btn)
        self.export_excel_btn = QPushButton("Excel")
        self.export_excel_btn.setObjectName("SecondaryButton")
        self.export_excel_btn.clicked.connect(lambda: self.export("excel"))
        actions.addWidget(self.export_excel_btn)
        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.setObjectName("SecondaryButton")
        self.export_pdf_btn.clicked.connect(lambda: self.export("pdf"))
        actions.addWidget(self.export_pdf_btn)
        self.print_btn = QPushButton("Print")
        self.print_btn.setObjectName("SecondaryButton")
        self.print_btn.clicked.connect(lambda: self.export("pdf"))
        actions.addWidget(self.print_btn)
        layout.addLayout(actions)

        # Completion bar
        self.completion_label = QLabel("")
        self.completion_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.completion_label)

        # Timetable grid
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context)
        self.table.cellDoubleClicked.connect(self.on_cell_double_click)
        # Drag and drop
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QTableWidget.InternalMove)
        self.table.viewport().installEventFilter(self)
        layout.addWidget(self.table, 1)
        # Track drag
        self._drag_entry_id = None
        self.table.setStyleSheet("""
            QTableWidget { background: #FFFFFF; alternate-background-color: #F8FAFC; gridline-color: #E2E8F0; border: 1px solid #CBD5E1; border-radius: 6px; }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section { background: #EEF2F7; padding: 4px 6px; font-weight: 600; font-size: 11px; color: #334155; border: 1px solid #E2E8F0; }
        """)
        # Hint for editable time slots
        self.hint = QLabel("Time slots are editable: double-click a time on the left to edit it, or go to Time Slots. Any custom time (e.g., 08:15-09:45) is allowed when adding a lecture.")
        self.hint.setStyleSheet("color: #64748B; font-size: 11px; padding: 2px 4px;")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.format_status = QLabel("")
        self.format_status.setStyleSheet("color: #64748B; font-size: 11px; padding: 2px 4px;")
        self.format_status.setWordWrap(True)
        layout.addWidget(self.format_status)
        self.load_semesters()

    def load_semesters(self):
        session = get_session()
        try:
            sems = session.query(Semester).order_by(Semester.id).all()
            self.sem_combo.clear()
            for s in sems:
                self.sem_combo.addItem(s.name, s.id)
            if sems:
                self.current_semester_id = sems[0].id
        finally:
            session.close()

    def refresh(self):
        self.load_semesters()
        self.refresh_format_status()
        if self.current_semester_id:
            self.load_timetable()

    def _saved_format_path(self):
        session = get_session()
        try:
            setting = session.query(Setting).filter(Setting.key == "timetable_format_photo").first()
            return setting.value if setting else ""
        finally:
            session.close()

    def refresh_format_status(self):
        path = self._saved_format_path()
        if path:
            self.format_status.setText(f"Format saved: {path}  •  Generate will reuse this format")
        else:
            self.format_status.setText("No format photo saved. Generate Timetable will ask for one before continuing.")

    def choose_format_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Timetable Format Photo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return False
        session = get_session()
        try:
            setting = session.query(Setting).filter(Setting.key == "timetable_format_photo").first()
            if setting:
                setting.value = path
            else:
                session.add(Setting(key="timetable_format_photo", value=path))
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Format Photo", f"Could not save the format photo:\n{exc}")
            return False
        finally:
            session.close()
        self.refresh_format_status()
        return True

    def generate_timetable(self):
        if not self._saved_format_path() and not self.choose_format_photo():
            return
        self.load_timetable()
        QMessageBox.information(
            self,
            "Timetable Ready",
            "The saved format is applied to this timetable view. Add or edit lectures to complete the schedule."
        )

    def on_semester_changed(self, idx):
        if idx < 0:
            return
        self.current_semester_id = self.sem_combo.currentData()
        self.load_timetable()

    def load_timetable(self):
        if not self.current_semester_id:
            return
        session = get_session()
        try:
            # Working days enabled
            days = session.query(WorkingDay).filter(WorkingDay.is_enabled==True).order_by(WorkingDay.sort_order).all()
            # Time slots for grid - use distinct time ranges from TimeSlot or default
            slots = session.query(TimeSlot).filter(TimeSlot.is_break==False, TimeSlot.is_enabled==True).order_by(TimeSlot.start_time).all()
            if not slots:
                slots = []
            # Build rows from slots plus any extra times from entries (to show custom times)
            entries = TimetableService.get_semester_timetable(session, self.current_semester_id)
            self.entries = entries
            # Completion
            comp = ConflictService.calculate_timetable_completion(session, self.current_semester_id)
            self.completion_label.setText(f"{self.sem_combo.currentText()} — Required: {comp['required']}  Scheduled: {comp['scheduled']}  Remaining: {comp['remaining']}  Completion: {comp['completion_pct']}%")
            # Table setup
            day_names = [d.name for d in days]
            self.table.clear()
            self.table.setColumnCount(len(day_names) + 1)
            headers = ["Time"] + day_names
            self.table.setHorizontalHeaderLabels(headers)
            # Rows: use slots
            times = [(s.start_time, s.end_time) for s in slots]
            # If slots empty, create default 8 rows
            if not times:
                times = [("08:00","09:00"),("09:00","10:00"),("10:00","11:00"),("11:00","12:00"),("12:00","13:00"),("14:00","15:00"),("15:00","16:00"),("16:00","17:00")]
            # Also ensure any entry time that doesn't match slot is still represented - add custom rows
            extra_times = []
            for e in entries:
                t = (e.start_time, e.end_time)
                if t not in times:
                    extra_times.append(t)
            times.extend(extra_times)
            # Sort times
            times = sorted(set(times), key=lambda x: time_to_minutes(x[0]))
            self.table.setRowCount(len(times))
            self._times = times
            self._days = days
            # Configure sizes
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            self.table.setColumnWidth(0, 110)
            for i in range(1, len(headers)):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            # Populate
            # Build lookup: (day_id, time) -> entry
            # But need overlap handling: if entry spans multiple slot rows, we need to place in exact matching row
            # Simplify: place entry in row where its start/end matches exactly, else custom row
            # For each entry, find row index
            # Initialize empty
            for r, (st, et) in enumerate(times):
                item = QTableWidgetItem(f"{st}-{et}")
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor("#F8FAFC"))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, 0, item)
                for c in range(1, len(headers)):
                    it = QTableWidgetItem("")
                    it.setTextAlignment(Qt.AlignCenter)
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(r, c, it)
            # Place entries
            for e in entries:
                # Find row
                t = (e.start_time, e.end_time)
                try:
                    row = times.index(t)
                except ValueError:
                    continue
                # Find column for day
                col = None
                for idx, d in enumerate(days):
                    if d.id == e.day_id:
                        col = idx + 1
                        break
                if col is None:
                    continue
                text = f"{e.subject.code if e.subject else ''}\n{e.subject.name if e.subject else ''}\n{e.teacher.name if e.teacher else ''}\n{e.room.name if e.room else ''} ({e.room.room_number if e.room else ''})\n{e.lecture_type}"
                item = self.table.item(row, col)
                if item:
                    item.setText(text)
                    # Color by type
                    colors = {"Theory": "#D9E1F2", "Practical": "#D1FAE5", "Lab": "#FEF3C7", "Tutorial": "#E0E7FF"}
                    bg = colors.get(e.lecture_type, "#F1F5F9")
                    item.setBackground(QColor(bg))
                    item.setData(Qt.UserRole, e.id)
                    item.setToolTip(f"{e.subject.name if e.subject else ''} - {e.teacher.name if e.teacher else ''} - {e.room.name if e.room else ''}\n{e.day.name if e.day else ''} {e.start_time}-{e.end_time}\nClick Edit to modify, drag to move")
            self.table.resizeRowsToContents()
        finally:
            session.close()

    def _selected_entry_id(self):
        row = self.table.currentRow()
        col = self.table.currentColumn()
        if row < 0 or col <= 0:
            # Try find any selected with data
            for r in range(self.table.rowCount()):
                for c in range(1, self.table.columnCount()):
                    it = self.table.item(r, c)
                    if it and it.isSelected() and it.data(Qt.UserRole):
                        return it.data(Qt.UserRole)
            return None
        item = self.table.item(row, col)
        if item and item.data(Qt.UserRole):
            return item.data(Qt.UserRole)
        # Search for data in row selection
        for c in range(1, self.table.columnCount()):
            it = self.table.item(row, c)
            if it and it.data(Qt.UserRole):
                return it.data(Qt.UserRole)
        return None

    def add_lecture(self):
        if not self.current_semester_id:
            QMessageBox.warning(self, "No Semester", "Please select a semester.")
            return
        # Try to prefill from selected cell time/day
        day_id = None
        st = None
        et = None
        row = self.table.currentRow()
        col = self.table.currentColumn()
        if row >= 0 and col >= 0 and hasattr(self, '_times') and hasattr(self, '_days'):
            if 0 <= row < len(self._times):
                st, et = self._times[row]
            if col > 0 and col-1 < len(self._days):
                day_id = self._days[col-1].id
        dlg = LectureDialog(self, semester_id=self.current_semester_id, day_id=day_id, start_time=st, end_time=et)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                ok, result = TimetableService.create_entry(session, **data, academic_year="2026-27")
                if ok:
                    QMessageBox.information(self, "Success", "Lecture added successfully.")
                    self.load_timetable()
                else:
                    msgs = "\n".join([c.message for c in result])
                    QMessageBox.critical(self, "Failed to Add", msgs)
            finally:
                session.close()
                try:
                    dlg.session.close()
                except:
                    pass

    def edit_lecture(self):
        eid = self._selected_entry_id()
        if not eid:
            QMessageBox.warning(self, "Select Lecture", "Please select a lecture cell to edit. Click on a filled cell.")
            return
        session = get_session()
        try:
            entry = session.query(TimetableEntry).filter(TimetableEntry.id==eid).first()
            if not entry:
                QMessageBox.warning(self, "Not Found", "Entry not found.")
                return
            # Need to keep session open for dialog? Dialog creates its own session, so close this
            session.expunge(entry)
        finally:
            session.close()
        dlg = LectureDialog(self, entry=entry)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                ok, result = TimetableService.update_entry(session, eid, **data)
                if ok:
                    QMessageBox.information(self, "Success", "Lecture updated.")
                    self.load_timetable()
                else:
                    msgs = "\n".join([c.message for c in result])
                    QMessageBox.critical(self, "Conflict", msgs)
            finally:
                session.close()
                try:
                    dlg.session.close()
                except:
                    pass

    def delete_lecture(self):
        eid = self._selected_entry_id()
        if not eid:
            QMessageBox.warning(self, "Select Lecture", "Please select a lecture to delete.")
            return
        if QMessageBox.question(self, "Confirm Delete", "Delete this lecture?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = get_session()
        try:
            if TimetableService.delete_entry(session, eid):
                QMessageBox.information(self, "Deleted", "Lecture deleted. Resources freed.")
                self.load_timetable()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete.")
        finally:
            session.close()

    def find_available(self):
        # Ask for subject/teacher/room
        session = get_session()
        try:
            from app.models import Teacher, Room, Subject
            teachers = session.query(Teacher).filter(Teacher.status=="Active").all()
            rooms = session.query(Room).filter(Room.status=="Available").all()
            # Simple dialog - use current selection's teacher/room if available, else first
            if not teachers or not rooms:
                QMessageBox.warning(self, "Missing Data", "Need teachers and rooms to find slots.")
                return
            # For demo, use selected entry's teacher/room or first
            eid = self._selected_entry_id()
            teacher_id = None
            room_id = None
            if eid:
                entry = session.query(TimetableEntry).filter(TimetableEntry.id==eid).first()
                if entry:
                    teacher_id = entry.teacher_id
                    room_id = entry.room_id
            if not teacher_id:
                teacher_id = teachers[0].id
            if not room_id:
                room_id = rooms[0].id
            # Duration dialog
            dur, ok = QInputDialog.getInt(self, "Duration", "Lecture duration (minutes):", 60, 30, 240, 15)
            if not ok:
                return
            slots = ConflictService.find_available_slots(session, self.current_semester_id, teacher_id, room_id, dur)
            if not slots:
                QMessageBox.information(self, "No Slots", "No available slots found.")
                return
            msg = "\n".join([f"✓ {s['day_name']} {s['start_time']}-{s['end_time']}" for s in slots[:10]])
            QMessageBox.information(self, f"Available Slots ({len(slots)} found)", msg)
        finally:
            session.close()

    def export(self, kind: str):
        if not self.current_semester_id:
            return
        session = get_session()
        try:
            sem = session.query(Semester).filter(Semester.id==self.current_semester_id).first()
            name = sem.name if sem else "Timetable"
        finally:
            session.close()
        if kind == "csv":
            path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"{name}.csv", "CSV Files (*.csv)")
            if not path:
                return
            session = get_session()
            try:
                export_csv(session, self.current_semester_id, path)
                QMessageBox.information(self, "Exported", f"CSV exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))
            finally:
                session.close()
        elif kind == "excel":
            path, _ = QFileDialog.getSaveFileName(self, "Export Excel", f"{name}.xlsx", "Excel Files (*.xlsx)")
            if not path:
                return
            session = get_session()
            try:
                export_excel(session, self.current_semester_id, path)
                QMessageBox.information(self, "Exported", f"Excel exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))
            finally:
                session.close()
        elif kind == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "Export PDF", f"{name}.pdf", "PDF Files (*.pdf)")
            if not path:
                return
            session = get_session()
            try:
                export_pdf(session, self.current_semester_id, path)
                QMessageBox.information(self, "Exported", f"PDF exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))
            finally:
                session.close()

    def on_cell_double_click(self, row, col):
        # Left time column = editable time slot
        if col == 0:
            self.edit_time_slot(row)
        else:
            self.edit_lecture()

    def edit_time_slot(self, row):
        if not hasattr(self, '_times') or row < 0 or row >= len(self._times):
            return
        st, et = self._times[row]
        session = get_session()
        try:
            # Find slot matching this time (if any)
            slot = session.query(TimeSlot).filter(TimeSlot.start_time==st, TimeSlot.end_time==et).first()
            # Detach for dialog
            if slot:
                session.expunge(slot)
            session.close()
            dlg = TimeSlotDialog(self, slot if slot else None)
            # If no existing slot, pre-fill with row times
            if not slot:
                # set dialog times to row times (already default 08-09, need to set)
                from PySide6.QtCore import QTime
                try:
                    sh, sm = map(int, st.split(":"))
                    eh, em = map(int, et.split(":"))
                    dlg.start_edit.setTime(QTime(sh, sm))
                    dlg.end_edit.setTime(QTime(eh, em))
                except:
                    pass
            if dlg.exec():
                data = dlg.get_data()
                s2 = get_session()
                try:
                    if slot:
                        s = s2.query(TimeSlot).filter(TimeSlot.id==slot.id).first()
                        for k,v in data.items():
                            setattr(s, k, v)
                    else:
                        # Create new slot for custom time
                        s = TimeSlot(**data)
                        s2.add(s)
                    s2.commit()
                    QMessageBox.information(self, "Saved", "Time slot saved. Timetable updated to allow any time.")
                    self.load_timetable()
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

    def show_context(self, pos):
        menu = QMenu(self)
        add_act = QAction("Add Lecture (any time)", self)
        add_act.triggered.connect(self.add_lecture)
        menu.addAction(add_act)
        edit_act = QAction("Edit Lecture", self)
        edit_act.triggered.connect(self.edit_lecture)
        menu.addAction(edit_act)
        del_act = QAction("Delete Lecture", self)
        del_act.triggered.connect(self.delete_lecture)
        menu.addAction(del_act)
        menu.addSeparator()
        # Time slot edit for left column
        idx = self.table.indexAt(pos)
        if idx.isValid() and idx.column() == 0:
            time_act = QAction("Edit This Time Slot", self)
            time_act.triggered.connect(lambda: self.edit_time_slot(idx.row()))
            menu.addAction(time_act)
        find_act = QAction("Find Available Slot", self)
        find_act.triggered.connect(self.find_available)
        menu.addAction(find_act)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # Simple drag-drop handling: override eventFilter to capture drop
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj == self.table.viewport():
            if event.type() == QEvent.Drop:
                # Handle move
                self.handle_drop(event)
                return True
            elif event.type() == QEvent.DragEnter:
                event.accept()
                return True
            elif event.type() == QEvent.DragMove:
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def handle_drop(self, event):
        # Get source item id and target cell
        # For simplicity, we don't have drag source id via mime, so use selected entry
        eid = self._selected_entry_id()
        if not eid:
            return
        pos = event.position().toPoint() if hasattr(event.position(), 'toPoint') else event.pos()
        target = self.table.indexAt(pos)
        if not target.isValid():
            return
        row = target.row()
        col = target.column()
        if col == 0:
            return
        if row < 0 or row >= len(self._times):
            return
        new_start, new_end = self._times[row]
        day_id = self._days[col-1].id if col-1 < len(self._days) else None
        if not day_id:
            return
        session = get_session()
        try:
            ok, result = TimetableService.move_entry(session, eid, day_id, new_start, new_end)
            if ok:
                QMessageBox.information(self, "Moved", f"Lecture moved to {self._days[col-1].name} {new_start}-{new_end}")
                self.load_timetable()
            else:
                msgs = "\n".join([c.message for c in result])
                QMessageBox.critical(self, "Move Failed - Conflict", msgs)
        finally:
            session.close()
        event.accept()
