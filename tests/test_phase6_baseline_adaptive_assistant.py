"""Phase 6 tests: baseline deployment, adaptation, assistant, voice bounds.

All offline. Voice engines are optional; tests assert graceful degradation,
never real audio. Model claims stay structural (rows/separation), never
generic AI accuracy.
"""
import csv
import json
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Room, Semester, Subject, Teacher, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.conflict_service import ConflictService
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.schemas import LearningError

HISTORY = [
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": "60",
     "day": "Monday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": "60",
     "day": "Wednesday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "MA101", "name": "Maths", "type": "Theory", "duration": "60",
     "day": "Friday", "start": "09:00", "end": "10:00",
     "teacher": "Dr A", "room": "101"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": "120",
     "day": "Tuesday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1"},
    {"code": "PH102", "name": "Physics", "type": "Practical", "duration": "120",
     "day": "Thursday", "start": "14:00", "end": "16:00",
     "teacher": "Dr B", "room": "Lab 1"},
    {"code": "CS103", "name": "Programming", "type": "Theory", "duration": "60",
     "day": "Monday", "start": "10:00", "end": "11:00",
     "teacher": "Dr C", "room": "102"},
    {"code": "CS103", "name": "Programming", "type": "Theory", "duration": "60",
     "day": "Thursday", "start": "10:00", "end": "11:00",
     "teacher": "Dr C", "room": "102"},
]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
    sem = Semester(name="Semester 1", status="Active")
    session.add(sem)
    session.flush()
    teachers = [Teacher(name=f"T{i}", email=f"t{i}@c.edu", department="CS",
                        status="Active") for i in (1, 2)]
    rooms = [Room(name=f"R{i}", room_number=f"10{i}", type="Classroom",
                  status="Available") for i in (1, 2)]
    session.add_all(teachers + rooms)
    session.flush()
    days = [WorkingDay(name=n, is_enabled=(n != "Sunday"), sort_order=i)
            for i, n in enumerate(["Monday", "Tuesday", "Wednesday",
                                   "Thursday", "Friday", "Saturday",
                                   "Sunday"])]
    session.add_all(days)
    slots = [TimeSlot(start_time="09:00", end_time="10:00", label="09:00-10:00"),
             TimeSlot(start_time="10:00", end_time="11:00", label="10:00-11:00"),
             TimeSlot(start_time="11:00", end_time="12:00", label="11:00-12:00"),
             TimeSlot(start_time="14:00", end_time="15:00", label="14:00-15:00"),
             TimeSlot(start_time="15:00", end_time="16:00", label="15:00-16:00")]
    session.add_all(slots)
    subjects = [
        Subject(code="NW101", name="Networks", semester_id=sem.id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id,
                room_id=rooms[0].id),
    ]
    session.add_all(subjects)
    session.commit()
    return sem


# ---- baseline deployment ----

