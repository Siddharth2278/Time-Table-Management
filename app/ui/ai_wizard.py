"""AI timetable generation wizard: internet-only, preview-first, atomic apply.

Flow: check internet -> pick reference -> analyze (real profile) ->
generate online -> validate every entry with ConflictService -> preview ->
diff -> [Cancel] discards everything / [OK] applies atomically.
The database is never touched until OK, and Cancel always discards.
"""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.database import get_session
from app.models import Semester
from app.services.ai.ai_client import AIError, config_from_settings, provider_status
from app.services.ai.prompt_builder import build_reference_profile
from app.services.ai.timetable_agent import STAGES, apply_proposal, run as run_agent
from app.ui.icons import icon
from app.ui.modals import error as modal_error
from app.ui.widgets import pin_dialog_buttons, show_toast, style_dialog_buttons

STAGE_LABELS = {
    "internet": "Internet connected",
    "reference": "Reference timetable loaded",
    "requirements": "Weekly requirements analyzed",
    "teachers": "Teacher constraints analyzed",
    "rooms": "Room constraints analyzed",
    "breaks": "Break pattern analyzed",
    "generated": "Timetable generated",
    "validated": "Conflict validation complete",
}


class _Worker(QThread):
    progressed = Signal(str)
    done_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, target_id, ref_id, mode, config):
        super().__init__()
        self._target_id = target_id
        self._ref_id = ref_id
        self._mode = mode
        self._config = config

    def run(self):
        session = get_session()
        try:
            out = run_agent(session, self._target_id, self._ref_id,
                            self._mode, self._config,
                            progress=self.progressed.emit)
            self.done_ok.emit(out)
        except AIError as e:
            self.failed.emit(str(e))
        except Exception:
            self.failed.emit("Unexpected failure. Nothing was changed.")
        finally:
            try:
                session.close()
            except Exception:
                pass


