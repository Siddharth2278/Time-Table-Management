"""Phase 1 local agent tests: learner + storage. No network, no Ollama needed."""
import json

import pytest

from app.services.local_agent import pattern_store
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import DEFAULT_ENDPOINT, OllamaClient
from app.services.local_agent.schemas import LearningError
from app.services.local_agent.timetable_learner import learn, load_rows

ROWS = [
    {"subject_code": "MA101", "subject_name": "Maths", "subject_type": "Theory",
     "day": "Monday", "start_time": "09:00", "end_time": "10:00",
     "teacher": "Dr A", "room": "101", "duration": "60"},
    {"subject_code": "MA101", "subject_name": "Maths", "subject_type": "Theory",
     "day": "Wednesday", "start_time": "09:00", "end_time": "10:00",
     "teacher": "Dr A", "room": "101", "duration": "60"},
    {"subject_code": "MA101", "subject_name": "Maths", "subject_type": "Theory",
     "day": "Friday", "start_time": "09:00", "end_time": "10:00",
     "teacher": "Dr A", "room": "101", "duration": "60"},
    {"subject_code": "PH102", "subject_name": "Physics", "subject_type": "Practical",
     "day": "Tuesday", "start_time": "14:00", "end_time": "16:00",
     "teacher": "Dr B", "room": "Lab 1", "duration": "120"},
    {"subject_code": "PH102", "subject_name": "Physics", "subject_type": "Practical",
     "day": "Thursday", "start_time": "14:00", "end_time": "16:00",
     "teacher": "Dr B", "room": "Lab 1", "duration": "120"},
]


def write_files(tmp_path):
    import csv
    csv_path = tmp_path / "ref.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()))
        writer.writeheader()
        writer.writerows(ROWS)
    json_path = tmp_path / "ref.json"
    json_path.write_text(json.dumps(ROWS), encoding="utf-8")
    xlsx_path = tmp_path / "ref.xlsx"
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(ROWS[0].keys()))
    for row in ROWS:
        sheet.append(list(row.values()))
    workbook.save(xlsx_path)
    workbook.close()
    return csv_path, json_path, xlsx_path


def test_learn_csv_xlsx_json_agree(tmp_path):
    profiles = []
    for path in write_files(tmp_path):
        rows, skipped = load_rows(str(path))
        assert skipped == 0, path
        assert len(rows) == 5
        profiles.append(learn(rows, source_label=str(path)))
    first = profiles[0]
    for other in profiles[1:]:
        assert other["total_lectures"] == first["total_lectures"] == 5
        assert other["roles"] == first["roles"]
        assert other["patterns"] == first["patterns"]


def test_structural_patterns_not_names():
    from app.services.local_agent.timetable_learner import learn as do_learn
    from app.services.local_agent.schemas import LectureRow
    rows = [LectureRow(code=r["subject_code"], name=r["subject_name"],
                       type=r["subject_type"], duration=int(r["duration"]),
                       day=r["day"], start=r["start_time"], end=r["end_time"],
                       teacher=r["teacher"], room=r["room"]) for r in ROWS]
    profile = do_learn(rows, source_label="t")
    assert profile["version"] == 1
    assert profile["total_lectures"] == 5
    # Roles are keyed by structure (type|duration|frequency), never names.
    assert set(profile["roles"]) == {"theory|60|3", "practical|120|2"}
    theory = profile["roles"]["theory|60|3"]
    assert theory["preferred_days"] == ["Friday", "Monday", "Wednesday"]
    assert theory["preferred_times"] == ["09:00"]
    assert theory["morning_share"] == 1.0
    practical = profile["roles"]["practical|120|2"]
    assert practical["morning_share"] == 0.0
    patterns = profile["patterns"]
    # All five days tie at 1 lecture each: alphabetical tie-break.
    assert patterns["preferred_days"] == [
        "Friday", "Monday", "Thursday", "Tuesday", "Wednesday"]
    assert patterns["theory_duration"] == 60
    assert patterns["practical_duration"] == 120
    assert patterns["teacher_workload"] == {"Dr A": 3, "Dr B": 2}
    assert patterns["average_daily_load"] == 1.0
    for name in ("MA101", "PH102", "Maths", "Physics", "Dr A"):
        assert name not in profile["roles"]


