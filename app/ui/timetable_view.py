from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QPushButton, QMessageBox, QFileDialog, QInputDialog
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QPixmap
from app.database import get_session
from app.models import Semester, WorkingDay, TimetableEntry, TimeSlot, Setting
from app.services.timetable_service import TimetableService
from app.services.conflict_service import ConflictService
from app.services.export_service import export_csv, export_excel, export_pdf
from app.ui.dialogs import LectureDialog, TimeSlotDialog
from app.utils.helpers import time_to_minutes
from app.ui.timetable_grid import TimetableGridWidget

class TimetableView(QWidget):
    def __init__(self):
        super().__init__()
        self.current_semester_id = None
        self.entries = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(10)
        # Top bar
        top = QHBoxLayout()
        title = QLabel("Timetable Builder")
        title.setObjectName("PageTitle")
        top.addWidget(title)
        top.addStretch()
        sem_lbl = QLabel("Semester:")
        sem_lbl.setObjectName("PageSubtitle")
        self.sem_combo = QComboBox()
        self.sem_combo.setMinimumWidth(180)
        self.sem_combo.currentIndexChanged.connect(self.on_semester_changed)
        top.addWidget(sem_lbl)
        top.addWidget(self.sem_combo)
        layout.addLayout(top)
        sub = QLabel("Build a conflict-free weekly schedule. Select a cell to add a lecture or double-click an existing lecture to edit it.")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(sub)

        # Actions bar
        actions = QGridLayout()
        actions.setHorizontalSpacing(6)
        actions.setVerticalSpacing(6)
        self.add_btn = QPushButton("＋ Add Lecture")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_lecture)
        actions.addWidget(self.add_btn, 0, 0)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_lecture)
        actions.addWidget(self.edit_btn, 0, 1)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_lecture)
        actions.addWidget(self.del_btn, 0, 2)
        self.generate_btn = QPushButton("Generate Timetable")
        self.generate_btn.setObjectName("PrimaryButton")
        self.generate_btn.clicked.connect(self.generate_timetable)
        actions.addWidget(self.generate_btn, 0, 3)
        self.format_btn = QPushButton("Format Photo")
        self.format_btn.setObjectName("SecondaryButton")
        self.format_btn.clicked.connect(self.choose_format_photo)
        actions.addWidget(self.format_btn, 0, 4)
        self.find_btn = QPushButton("Find Available Slot")
        self.find_btn.setObjectName("SecondaryButton")
        self.find_btn.clicked.connect(self.find_available)
        actions.addWidget(self.find_btn, 1, 0)
        # Export
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("SecondaryButton")
        self.export_csv_btn.clicked.connect(lambda: self.export("csv"))
        actions.addWidget(self.export_csv_btn, 1, 1)
        self.export_excel_btn = QPushButton("Excel")
        self.export_excel_btn.setObjectName("SecondaryButton")
        self.export_excel_btn.clicked.connect(lambda: self.export("excel"))
        actions.addWidget(self.export_excel_btn, 1, 2)
        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.setObjectName("SecondaryButton")
        self.export_pdf_btn.clicked.connect(lambda: self.export("pdf"))
        actions.addWidget(self.export_pdf_btn, 1, 3)
        self.print_btn = QPushButton("Print")
        self.print_btn.setObjectName("SecondaryButton")
        self.print_btn.clicked.connect(lambda: self.export("pdf"))
        actions.addWidget(self.print_btn, 1, 4)
        actions.setColumnStretch(5, 1)
        layout.addLayout(actions)

        # Completion bar
        self.completion_label = QLabel("")
        self.completion_label.setObjectName("SectionTitle")
        layout.addWidget(self.completion_label)
        self.conflict_notice = QLabel("")
        self.conflict_notice.setWordWrap(True)
        self.conflict_notice.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.conflict_notice.hide()
        layout.addWidget(self.conflict_notice)

        self.grid = TimetableGridWidget()
        self.grid.card_double_clicked.connect(self.edit_lecture_by_id)
        self.grid.drop_requested.connect(self.handle_grid_drop)
        self.grid.slot_clicked.connect(self.select_grid_slot)
        layout.addWidget(self.grid, 1)
        # Hint for editable time slots
        self.hint = QLabel("Time slots are editable: double-click a time on the left to edit it, or go to Time Slots. Any custom time (e.g., 08:15-09:45) is allowed when adding a lecture.")
        self.hint.setObjectName("PageSubtitle")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.format_status = QLabel("")
        self.format_status.setObjectName("PageSubtitle")
        self.format_status.setWordWrap(True)
        layout.addWidget(self.format_status)
        self.format_preview = QLabel("No format photo selected")
        self.format_preview.setMinimumHeight(72)
        self.format_preview.setAlignment(Qt.AlignCenter)
        self.format_preview.setStyleSheet("color: #64748B; font-size: 12px; background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 6px;")
        layout.addWidget(self.format_preview)
        self.load_semesters()

    def show_conflict_notice(self, message):
        self.conflict_notice.setText(f"\u274c Blocked \u2014 scheduling conflict:\n{message}")
        self.conflict_notice.setStyleSheet(
            "color: #991B1B; background: #FEF2F2; border: 1px solid #FECACA; "
            "border-radius: 10px; padding: 10px 12px; font-weight: 600; font-size: 12.5px;"
        )
        self.conflict_notice.show()

    def clear_conflict_notice(self):
        self.conflict_notice.clear()
        self.conflict_notice.hide()

    def select_grid_slot(self, row, column):
        self.grid.selected_slot = (row, column)

    def edit_lecture_by_id(self, entry_id):
        self.grid.selected_entry_id = entry_id
        self.edit_lecture()

    def load_semesters(self):
        session = get_session()
        try:
            sems = session.query(Semester).order_by(Semester.id).all()
            self.sem_combo.blockSignals(True)
            self.sem_combo.clear()
            for s in sems:
                self.sem_combo.addItem(s.name, s.id)
            if sems:
                self.current_semester_id = sems[0].id
            self.sem_combo.blockSignals(False)
        finally:
            try:
                self.sem_combo.blockSignals(False)
            except Exception:
                pass
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
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.format_status.setText(f"Format file is missing or unreadable: {path}  •  Choose Format Photo again")
                self.format_preview.setText("Saved format preview unavailable")
                self.format_preview.setPixmap(QPixmap())
            else:
                self.format_status.setText(f"Format saved: {path}  •  Generate will reuse this format")
                self.format_preview.setText("")
                self.format_preview.setPixmap(pixmap.scaled(520, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.format_status.setText("No format photo saved. Generate Timetable will ask for one before continuing.")
            self.format_preview.setText("No format photo selected")
            self.format_preview.setPixmap(QPixmap())

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
            if not days:
                self.completion_label.setText("No working days enabled — enable Mon-Sat in Time Slots.")
                self._times = []
                self._days = []
                self.grid.populate([], [], [])
                QMessageBox.warning(self, "No Working Days", "All working days are disabled. Enable at least one day in Time Slots.")
                return
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
            # Card grid setup
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
            def _sort_key(x):
                try:
                    return time_to_minutes(str(x[0]).strip())
                except (ValueError, AttributeError, TypeError):
                    return 10 ** 9
            times = sorted(set(times), key=_sort_key)
            times = [t for t in times if _sort_key(t) < 10 ** 9][:24]
            self._times = times
            self._days = days
            self.grid.populate(days, times, entries)
        finally:
            session.close()

    def _selected_entry_id(self):
        return self.grid.selected_entry_id

    def add_lecture(self):
        if not self.current_semester_id:
            QMessageBox.warning(self, "No Semester", "Please select a semester.")
            return
        # Try to prefill from selected cell time/day
        day_id = None
        st = None
        et = None
        row, col = self.grid.selected_slot if hasattr(self.grid, "selected_slot") else (-1, -1)
        if row >= 0 and col >= 0 and hasattr(self, '_times') and hasattr(self, '_days'):
            st, et = self._times[row]
            day_id = self._days[col].id
        dlg = LectureDialog(self, semester_id=self.current_semester_id, day_id=day_id, start_time=st, end_time=et)
        if dlg.exec():
            data = dlg.get_data()
            session = get_session()
            try:
                acad = session.query(Setting).filter(Setting.key == "academic_year").first()
                year = acad.value if acad and acad.value else "2026-27"
                ok, result = TimetableService.create_entry(session, **data, academic_year=year)
                if ok:
                    self.clear_conflict_notice()
                    QMessageBox.information(self, "Success", "Lecture added successfully.")
                    self.load_timetable()
                else:
                    msgs = "\n".join([c.message for c in result])
                    self.show_conflict_notice(msgs)
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
                    self.clear_conflict_notice()
                    QMessageBox.information(self, "Success", "Lecture updated.")
                    self.load_timetable()
                else:
                    msgs = "\n".join([c.message for c in result])
                    self.show_conflict_notice(msgs)
                    QMessageBox.critical(self, "Conflict", msgs)
            finally:
                session.close()
                try:
                    dlg.session.close()
                except:
                    pass

    def handle_grid_drop(self, entry_id, row, column):
        if not hasattr(self, "_times") or not hasattr(self, "_days"):
            return
        if row < 0 or row >= len(self._times) or column < 0 or column >= len(self._days):
            return
        new_start, new_end = self._times[row]
        day_id = self._days[column].id
        session = get_session()
        try:
            ok, result = TimetableService.move_entry(session, entry_id, day_id, new_start, new_end)
            if ok:
                self.clear_conflict_notice()
                self.load_timetable()
                QMessageBox.information(self, "Lecture moved", f"Moved to {self._days[column].name} {new_start}-{new_end}.")
            else:
                msgs = "\n".join([c.message for c in result])
                self.show_conflict_notice(msgs)
                self.grid.set_drop_feedback(row, column, False)
                QMessageBox.critical(self, "Move blocked by conflict", msgs)
        finally:
            session.close()

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
            QMessageBox.warning(self, "No Semester", "Please select a semester first.")
            return
        session = get_session()
        try:
            sem = session.query(Semester).filter(Semester.id==self.current_semester_id).first()
            raw = sem.name if sem else "Timetable"
            import re
            name = re.sub(r'[<>:/\\|?*]', '-', raw).strip() or "Timetable"
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
