"""Timetable Intelligence dialog: offline smart generation, preview, atomic apply.

Flow: reference -> analyze (real profile) -> generate (deterministic
optimization) -> validate -> preview + diff -> [Cancel] discards /
[OK] applies atomically. Database untouched until OK.
"""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
)

from app.database import get_session
from app.models import Semester
from app.services.intelligence.reference_analyzer import analyze_reference
from app.services.intelligence.timetable_agent import (
    STAGES, IntelligenceError, apply_result, run_intelligence,
)
from app.services.local_agent.schemas import LearningError as AgentError
from app.ui.base_dialog import BaseDialog
from app.ui.icons import icon
from app.ui.modals import error as modal_error
from app.ui.widgets import show_toast

STAGE_LABELS = {
    "reference": "Reference timetable loaded",
    "requirements": "Weekly requirements analyzed",
    "constraints": "Teacher/room/break constraints analyzed",
    "patterns": "Reference patterns extracted",
    "candidates": "Candidates generated",
    "optimization": "Optimization completed",
    "validation": "Conflict validation completed",
}


class _Worker(QThread):
    progressed = Signal(str)
    done_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, target_id, ref_id, mode, ref_profile=None,
                 planner="template", model=None, avoid=None):
        super().__init__()
        self._target_id = target_id
        self._ref_id = ref_id
        self._mode = mode
        self._ref_profile = ref_profile
        self._planner = planner
        self._model = model
        self._avoid = avoid

    def run(self):
        session = get_session()
        try:
            if self._planner == "local":
                from app.services.local_agent.agent import TimetableAgent
                agent = TimetableAgent()
                result = agent.generate_dry_run(
                    session, self._target_id, self._mode, self._model,
                    progress=self.progressed.emit, avoid=self._avoid)
                self.done_ok.emit({
                    "accepted": result.accepted,
                    "rejected": result.rejected,
                    "diff": result.stats.get("diff", {}),
                    "explanation": (
                        f"Planner: {result.profile_info.get('planner', '')}\n"
                        f"Profile: {result.profile_info.get('lectures', 0)} lectures, "
                        f"{result.profile_info.get('roles', 0)} roles "
                        f"from {len(result.profile_info.get('sources', []))} file(s).\n"
                        f"Model notes: {result.profile_info.get('model_notes', '')}\n"
                        f"Structural similarity: {result.structural_similarity:.2f}."
                    ),
                    "similarity": {"total": result.structural_similarity},
                    "requirements": [],
                    "mode": self._mode,
                })
            else:
                out = run_intelligence(session, self._target_id, self._ref_id,
                                       self._mode, progress=self.progressed.emit,
                                       ref_profile=self._ref_profile)
                self.done_ok.emit(out)
        except (IntelligenceError, AgentError) as e:
            self.failed.emit(str(e))
        except Exception:
            self.failed.emit("Unexpected failure. Nothing was changed.")
        finally:
            try:
                session.close()
            except Exception:
                pass


class _ProbeThread(QThread):
    probed = Signal(dict)

    def __init__(self, model=None):
        super().__init__()
        self._model = model

    def run(self):
        from app.services.local_agent.agent import TimetableAgent
        try:
            agent = TimetableAgent()
            client = agent._client()
            client.timeout = 3
            running = client.is_running()
            available = client.is_model_available(self._model) if running else False
            self.probed.emit({"running": running, "available": available,
                              "endpoint": client.endpoint,
                              "model": self._model or client.model})
        except Exception:
            self.probed.emit({"running": False, "available": False,
                              "endpoint": "", "model": self._model or ""})