def test_insufficient_and_invalid_files(tmp_path):
    rows, _ = load_rows(str(write_files(tmp_path)[0]))
    with pytest.raises(LearningError):
        learn(rows[:2], source_label="tiny")
    with pytest.raises(LearningError):
        load_rows(str(tmp_path / "ref.txt"))
    empty = tmp_path / "empty.csv"
    empty.write_text("code,day,start,end\n", encoding="utf-8")
    with pytest.raises(LearningError):
        learn(*load_rows(str(empty))[:1], source_label="empty")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(LearningError):
        load_rows(str(bad))


def test_store_roundtrip_update_clear(tmp_path):
    rows, _ = load_rows(str(write_files(tmp_path)[0]))
    from app.services.local_agent.timetable_learner import learn as do_learn
    profile = do_learn(rows, source_label="a.csv")
    saved = pattern_store.save_profile(profile, tmp_path)
    assert saved.exists()
    loaded = pattern_store.load_profile(tmp_path)
    assert loaded["total_lectures"] == 5
    assert loaded["sources"] == ["a.csv"]
    extra = do_learn(rows, source_label="b.csv")
    merged = pattern_store.update_profile(extra, tmp_path)
    assert merged["total_lectures"] == 10
    assert set(merged["sources"]) == {"a.csv", "b.csv"}
    assert merged["patterns"]["teacher_workload"] == {"Dr A": 6, "Dr B": 4}
    assert pattern_store.load_profile(tmp_path)["total_lectures"] == 10
    assert pattern_store.clear_profile(tmp_path) is True
    assert pattern_store.clear_profile(tmp_path) is False
    with pytest.raises(LearningError):
        pattern_store.load_profile(tmp_path)
    with pytest.raises(LearningError):
        pattern_store.save_profile({"version": 999}, tmp_path)


def test_agent_interface_end_to_end(tmp_path, monkeypatch):
    csv_path = write_files(tmp_path)[0]
    agent = TimetableAgent(data_dir=tmp_path)
    summary = agent.analyze_reference_timetable(str(csv_path))
    assert summary["lectures"] == 5
    assert summary["subjects"] == 2
    assert summary["roles"] == 2
    assert summary["saved_to"].endswith("timetable_learning_profile.json")
    profile = agent.get_learning_profile()
    assert profile["total_lectures"] == 5
    assert agent.clear_learning_profile() is True
    with pytest.raises(LearningError):
        agent.get_learning_profile()
    with pytest.raises(LearningError):
        agent.analyze_reference_timetable(str(tmp_path / "missing.csv"))


def test_ollama_down_and_unavailable(monkeypatch):
    import socket
    import urllib.request

    def _fail(*args, **kwargs):
        raise OSError("network blocked in test")

    monkeypatch.setattr(socket, "socket", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    client = OllamaClient()
    assert client.endpoint == DEFAULT_ENDPOINT
    assert client.is_running() is False
    assert client.models() == []
    with pytest.raises(LearningError):
        client.ensure_ready()
    agent = TimetableAgent(data_dir=None, ollama=client)
    with pytest.raises(LearningError):
        agent.check_model()
    # Learning itself never touches the network: still works.
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "r.csv"
        import csv as _csv
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = _csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()))
            writer.writeheader()
            writer.writerows(ROWS)
        summary = TimetableAgent(data_dir=Path(tmp)).analyze_reference_timetable(
            str(csv_path))
        assert summary["lectures"] == 5


def test_ollama_up_but_model_missing(monkeypatch):
    client = OllamaClient()
    monkeypatch.setattr(OllamaClient, "is_running", lambda self: True)
    monkeypatch.setattr(OllamaClient, "models", lambda self: ["other:tag"])
    with pytest.raises(LearningError):
        client.ensure_ready("llama3.1")