class AIGenerateDialog(QDialog):
    def __init__(self, parent, target_semester_id: int, on_applied=None):
        super().__init__(parent)
        self._target_id = target_semester_id
        self._on_applied = on_applied
        self._proposal = None
        self._worker = None
        self._session = get_session()
        self.setWindowTitle("AI Generate Timetable")
        self.setMinimumSize(760, 560)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        top = QGroupBox("REFERENCE & MODE")
        grid = QGridLayout(top)
        grid.addWidget(QLabel("Target:"), 0, 0)
        self.target_label = QLabel(self._semester_name(target_semester_id))
        self.target_label.setObjectName("SectionTitle")
        grid.addWidget(self.target_label, 0, 1)
        grid.addWidget(QLabel("Reference timetable:"), 1, 0)
        self.ref_combo = QComboBox()
        self.ref_combo.setMinimumWidth(220)
        self.ref_combo.currentIndexChanged.connect(self._analyze_reference)
        grid.addWidget(self.ref_combo, 1, 1)
        self.mode_fill = QRadioButton("Fill only unassigned lectures")
        self.mode_fill.setChecked(True)
        self.mode_replace = QRadioButton("Replace entire timetable (shows diff)")
        grid.addWidget(self.mode_fill, 2, 0, 1, 2)
        grid.addWidget(self.mode_replace, 3, 0, 1, 2)
        layout.addWidget(top)

        self.ref_summary = QLabel("")
        self.ref_summary.setObjectName("InfoBar")
        self.ref_summary.setWordWrap(True)
        layout.addWidget(self.ref_summary)

        stages_box = QGroupBox("PROGRESS")
        stages_layout = QVBoxLayout(stages_box)
        self._stage_labels = {}
        for stage in STAGES:
            row = QHBoxLayout()
            name = QLabel(STAGE_LABELS[stage])
            name.setObjectName("Muted")
            status = QLabel("Waiting")
            status.setObjectName("Muted")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(status)
            stages_layout.addLayout(row)
            self._stage_labels[stage] = status
        layout.addWidget(stages_box)

        gen_row = QHBoxLayout()
        gen_row.addStretch()
        self.generate_btn = QPushButton(" Generate with AI")
        self.generate_btn.setObjectName("PrimaryButton")
        self.generate_btn.setIcon(icon("sparkles", "#FFFFFF", 16))
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self._start_generation)
        gen_row.addWidget(self.generate_btn)
        layout.addLayout(gen_row)

        self.result_box = QGroupBox("PROPOSAL PREVIEW")
        result_layout = QVBoxLayout(self.result_box)
        self.diff_label = QLabel("")
        self.diff_label.setObjectName("Muted")
        self.diff_label.setWordWrap(True)
        result_layout.addWidget(self.diff_label)
        self.preview = QTableWidget(0, 6)
        self.preview.setHorizontalHeaderLabels(
            ["DAY", "TIME", "SUBJECT", "TEACHER", "ROOM", "STATUS"])
        self.preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview.setAlternatingRowColors(True)
        self.preview.verticalHeader().setVisible(False)
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.setMinimumHeight(160)
        result_layout.addWidget(self.preview)
        self.unplaced_label = QLabel("")
        self.unplaced_label.setWordWrap(True)
        self.unplaced_label.setObjectName("Muted")
        result_layout.addWidget(self.unplaced_label)
        self.explain = QTextEdit()
        self.explain.setReadOnly(True)
        self.explain.setMaximumHeight(110)
        result_layout.addWidget(self.explain)
        self.result_box.setVisible(False)
        layout.addWidget(self.result_box)

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btns.accepted.connect(self._apply)
        self.btns.rejected.connect(self.reject)
        layout.addWidget(self.btns)
        style_dialog_buttons(self.btns)
        pin_dialog_buttons(self)

        self._load_references()
        self._set_ok_enabled(False)

    # ---- setup ---------------------------------------------------------
    def _semester_name(self, semester_id):
        sem = self._session.query(Semester).filter(
            Semester.id == semester_id).first()
        return sem.name if sem else f"Semester {semester_id}"

    def _load_references(self):
        sems = self._session.query(Semester).order_by(Semester.id).all()
        self.ref_combo.blockSignals(True)
        self.ref_combo.clear()
        best, best_count = None, -1
        for s in sems:
            profile = build_reference_profile(self._session, s.id)
            self.ref_combo.addItem(
                f"{s.name} ({profile['total_lectures']} lectures)", s.id)
            if s.id != self._target_id and profile["total_lectures"] > best_count:
                best, best_count = s.id, profile["total_lectures"]
        if best is not None:
            idx = self.ref_combo.findData(best)
            if idx >= 0:
                self.ref_combo.setCurrentIndex(idx)
        self.ref_combo.blockSignals(False)
        self._analyze_reference()

    def _analyze_reference(self):
        ref_id = self.ref_combo.currentData()
        if ref_id is None:
            self.ref_summary.setText("No reference timetable available.")
            return
        profile = build_reference_profile(self._session, ref_id)
        if not profile["has_data"]:
            self.ref_summary.setText(
                "Reference Pattern Detected: empty — pick a semester with lectures.")
            return
        days = profile["working_days"]
        day_range = f"{days[0]}-{days[-1]}" if days else "-"
        self.ref_summary.setText(
            f"Reference Pattern Detected: {profile['semester']['name']} — "
            f"{profile['total_lectures']} lectures, {day_range} "
            f"({len(days)} days), avg load {profile['average_daily_load']}/day, "
            f"{profile['subject_count']} subjects, "
            f"{profile['practical_sessions']} practical sessions, "
            f"morning {profile['morning_lectures']} / afternoon {profile['afternoon_lectures']}, "
            f"density {profile['density']}.")

    # ---- generation ----------------------------------------------------
    def _set_ok_enabled(self, enabled: bool):
        ok_btn = self.btns.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setEnabled(enabled)

    def _mark_stage(self, stage):
        label = self._stage_labels.get(stage)
        if label is not None:
            label.setText("Done")

    def _reset_stages(self):
        for label in self._stage_labels.values():
            label.setText("Waiting")

    def _start_generation(self):
        session = get_session()
        try:
            config = config_from_settings(session)
        finally:
            session.close()
        state = provider_status(config)
        if state["state"] != "ready":
            modal_error(self, "AI Unavailable", state["message"])
            return
        ref_id = self.ref_combo.currentData()
        if ref_id is None:
            modal_error(self, "AI Unavailable", "Select a reference timetable first.")
            return
        mode = "replace" if self.mode_replace.isChecked() else "fill"
        self._proposal = None
        self.result_box.setVisible(False)
        self._set_ok_enabled(False)
        self._reset_stages()
        self.generate_btn.setEnabled(False)
        self._worker = _Worker(self._target_id, ref_id, mode, config)
        self._worker.progressed.connect(self._mark_stage)
        self._worker.done_ok.connect(self._on_generated)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_generated(self, proposal):
        self.generate_btn.setEnabled(True)
        self._proposal = proposal
        self._fill_preview(proposal)
        self.result_box.setVisible(True)
        self._set_ok_enabled(len(proposal.get("accepted", [])) > 0)

    def _on_failed(self, message):
        self.generate_btn.setEnabled(True)
        modal_error(self, "AI Generation Failed",
                    f"{message}\n\nNothing was written to the database.")

    def _resolve(self, entry):
        from app.models import Room, Subject, Teacher, WorkingDay
        s = self._session
        sub = s.query(Subject).filter(Subject.id == entry["subject_id"]).first()
        tea = s.query(Teacher).filter(Teacher.id == entry["teacher_id"]).first()
        roo = s.query(Room).filter(Room.id == entry["room_id"]).first()
        day = s.query(WorkingDay).filter(WorkingDay.id == entry["day_id"]).first()
        return (day.name if day else "", f"{entry['start_time']}-{entry['end_time']}",
                sub.code if sub else "", tea.name if tea else "",
                roo.name if roo else "")

    def _fill_preview(self, proposal):
        accepted = proposal.get("accepted", [])
        self.preview.setRowCount(len(accepted))
        for r, e in enumerate(accepted):
            day, time, code, teacher, room = self._resolve(e)
            for c, text in enumerate([day, time, code, teacher, room, "New"]):
                self.preview.setItem(r, c, QTableWidgetItem(text))
        rejected = proposal.get("rejected", [])
        model_unplaced = proposal.get("model_unplaced", [])
        lines = [f"• {r.get('reason', '')}" for r in rejected[:8]]
        lines += [f"• {u}" for u in model_unplaced[:8]]
        if len(rejected) + len(model_unplaced) > 8:
            lines.append(f"• (+{len(rejected) + len(model_unplaced) - 8} more)")
        self.unplaced_label.setText(
            "Unplaced:\n" + "\n".join(lines) if lines else "Unplaced: none.")
        self.explain.setPlainText(proposal.get("explanation", ""))
        diff = proposal.get("diff", {})
        mode = proposal.get("mode", "fill")
        self.diff_label.setText(
            f"Mode: {'Replace entire timetable' if mode == 'replace' else 'Fill only unassigned'} — "
            f"Existing: {diff.get('existing', 0)}, Generated: {diff.get('generated', 0)}, "
            f"Unchanged: {diff.get('unchanged', 0)}, Changed: {diff.get('changed', 0)}."
            + (" Replace will delete existing entries of this semester first." if mode == "replace" else ""))

    # ---- apply ---------------------------------------------------------
    def _apply(self):
        if not self._proposal or not self._proposal.get("accepted"):
            modal_error(self, "Nothing to Apply", "Generate a valid proposal first.")
            return
        from app.services.ai.timetable_agent import apply_proposal
        session = get_session()
        try:
            try:
                result = apply_proposal(session, self._target_id,
                                        self._proposal, self._proposal.get("mode", "fill"))
            except Exception:
                modal_error(self, "Apply Failed",
                            "Database failure. Everything was rolled back; nothing changed.")
                return
            if result.get("rejected"):
                modal_error(self, "Apply Blocked",
                            "Re-validation failed. Nothing was written.")
                return
            show_toast(self, f"Applied {result.get('applied', 0)} lecture(s).")
            try:
                if callable(self._on_applied):
                    self._on_applied()
            except Exception:
                pass
            self.accept()
        finally:
            try:
                session.close()
            except Exception:
                pass

    def closeEvent(self, event):
        try:
            if self._worker is not None and self._worker.isRunning():
                self._worker.wait()
        except Exception:
            pass
        try:
            self._session.close()
        except Exception:
            pass
        super().closeEvent(event)


def open_ai_wizard(parent, target_semester_id: int, on_applied=None):
    dialog = AIGenerateDialog(parent, target_semester_id, on_applied=on_applied)
    dialog.exec()
