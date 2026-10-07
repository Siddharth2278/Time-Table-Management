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
from app.ui.modals import error as modal_error, info as modal_info
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
            if self._planner in ("local", "trained"):
                from app.services.local_agent.agent import TimetableAgent
                agent = TimetableAgent()
                result = agent.generate_dry_run(
                    session, self._target_id, self._mode, self._model,
                    progress=self.progressed.emit, avoid=self._avoid,
                    planner=self._planner)
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


class _TrainWorker(QThread):
    done_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, files=None, incremental=False, records=None,
                 source_label="approved-import"):
        super().__init__()
        self._files = [str(p) for p in (files or [])]
        self._incremental = incremental
        self._records = [dict(r) for r in (records or [])]
        self._source_label = source_label

    def run(self):
        from app.services.local_agent.agent import TimetableAgent
        try:
            agent = TimetableAgent()
            if self._records:
                if self._incremental:
                    from app.services.local_agent import model_store
                    report = model_store.train_from_rows(
                        self._records, source_label=self._source_label,
                        data_dir=None, replace=False)
                    agent._verify_persisted_model(report)
                    agent._rebuild_profile_from_dataset()
                else:
                    report = agent.train_records(self._records,
                                                 self._source_label)
            elif self._incremental:
                report = agent.update_training(self._files)
            else:
                report = agent.train_agent(self._files)
            self.done_ok.emit(report)
        except Exception as e:
            try:
                from app.services.local_agent.schemas import LearningError
                message = str(e) if isinstance(e, LearningError) else \
                    "Training failed unexpectedly; previous model kept."
            except Exception:
                message = "Training failed unexpectedly; previous model kept."
            self.failed.emit(message)


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
        self.planner_trained = QRadioButton("Trained Local Model")
        self.planner_trained.setToolTip(
            "Scores candidates with the fitted on-PC model "
            "(timetable_agent_model/model.joblib). Never needs Ollama or internet.")
        self.planner_local = QRadioButton("Optional Ollama plan")
        self.planner_local.setToolTip(
            "Optional explanation/planning via Ollama on this PC only "
            "(http://127.0.0.1:11434). Never required for the trained model.")
        self.planner_local.toggled.connect(self._refresh_model_status)
        planner_row.addWidget(self.planner_template)
        planner_row.addWidget(self.planner_trained)
        planner_row.addWidget(self.planner_local)
        planner_row.addStretch()
        grid.addLayout(planner_row)
        self.model_status = QLabel("Optional Ollama planner: not checked. Trained Local Model works offline.")
        self.model_status.setObjectName("Muted")
        self.model_status.setWordWrap(True)
        grid.addWidget(self.model_status)
        self.body_layout.addWidget(top)

        train_box = QGroupBox("AI TIMETABLE AGENT")
        train_layout = QVBoxLayout(train_box)
        self.train_status = QLabel("Training status: checking…")
        self.train_status.setObjectName("Muted")
        self.train_status.setWordWrap(True)
        train_layout.addWidget(self.train_status)
        train_row = QHBoxLayout()
        self.train_btn = QPushButton("Train Agent")
        self.train_btn.setObjectName("SecondaryButton")
        self.train_btn.setCursor(Qt.PointingHandCursor)
        self.train_btn.setToolTip("Fit the local model on previous timetable files.")
        self.train_btn.clicked.connect(self._train_agent_files)
        train_row.addWidget(self.train_btn)
        self.add_data_btn = QPushButton("Add Training Data")
        self.add_data_btn.setObjectName("SecondaryButton")
        self.add_data_btn.setCursor(Qt.PointingHandCursor)
        self.add_data_btn.clicked.connect(lambda: self._train_agent_files(incremental=True))
        train_row.addWidget(self.add_data_btn)
        self.view_patterns_btn = QPushButton("View Learned Patterns")
        self.view_patterns_btn.setObjectName("SecondaryButton")
        self.view_patterns_btn.setCursor(Qt.PointingHandCursor)
        self.view_patterns_btn.clicked.connect(self._view_learned_patterns)
        train_row.addWidget(self.view_patterns_btn)
        self.clear_train_btn = QPushButton("Clear Training")
        self.clear_train_btn.setObjectName("SecondaryButton")
        self.clear_train_btn.setCursor(Qt.PointingHandCursor)
        self.clear_train_btn.clicked.connect(self._clear_training)
        train_row.addWidget(self.clear_train_btn)
        train_row.addStretch()
        train_layout.addLayout(train_row)
        self.baseline_status = QLabel("Baseline: checking…")
        self.baseline_status.setObjectName("Muted")
        self.baseline_status.setWordWrap(True)
        train_layout.addWidget(self.baseline_status)
        deploy_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Deployable Agent")
        self.export_btn.setObjectName("SecondaryButton")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setToolTip("Export the fitted model as a verified baseline package.")
        self.export_btn.clicked.connect(self._export_agent)
        deploy_row.addWidget(self.export_btn)
        self.import_btn = QPushButton("Import Trained Agent")
        self.import_btn.setObjectName("SecondaryButton")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.setToolTip("Import a verified agent package (model/data only).")
        self.import_btn.clicked.connect(self._import_agent)
        deploy_row.addWidget(self.import_btn)
        self.update_btn = QPushButton("Update Agent")
        self.update_btn.setObjectName("SecondaryButton")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setToolTip("Retrain on collected feedback when the threshold is reached.")
        self.update_btn.clicked.connect(self._update_agent)
        deploy_row.addWidget(self.update_btn)
        self.history_btn = QPushButton("Training History")
        self.history_btn.setObjectName("SecondaryButton")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.clicked.connect(self._show_history)
        deploy_row.addWidget(self.history_btn)
        deploy_row.addStretch()
        train_layout.addLayout(deploy_row)
        self.body_layout.addWidget(train_box)

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
        self._train_worker = None
        self._refresh_model_status()
        self._refresh_train_status()

    def _trained_state(self):
        try:
            from app.services.local_agent.agent import TimetableAgent
            return TimetableAgent().model_status()
        except Exception:
            return {"trained": False}

    def _refresh_train_status(self):
        state = self._trained_state()
        if state.get("trained"):
            self.train_status.setText(
                f"Training status: ● Trained — "
                f"{len(state.get('sources', []))} file(s), "
                f"{state.get('lectures', 0)} lectures, "
                f"{state.get('positives', 0)}+{state.get('negatives', 0)} samples, "
                f"model v{state.get('model_version', '?')}.")
        else:
            self.train_status.setText(
                "Timetable Agent not trained. "
                "Import previous timetable data and train the local agent "
                "to personalize timetable generation.")
        self._refresh_baseline_status(state)

    def _refresh_baseline_status(self, state=None):
        try:
            from app.services.local_agent import adaptive
            from app.services.local_agent.baseline import (
                active_origin, find_bundled_baseline,
            )
            status = adaptive.adaptive_status()
            bundled = find_bundled_baseline()
            origin = active_origin().get("origin", "local")
            quality = ""
            if (state or {}).get("trained"):
                quality = (f"Backend {state.get('backend', '?')}, "
                           f"separation {state.get('separation', '?')}, "
                           f"trained in {state.get('train_seconds', '?')}s.")
            if (state or {}).get("trained") and origin == "bundled-production-baseline":
                self.baseline_status.setText(
                    f"Trained Timetable Agent Ready — current model is the bundled production baseline: "
                    f"model v{state.get('model_version', '?')}, "
                    f"{state.get('lectures', 0)} rows, "
                    f"trained {state.get('trained_at', '-')}, "
                    f"schema v{state.get('feature_schema', '?')}. {quality} "
                    f"Feedback: {status.get('pending', 0)}/{status.get('min_examples', '?')} "
                    f"(retrain {'pending' if status.get('retrain_pending') else 'not needed'}).")
            elif (state or {}).get("trained") and origin == "bundled-sample-baseline":
                self.baseline_status.setText(
                    f"Trained Timetable Agent Ready — development sample baseline "
                    f"(not a production model): model v{state.get('model_version', '?')}, "
                    f"{state.get('lectures', 0)} rows. {quality} "
                    f"Feedback: {status.get('pending', 0)}/{status.get('min_examples', '?')}.")
            elif (state or {}).get("trained"):
                self.baseline_status.setText(
                    f"Trained Timetable Agent Ready — current model was trained locally on this PC: "
                    f"model v{state.get('model_version', '?')}, "
                    f"{state.get('lectures', 0)} rows, "
                    f"trained {state.get('trained_at', '-')}. {quality} "
                    f"Feedback: {status.get('pending', 0)}/{status.get('min_examples', '?')} "
                    f"(retrain {'pending' if status.get('retrain_pending') else 'not needed'}).")
            elif bundled is not None:
                self.baseline_status.setText(
                    "Bundled baseline available — restart the app to seed it, "
                    "or train on Historical Timetable Data.")
            else:
                self.baseline_status.setText(
                    f"Baseline: none bundled. Feedback: {status.get('pending', 0)}/"
                    f"{status.get('min_examples', '?')}.")
        except Exception:
            pass

    def _export_agent(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Deployable Agent", "CollegeTimetableAgentPackage.zip",
            "Agent package (*.zip)")
        if not path:
            return
        try:
            from app.services.local_agent.baseline import export_package
            out = export_package(zip_path=path)
            show_toast(self, f"Agent exported: {out['zip']}")
            self._refresh_train_status()
        except Exception as e:
            modal_error(self, "Export Failed", str(e))

    def _import_agent(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Trained Agent", "", "Agent package (*.zip)")
        if not path:
            return
        try:
            from app.services.local_agent.baseline import import_package
            import_package(path)
            self._refresh_train_status()
            show_toast(self, "Trained agent imported and activated.")
        except Exception as e:
            modal_error(self, "Import Failed", str(e))

    def _update_agent(self):
        try:
            from app.services.local_agent import adaptive
            report = adaptive.maybe_retrain(force=False)
            if report is None:
                status = adaptive.adaptive_status()
                modal_info(self, "Update Agent",
                           f"Not enough new examples yet: {status['pending']}/"
                           f"{status['min_examples']}. Import timetables or "
                           "record accepted edits first.")
                return
            self._refresh_train_status()
            show_toast(self, f"Agent updated: {report.get('lectures', '?')} lectures.")
        except Exception as e:
            modal_error(self, "Update Failed", str(e))

    def _show_history(self):
        try:
            from app.services.local_agent import adaptive
            history = adaptive.training_history()
            lines = [f"Pending feedback: {history['status'].get('pending', 0)}, "
                     f"model v{history['status'].get('model_version', '?')}, "
                     f"last trained {history['status'].get('trained_at', '-') or '-'}."]
            for entry in history.get("versions", [])[-10:]:
                lines.append(f"{entry.get('version')}: "
                             f"{entry.get('label', '')} "
                             f"{entry.get('trained_at', '')}".strip())
            modal_info(self, "Training History", "\n".join(lines))
        except Exception as e:
            modal_error(self, "Training History", str(e))

    def _train_agent_files(self, incremental=False):
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Previous Timetable Files", "",
            "Timetable files (*.csv *.json *.xlsx *.xls *.pdf *.jpg *.jpeg *.png *.webp *.bmp);;All files (*.*)")
        if not paths:
            return
        self._analyze_and_train(paths, incremental)

    def _analyze_and_train(self, paths, incremental=False):
        """Analyze files, preview when review is needed, then train.

        Pure legacy batches (.csv/.json/.xlsx-family) keep the exact
        existing direct-train path. Batches containing new formats
        (.xls/.pdf/images) go through offline extraction + user preview;
        only approved rows are combined with any legacy rows and trained.
        """
        legacy = {".csv", ".json", ".xlsx", ".xlsm", ".xltx", ".xltm"}
        new = [str(p) for p in paths if (
            "." + str(p).lower().rsplit(".", 1)[-1]
            if "." in str(p) else "") not in legacy]
        if not new:
            self._start_train_worker(files=paths, incremental=incremental)
            return
        from app.services.timetable_import.importer import TimetableImporter
        from app.services.timetable_import.preview import (
            records_to_lecture_dicts,
        )
        analyzed = TimetableImporter.analyze_files(new)
        extractions = analyzed["extractions"]
        if not extractions:
            errors = analyzed["errors"]
            modal_error(self, "Import Failed",
                        errors[0]["error"] if errors else
                        "No timetable data was detected in these files.")
            return
        from app.ui.import_preview_dialog import open_import_preview
        approved = open_import_preview(
            self, extractions, analyzed["reports"], analyzed["errors"])
        if not approved:
            return  # user cancelled or approved nothing.
        try:
            from app.services.local_agent.training_dataset import (
                load_files_as_dicts,
            )
            legacy_paths = [str(p) for p in paths if str(p) not in new]
            combined = records_to_lecture_dicts(approved)
            label_parts = []
            if legacy_paths:
                legacy_rows, _skipped, _per = load_files_as_dicts(legacy_paths)
                combined.extend(legacy_rows)
                label_parts.append("training-files")
            label_parts.append(TimetableImporter.baseline_source_label(
                extractions))
            try:
                from app.services.timetable_import.preview import (
                    save_approved_jsonl,
                )
                from app.services.timetable_import.validator import (
                    validate_records,
                )
                all_records = []
                for extraction in extractions:
                    all_records.extend(extraction.records)
                save_approved_jsonl(all_records)
            except Exception:
                pass
        except Exception as e:
            modal_error(self, "Import Failed", str(e))
            return
        self._start_train_worker(
            records=combined, incremental=incremental,
            source_label=", ".join(label_parts))

    def _start_train_worker(self, files=None, incremental=False, records=None,
                            source_label="approved-import"):
        for btn in (self.train_btn, self.add_data_btn, self.clear_train_btn,
                    self.view_patterns_btn, self.generate_btn):
            btn.setEnabled(False)
        self._train_worker = _TrainWorker(files or [], incremental,
                                          records or [], source_label)
        self._train_worker.done_ok.connect(self._on_train_done)
        self._train_worker.failed.connect(self._on_train_failed)
        self._train_worker.start()

    def _on_train_done(self, report):
        for btn in (self.train_btn, self.add_data_btn, self.clear_train_btn,
                    self.view_patterns_btn, self.generate_btn):
            btn.setEnabled(True)
        self._refresh_train_status()
        show_toast(self,
                    f"Training completed: {report.get('positives', 0)}+"
                    f"{report.get('negatives', 0)} samples, "
                    f"accuracy {report.get('train_accuracy', '-')}. "
                    f"Model saved locally.")

    def _on_train_failed(self, message):
        for btn in (self.train_btn, self.add_data_btn, self.clear_train_btn,
                    self.view_patterns_btn, self.generate_btn):
            btn.setEnabled(True)
        modal_error(self, "Training Failed",
                    f"{message}\n\nPrevious working model (if any) was kept.")

    def _view_learned_patterns(self):
        from app.services.local_agent.agent import TimetableAgent
        try:
            profile = TimetableAgent().get_learning_profile()
        except Exception as e:
            modal_error(self, "Learned Patterns", str(e))
            return
        lines = [f"Sources: {len(profile.get('sources', []))} file(s), "
                 f"{profile.get('total_lectures', 0)} lectures."]
        for key in sorted((profile.get("roles", {}) or {})):
            role = profile["roles"][key]
            lines.append(
                f"{key}: days {', '.join(role.get('preferred_days', [])) or '-'}; "
                f"times {', '.join(role.get('preferred_times', [])) or '-'}; "
                f"morning share {role.get('morning_share')}.")
        modal_info(self, "Learned Patterns", "\n".join(lines))

    def _clear_training(self):
        from app.services.local_agent.agent import TimetableAgent
        try:
            removed = TimetableAgent().clear_model()
        except Exception as e:
            modal_error(self, "Clear Training", str(e))
            return
        self._refresh_train_status()
        show_toast(self, "Training cleared." if removed else "No trained model stored.")

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

    def _planner(self):
        if self.planner_trained.isChecked():
            return "trained"
        if self.planner_local.isChecked():
            return "local"
        return "template"

    def _start(self, regenerate=False):
        ref_id = self.ref_combo.currentData()
        if ref_id is None:
            modal_error(self, "Intelligence", "Select a reference timetable first.")
            return
        planner = self._planner()
        if planner == "local" and not self._model_state.get("available", False):
            modal_error(self, "Ollama Planner Unavailable",
                        "The optional Ollama planner is unavailable.\n\n"
                        f"Endpoint: {self._model_state.get('endpoint', '') or 'not checked'}\n"
                        "Start Ollama on this PC with `ollama serve`, then pull a "
                        "model once with e.g. `ollama pull llama3.1`.\n\n"
                        "No account or API key is ever needed. The Trained Local "
                        "Model and Template patterns keep working fully offline "
                        "and never need Ollama.")
            return
        if planner == "trained" and not self._trained_state().get("trained", False):
            modal_error(self, "Timetable Agent not trained",
                        "Import previous timetable data and train the local agent "
                        "to personalize timetable generation.\n\n"
                        "Use Train Agent below (works fully offline, no Ollama "
                        "needed), or pick Template patterns.")
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
            planner=self._planner(),
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
        self.model_status.setText("Optional Ollama planner: checking localhost…")
        self._probe = _ProbeThread()
        self._probe.probed.connect(self._on_model_probed)
        self._probe.start()

    def _on_model_probed(self, state):
        self._model_state = state
        if state.get("available"):
            self.model_status.setText(
                f"Optional Ollama planner: connected ({state.get('model', '')}). "
                "Trained Local Model works without it.")
        elif state.get("running"):
            self.model_status.setText(
                "Optional Ollama planner: Ollama is running but no model is pulled. "
                "Run `ollama pull llama3.1` once to enable it, or use the "
                "Trained Local Model / Template patterns (offline).")
        else:
            self.model_status.setText(
                "Optional Ollama planner: unavailable (offline is fine). "
                "Trained Local Model and Template patterns never need Ollama; "
                "start it with `ollama serve` only for optional explanations.")

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
                self._record_applied_feedback()
            except Exception:
                pass
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

    def _record_applied_feedback(self):
        """Best-effort: accepted conflict-free schedules become feedback."""
        try:
            from app.models import Room, Subject, Teacher, WorkingDay
            from app.services.local_agent import adaptive
            session = get_session()
            try:
                rows = []
                for item in (self._result or {}).get("accepted", []):
                    sub = session.query(Subject).filter(
                        Subject.id == item.get("subject_id")).first()
                    tea = session.query(Teacher).filter(
                        Teacher.id == item.get("teacher_id")).first()
                    roo = session.query(Room).filter(
                        Room.id == item.get("room_id")).first()
                    day = session.query(WorkingDay).filter(
                        WorkingDay.id == item.get("day_id")).first()
                    if not (sub and tea and roo and day):
                        continue
                    try:
                        duration = int(sub.lecture_duration or 60)
                    except (TypeError, ValueError):
                        duration = 60
                    rows.append({
                        "code": sub.code, "name": sub.name,
                        "type": sub.subject_type or "Theory",
                        "duration": duration, "day": day.name,
                        "start": item.get("start_time", ""),
                        "end": item.get("end_time", ""),
                        "teacher": tea.name, "room": roo.name,
                        "source": "accepted-schedule",
                    })
                if rows:
                    adaptive.record_feedback(rows, session=session)
            finally:
                try:
                    session.close()
                except Exception:
                    pass
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