class IntelligenceDialog(BaseDialog):
    def __init__(self, parent, target_semester_id: int, on_applied=None):
        super().__init__(parent, "Timetable Intelligence", min_width=720)
        self.setMinimumHeight(560)
        self._target_id = target_semester_id
        self._on_applied = on_applied
        self._result = None
        self._worker = None
        self._session = get_session()
        self._external = None

        top = QGroupBox("REFERENCE & MODE")
        grid = QVBoxLayout(top)
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("Reference timetable:"))
        self.ref_combo = QComboBox()
        self.ref_combo.setMinimumWidth(220)
        self.ref_combo.currentIndexChanged.connect(self._on_ref_combo_changed)
        ref_row.addWidget(self.ref_combo, 1)
        self.ext_btn = QPushButton("External File…")
        self.ext_btn.setObjectName("SecondaryButton")
        self.ext_btn.setCursor(Qt.PointingHandCursor)
        self.ext_btn.setToolTip("Use a CSV, JSON or Excel timetable as the reference format.")
        self.ext_btn.clicked.connect(self._load_external_reference)
        ref_row.addWidget(self.ext_btn)
        grid.addLayout(ref_row)
        self.mode_fill = QRadioButton("Fill Missing Lectures")
        self.mode_fill.setChecked(True)
        self.mode_fresh = QRadioButton("Generate Fresh Timetable")
        self.mode_replace = QRadioButton("Replacement Proposal (shows diff)")
        grid.addWidget(self.mode_fill)
        grid.addWidget(self.mode_fresh)
        grid.addWidget(self.mode_replace)
        planner_row = QHBoxLayout()
        planner_row.addWidget(QLabel("Planner:"))
        self.planner_template = QRadioButton("Template patterns (offline)")
        self.planner_template.setChecked(True)
        self.planner_local = QRadioButton("Local model plan")
        self.planner_local.toggled.connect(self._refresh_model_status)
        planner_row.addWidget(self.planner_template)
        planner_row.addWidget(self.planner_local)
        planner_row.addStretch()
        grid.addLayout(planner_row)
        self.model_status = QLabel("Local model: not checked.")
        self.model_status.setObjectName("Muted")
        self.model_status.setWordWrap(True)
        grid.addWidget(self.model_status)
        self.body_layout.addWidget(top)

        self.ref_summary = QLabel("")
        self.ref_summary.setObjectName("InfoBar")
        self.ref_summary.setWordWrap(True)
        self.body_layout.addWidget(self.ref_summary)

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
        self.body_layout.addWidget(stages_box)

        self.generate_btn = QPushButton(" Generate Timetable")
        self.generate_btn.setObjectName("PrimaryButton")
        self.generate_btn.setIcon(icon("sparkles", "#FFFFFF", 16))
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self._start)
        gen_row = QHBoxLayout()
        gen_row.addStretch()
        gen_row.addWidget(self.generate_btn)
        self.regen_btn = QPushButton("Regenerate")
        self.regen_btn.setObjectName("SecondaryButton")
        self.regen_btn.setCursor(Qt.PointingHandCursor)
        self.regen_btn.setToolTip("Generate a different candidate from the same profile.")
        self.regen_btn.setEnabled(False)
        self.regen_btn.clicked.connect(self._regenerate)
        gen_row.addWidget(self.regen_btn)
        self.body_layout.addLayout(gen_row)

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
        self.preview.setMinimumHeight(150)
        result_layout.addWidget(self.preview)
        self.unplaced_label = QLabel("")
        self.unplaced_label.setWordWrap(True)
        self.unplaced_label.setObjectName("Muted")
        result_layout.addWidget(self.unplaced_label)
        self.explain = QTextEdit()
        self.explain.setReadOnly(True)
        self.explain.setMaximumHeight(100)
        result_layout.addWidget(self.explain)
        self.result_box.setVisible(False)
        self.body_layout.addWidget(self.result_box)

        self._load_references()
        self.ok_button.setEnabled(False)
        self._model_state = {"running": False, "available": False,
                             "endpoint": "", "model": ""}
        self._probe = None
        self._last_accepted = []
        self._refresh_model_status()

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
            profile = analyze_reference(self._session, s.id)
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

    def _on_ref_combo_changed(self):
        # Picking a semester drops any loaded external file.
        self._external = None
        self._analyze_reference()

    def _load_external_reference(self):
        from PySide6.QtWidgets import QFileDialog
        from app.services.intelligence.reference_analyzer import (
            analyze_external_reference, load_reference_file,
        )
        from app.services.intelligence.timetable_agent import IntelligenceError
        path, _ = QFileDialog.getOpenFileName(
            self, "Load External Reference Timetable", "",
            "Timetable files (*.csv *.json *.xlsx);;All files (*.*)")
        if not path:
            return
        try:
            rows, skipped = load_reference_file(path)
            label = path.replace("\\", "/").rsplit("/", 1)[-1]
            profile = analyze_external_reference(self._session, rows, label)
        except IntelligenceError as e:
            modal_error(self, "External Reference", str(e))
            return
        except Exception:
            modal_error(self, "External Reference",
                        "Could not read reference file.")
            return
        self._external = {"label": label, "profile": profile, "skipped": skipped}
        self._show_external_summary()

    def _show_external_summary(self):
        profile = self._external["profile"]
        days = profile["working_days"]
        day_range = f"{days[0]}-{days[-1]}" if days else "-"
        skipped = f", {self._external['skipped']} row(s) skipped" if self._external["skipped"] else ""
        self.ref_summary.setText(
            f"External Reference: {self._external['label']} — "
            f"{profile['total_lectures']} lectures{skipped}, {day_range}, "
            f"avg {profile['average_daily_lectures']}/day, "
            f"{profile['subject_count']} subjects, "
            f"{profile['practical_sessions']} practical sessions, "
            f"morning {profile['morning_lectures']}/afternoon {profile['afternoon_lectures']}, "
            f"density {profile['density']}. "
            f"Changing the semester list clears this file.")

    def _analyze_reference(self):
        if self._external is not None:
            self._show_external_summary()
            return
        ref_id = self.ref_combo.currentData()
        if ref_id is None:
            self.ref_summary.setText("No reference timetable available.")
            return
        profile = analyze_reference(self._session, ref_id)
        if not profile["has_data"]:
            self.ref_summary.setText(
                "Reference Pattern Detected: empty — pick a semester with lectures.")
            return
        days = profile["working_days"]
        day_range = f"{days[0]}-{days[-1]}" if days else "-"
        self.ref_summary.setText(
            f"Reference Pattern Detected: {profile['semester']['name']} — "
            f"{profile['total_lectures']} lectures, {day_range}, "
            f"avg {profile['average_daily_lectures']}/day, "
            f"{profile['subject_count']} subjects, "
            f"{profile['practical_sessions']} practical sessions, "
            f"morning {profile['morning_lectures']}/afternoon {profile['afternoon_lectures']}, "
            f"density {profile['density']}.")

    # ---- generation ----------------------------------------------------
    def _mode(self):
        if self.mode_replace.isChecked():
            return "replace"
        if self.mode_fresh.isChecked():
            return "fresh"
        return "fill"

    def _start(self, regenerate=False):
        ref_id = self.ref_combo.currentData()
        if ref_id is None:
            modal_error(self, "Intelligence", "Select a reference timetable first.")
            return
        use_local = self.planner_local.isChecked()
        if use_local and not self._model_state.get("available", False):
            modal_error(self, "Local Model Unavailable",
                        "The local model is unavailable.\n\n"
                        f"Endpoint: {self._model_state.get('endpoint', '') or 'not checked'}\n"
                        "Start Ollama on this PC with `ollama serve`, then pull a "
                        "model once with e.g. `ollama pull llama3.1`.\n\n"
                        "No account or API key is ever needed. Meanwhile, "
                        "Template patterns generation below keeps working fully offline.")
            return
        self._result = None
        self.result_box.setVisible(False)
        self.ok_button.setEnabled(False)
        self.regen_btn.setEnabled(False)
        for label in self._stage_labels.values():
            label.setText("Waiting")
        self.generate_btn.setEnabled(False)
        ref_profile = self._external["profile"] if self._external else None
        if regenerate and self._last_accepted:
            avoid = {(e["subject_id"], e["day_id"], e["start_time"])
                     for e in self._last_accepted}
        else:
            avoid = None
        self._worker = _Worker(
            self._target_id, ref_id, self._mode(), ref_profile,
            planner="local" if use_local else "template",
            model=None, avoid=avoid)
        self._worker.progressed.connect(self._mark_stage)
        self._worker.done_ok.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _mark_stage(self, stage):
        label = self._stage_labels.get(stage)
        if label is not None:
            label.setText("Done")

    def _on_done(self, result):
        self.generate_btn.setEnabled(True)
        self._result = result
        self._last_accepted = list(result.get("accepted", []))
        self._fill_preview(result)
        self.result_box.setVisible(True)
        self.ok_button.setEnabled(len(result.get("accepted", [])) > 0)
        self.regen_btn.setEnabled(len(result.get("accepted", [])) > 0)

    def _regenerate(self):
        self._start(regenerate=True)

    def _refresh_model_status(self):
        try:
            if self._probe is not None and self._probe.isRunning():
                return
        except Exception:
            pass
        self.model_status.setText("Local model: checking localhost…")
        self._probe = _ProbeThread()
        self._probe.probed.connect(self._on_model_probed)
        self._probe.start()

    def _on_model_probed(self, state):
        self._model_state = state
        if state.get("available"):
            self.model_status.setText(
                f"Local model: connected ({state.get('model', '')}).")
        elif state.get("running"):
            self.model_status.setText(
                "Local model: Ollama is running but no model is pulled. "
                "Run `ollama pull llama3.1` once, or use Template patterns.")
        else:
            self.model_status.setText(
                "Local model: unavailable (offline is fine). "
                "Start it with `ollama serve`, or use Template patterns.")

    def _on_failed(self, message):
        self.generate_btn.setEnabled(True)
        modal_error(self, "Intelligence Failed",
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

    def _fill_preview(self, result):
        accepted = result.get("accepted", [])
        self.preview.setRowCount(len(accepted))
        for r, e in enumerate(accepted):
            day, time, code, teacher, room = self._resolve(e)
            for c, text in enumerate([day, time, code, teacher, room, "New"]):
                self.preview.setItem(r, c, QTableWidgetItem(text))
        rejected = result.get("rejected", [])
        lines = [f"• {x.get('code', '')} {x.get('reason', '')}".strip()
                 for x in rejected[:8]]
        if len(rejected) > 8:
            lines.append(f"• (+{len(rejected) - 8} more)")
        self.unplaced_label.setText(
            "Unplaced:\n" + "\n".join(lines) if lines else "Unplaced: none.")
        self.explain.setPlainText(result.get("explanation", ""))
        diff = result.get("diff", {})
        similarity = result.get("similarity", {}) or {}
        self.diff_label.setText(
            f"Mode: {result.get('mode', 'fill')} — "
            f"Current: {diff.get('existing', 0)}, Generated: {diff.get('generated', 0)}, "
            f"Unchanged: {diff.get('unchanged', 0)}, Changed: {diff.get('changed', 0)}, "
            f"Conflicts: 0, Unplaced: {len(rejected)}, "
            f"Structural similarity: {similarity.get('total', 0.0):.2f}."
            + (" Replace deletes this semester's entries first (after OK only)."
               if result.get("mode") == "replace" else ""))
        reqs = result.get("requirements", [])
        if reqs:
            self.explain.setPlainText(
                result.get("explanation", "") + "\n\n" + "\n".join(
                    f"{x['code']}: required {x['required']}, scheduled {x['scheduled']}, "
                    f"remaining {x['remaining']}" for x in reqs))

    # ---- apply ---------------------------------------------------------
    def accept(self):
        if not self._result or not self._result.get("accepted"):
            modal_error(self, "Nothing to Apply", "Generate a valid proposal first.")
            return
        session = get_session()
        try:
            try:
                out = apply_result(session, self._target_id, self._result,
                                   self._result.get("mode", "fill"))
            except Exception:
                modal_error(self, "Apply Failed",
                            "Database failure. Everything was rolled back; nothing changed.")
                return
            if out.get("rejected"):
                modal_error(self, "Apply Blocked",
                            "Re-validation failed. Nothing was written.")
                return
            show_toast(self, f"Applied {out.get('applied', 0)} lecture(s).")
            try:
                if callable(self._on_applied):
                    self._on_applied()
            except Exception:
                pass
            super().accept()
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


def open_intelligence_dialog(parent, target_semester_id: int, on_applied=None):
    dialog = IntelligenceDialog(parent, target_semester_id, on_applied=on_applied)
    dialog.exec()