def test_baseline_export_validate(tmp_path):
    from app.services.local_agent.baseline import (
        export_baseline, validate_baseline_dir,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    out = export_baseline(tmp_path / "admin", tmp_path / "seed")
    manifest = out["manifest"]
    assert manifest["package_format"] == 1
    assert manifest["lectures"] == len(HISTORY)
    assert manifest["backend"] in ("sklearn-hgb", "stdlib-logreg")
    assert set(manifest["checksums"]) >= {
        "model.joblib", "metadata.json", "training_rows.jsonl",
        "timetable_learning_profile.json"}
    assert validate_baseline_dir(tmp_path / "seed")["lectures"] == len(HISTORY)


def test_baseline_tamper_rejected(tmp_path):
    from app.services.local_agent.baseline import (
        export_baseline, validate_baseline_dir,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    export_baseline(tmp_path / "admin", tmp_path / "seed")
    (tmp_path / "seed" / "metadata.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(LearningError):
        validate_baseline_dir(tmp_path / "seed")


def test_seed_and_generate_immediately(tmp_path, monkeypatch):
    """Simulated install: seed from baseline, generate with no retraining."""
    from app.services.local_agent.baseline import (
        export_baseline, seed_active_from_baseline,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    export_baseline(tmp_path / "admin", tmp_path / "seed")
    fresh = tmp_path / "pcB"
    info = seed_active_from_baseline(fresh, bundled=tmp_path / "seed")
    assert info and info["seeded"] is True
    agent_b = TimetableAgent(data_dir=fresh)
    assert agent_b.model_status()["trained"] is True
    # Seeding twice never overwrites the active model.
    assert seed_active_from_baseline(fresh, bundled=tmp_path / "seed") is None

    def _boom(*a, **k):
        raise AssertionError("trained generation must not touch Ollama")

    monkeypatch.setattr(OllamaClient, "generate", _boom)
    monkeypatch.setattr(OllamaClient, "ensure_ready", _boom)
    s = make_session()
    sem = seed(s)
    result = agent_b.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    assert ConflictService.detect_all_conflicts(s) == []
    s.close()


def test_repo_baseline_valid():
    root = Path(__file__).resolve().parents[1]
    seed = root / "assets" / "baseline_agent"
    assert (seed / "manifest.json").is_file(), "run scripts/build_baseline.py first"
    from app.services.local_agent.baseline import validate_baseline_dir
    manifest = validate_baseline_dir(seed)
    assert manifest["backend"] in ("sklearn-hgb", "stdlib-logreg")
    assert manifest["lectures"] >= 5


# ---- versions / rollback / feedback / adaptive ----

def test_version_snapshot_and_rollback(tmp_path):
    from app.services.local_agent import model_versions
    agent = TimetableAgent(data_dir=tmp_path)
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    name = model_versions.snapshot_version(tmp_path, label="test")
    assert name and model_versions.list_versions(tmp_path)
    # Corrupt the active model, then roll back to the snapshot.
    (tmp_path / "timetable_agent_model" / "model.joblib").write_bytes(b"junk")
    out = model_versions.rollback_to_version(tmp_path, name)
    assert out["restored"] == name
    assert TimetableAgent(data_dir=tmp_path).model_status()["trained"] is True


def test_feedback_validation_and_threshold(tmp_path):
    from app.services.local_agent import adaptive
    old_min = adaptive.get_setting("adaptive_min_examples")
    adaptive.set_setting("adaptive_min_examples", "2")
    try:
        agent = TimetableAgent(data_dir=tmp_path)
        agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
        good = dict(HISTORY[0])
        good["source"] = "manual-edit"
        assert adaptive.record_feedback([good], tmp_path) == 1
        with pytest.raises(LearningError):
            adaptive.record_feedback([{"code": "", "day": "Monday",
                                       "start": "09:00", "end": "10:00"}],
                                     tmp_path)
        with pytest.raises(LearningError):
            adaptive.record_feedback([dict(good, start="10:00",
                                           end="09:00")], tmp_path)
        # Second valid row reaches the threshold of 2.
        good2 = dict(HISTORY[1])
        good2["source"] = "manual-edit"
        adaptive.record_feedback([good2], tmp_path)
        status = adaptive.adaptive_status(tmp_path)
        assert status["pending"] == 2
        assert status["retrain_pending"] is True
        report = adaptive.maybe_retrain(tmp_path)
        assert report and report["feedback_consumed"] == 2
        assert adaptive.pending_feedback(tmp_path) == []
        history = adaptive.training_history(tmp_path)
        assert history["versions"]
    finally:
        adaptive.set_setting("adaptive_min_examples", old_min)


def test_feedback_conflict_rejected(tmp_path):
    from app.services.local_agent import adaptive
    s = make_session()
    sem = seed(s)
    sub = s.query(Subject).first()
    tea = s.query(Teacher).all()
    roo = s.query(Room).all()
    day = s.query(WorkingDay).filter_by(name="Monday").first()
    # Occupy Monday 09:00 twice with the same teacher: second placement
    # conflicts, so identical feedback must be refused.
    s.add(TimetableEntry(semester_id=sem.id, subject_id=sub.id,
                         teacher_id=tea[0].id, room_id=roo[0].id,
                         day_id=day.id, start_time="09:00", end_time="10:00",
                         lecture_type="Theory"))
    s.commit()
    bad = {"code": sub.code, "name": sub.name, "type": "Theory",
           "duration": 60, "day": "Monday", "start": "09:00",
           "end": "10:00", "teacher": tea[0].name, "room": roo[1].name,
           "source": "manual-edit"}
    with pytest.raises(LearningError):
        adaptive.record_feedback([bad], tmp_path, session=s)
    s.close()


def test_package_zip_roundtrip_and_rejections(tmp_path):
    from app.services.local_agent.baseline import (
        export_package, import_package,
    )
    agent = TimetableAgent(data_dir=tmp_path / "admin")
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    out = export_package(tmp_path / "admin", tmp_path / "pkg.zip")
    assert Path(out["zip"]).is_file()
    import_package(tmp_path / "pkg.zip", tmp_path / "pc")
    assert TimetableAgent(data_dir=tmp_path / "pc").model_status()["trained"] is True
    # Incomplete zip rejected.
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("metadata.json", "{}")
    with pytest.raises(LearningError):
        import_package(bad, tmp_path / "pc2")
    # Executable content rejected.
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as archive:
        for name in ("model.joblib", "metadata.json", "training_rows.jsonl",
                     "timetable_learning_profile.json", "manifest.json",
                     "run.py"):
            archive.writestr(name, "x")
    with pytest.raises(LearningError):
        import_package(evil, tmp_path / "pc3")


def test_pc_isolation_with_feedback(tmp_path):
    from app.services.local_agent import adaptive
    old_min = adaptive.get_setting("adaptive_min_examples")
    adaptive.set_setting("adaptive_min_examples", "99")
    try:
        a_dir, b_dir = tmp_path / "a", tmp_path / "b"
        TimetableAgent(data_dir=a_dir).train_agent(
            [write_csv(str(tmp_path / "h.csv"), HISTORY)])
        other = [dict(r, code="ZZ") for r in HISTORY[:5]]
        TimetableAgent(data_dir=b_dir).train_agent(
            [write_csv(str(tmp_path / "o.csv"), other)])
        adaptive.record_feedback([dict(HISTORY[0], source="manual-edit")],
                                 a_dir)
        assert len(adaptive.pending_feedback(a_dir)) == 1
        assert adaptive.pending_feedback(b_dir) == []
        assert TimetableAgent(data_dir=b_dir).model_status()["stored_rows"] == 5
    finally:
        adaptive.set_setting("adaptive_min_examples", old_min)


# ---- assistant ----

def test_assistant_typed_tools_and_confirmation():
    from app.services.assistant.service import AssistantService
    s = make_session()
    sem = seed(s)
    svc = AssistantService()
    out = svc.handle_text("Show my AI training status.")
    assert "Pending examples" in out["reply"]
    out = svc.handle_text("Show timetable conflicts.")
    assert "conflict" in out["reply"].lower()
    out = svc.handle_text("Add a teacher named Rahul.")
    assert "Rahul" in out["reply"]
    assert s.query(Teacher).filter_by(name="Rahul").first() is None  # own session
    s.close()
    # Destructive flow needs explicit Yes.
    out = svc.handle_text("Delete all Semester 4 timetable entries.")
    assert out.get("needs_confirmation") is True
    out = svc.handle_text("No")
    assert "Cancelled" in out["reply"]
    out = svc.handle_text("Delete all Semester 4 timetable entries.")
    out = svc.handle_text("Yes")
    assert "Semester" in out["reply"]


def test_assistant_rejects_unknown_tool_and_bad_args():
    from app.services.assistant import tools
    with pytest.raises(LearningError):
        tools.dispatch("drop_tables", {})
    with pytest.raises(LearningError):
        tools.dispatch("move_lecture", {"bogus": 1})
    assert "drop_tables" not in tools.TOOLS
    # No tool exposes SQL or eval.
    import inspect
    for name, spec in tools.TOOLS.items():
        src = inspect.getsource(spec["func"]).lower()
        assert "execute(" not in src and "eval(" not in src, name


def test_assistant_ambiguous_asks_not_guesses():
    from app.services.assistant.service import AssistantService
    svc = AssistantService()
    out = svc.handle_text("Move this to Friday.")
    assert "Which lecture" in out["reply"]
    out = svc.handle_text("asdlfkj qwerty zzz")
    assert "What should I do" in out["reply"] or "can generate" in out["reply"]


def test_voice_bounds_graceful():
    from app.services.assistant import voice_io
    status = voice_io.stt_status()
    assert isinstance(status["stt_available"], bool)
    assert isinstance(status["tts_available"], bool)
    # speak(False) never raises and never speaks.
    assert voice_io.speak("hello", enabled=False) is False


def test_offline_trained_generation_no_network(tmp_path, monkeypatch):
    import socket
    import urllib.request

    def _fail(*a, **k):
        raise OSError("network blocked")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    agent = TimetableAgent(data_dir=tmp_path)
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    s = make_session()
    sem = seed(s)
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    s.close()


def test_installer_and_spec_baseline_rules():
    root = Path(__file__).resolve().parents[1]
    spec = (root / "CollegeTimetable.spec").read_text(encoding="utf-8")
    assert "baseline_agent" in spec
    assert "assistant_dialog" in spec
    iss = (root / "installer" / "CollegeTimetableSetup.iss").read_text(
        encoding="utf-8")
    sources = [l for l in iss.splitlines() if l.strip().lower().startswith("source:")]
    bundled = " ".join(sources).lower()
    for forbidden in ("timetable.db", "training_rows.jsonl",
                      "timetable_learning_profile"):
        assert forbidden not in bundled
    assert "UninstallDelete" in iss


def test_error_paths_are_user_safe(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    with pytest.raises(LearningError):
        agent.train_agent([str(tmp_path / "missing.csv")])
    empty = tmp_path / "empty.csv"
    empty.write_text("code,day,start,end\n", encoding="utf-8")
    with pytest.raises(LearningError):
        agent.train_agent([str(empty)])
    with pytest.raises(LearningError):
        agent.generate_dry_run(make_session(), 9999, "fill", planner="trained")


def test_training_report_has_cost_metrics(tmp_path):
    agent = TimetableAgent(data_dir=tmp_path)
    report = agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    assert isinstance(report.get("train_seconds"), (int, float))
    assert report.get("train_seconds", -1) >= 0
    assert isinstance(report.get("model_bytes"), int)
    assert report["model_bytes"] > 0


def test_evaluation_reports_real_data(tmp_path):
    from app.services.intelligence.evaluation import (
        evaluate_proposal, summary_lines,
    )
    s = make_session()
    sem = seed(s)
    agent = TimetableAgent(data_dir=tmp_path)
    agent.train_agent([write_csv(str(tmp_path / "h.csv"), HISTORY)])
    result = agent.generate_dry_run(s, sem.id, "fill", planner="trained")
    assert result.accepted
    for e in result.accepted:
        e["semester_id"] = sem.id
    report = evaluate_proposal(s, result.accepted,
                               similarity=result.structural_similarity)
    assert report["accepted"] == len(result.accepted)
    assert report["conflicts"] == 0
    assert report["daily_distribution"]
    assert report["teacher_workload"]
    assert summary_lines(report)
    s.close()


def test_assistant_extended_hints():
    from app.services.assistant.service import AssistantService
    svc = AssistantService()
    out = svc.handle_text("Export Semester 5 timetable to PDF.")
    assert "Export" in out["reply"] or "export" in out["reply"].lower()
    out = svc.handle_text("Backup my data.")
    assert "Backup" in out["reply"]
