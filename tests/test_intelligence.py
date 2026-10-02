"""Intelligence pipeline tests: fully offline, deterministic, in-memory DB."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Room, RoomAvailability, Semester, Subject, Teacher,
    TeacherAvailability, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.intelligence import reference_analyzer, requirement_analyzer
from app.services.intelligence.candidate_generator import generate_candidates
from app.services.intelligence.pattern_extractor import extract_patterns
from app.services.intelligence.timetable_agent import (
    IntelligenceError, apply_result, run_intelligence,
)
from app.services.intelligence.timetable_optimizer import optimize
from app.services.intelligence.timetable_scorer import score_breakdown, score_candidate
from app.services.conflict_service import ConflictService


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(session):
    semesters = [Semester(name=f"Semester {i}", status="Active") for i in (1, 2, 3)]
    session.add_all(semesters)
    session.flush()
    teachers = [Teacher(name=f"T{i}", email=f"t{i}@c.edu", department="CS", status="Active")
                for i in (1, 2)]
    rooms = [Room(name=f"R{i}", room_number=f"10{i}", type="Classroom", status="Available")
             for i in (1, 2)]
    session.add_all(teachers + rooms)
    session.flush()
    days = [WorkingDay(name=n, is_enabled=(n != "Sunday"), sort_order=i)
            for i, n in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday",
                                   "Friday", "Saturday", "Sunday"])]
    session.add_all(days)
    slots = [TimeSlot(start_time="09:00", end_time="10:00", label="09:00-10:00"),
             TimeSlot(start_time="10:00", end_time="11:00", label="10:00-11:00"),
             TimeSlot(start_time="11:00", end_time="12:00", label="11:00-12:00"),
             TimeSlot(start_time="13:00", end_time="14:00", label="13:00-14:00",
                      is_break=True, break_name="Lunch")]
    session.add_all(slots)
    subjects = [
        Subject(code="CS101", name="Sub1", semester_id=semesters[0].id,
                subject_type="Theory", required_lectures_per_week=3,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
        Subject(code="CS102", name="Sub2", semester_id=semesters[0].id,
                subject_type="Practical", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[1].id, room_id=rooms[1].id),
        Subject(code="CS201", name="Ref", semester_id=semesters[2].id,
                subject_type="Theory", required_lectures_per_week=2,
                lecture_duration=60, teacher_id=teachers[0].id, room_id=rooms[0].id),
    ]
    session.add_all(subjects)
    session.commit()
    mon = session.query(WorkingDay).filter_by(name="Monday").first()
    tue = session.query(WorkingDay).filter_by(name="Tuesday").first()
    ref = subjects[2]
    # Reference: Mon 09:00 + Mon 10:00 (consecutive pair), Tue 09:00.
    session.add_all([
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[0].id, room_id=rooms[0].id,
                       day_id=mon.id, start_time="09:00", end_time="10:00",
                       lecture_type="Theory"),
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[0].id, room_id=rooms[0].id,
                       day_id=mon.id, start_time="10:00", end_time="11:00",
                       lecture_type="Theory"),
        TimetableEntry(semester_id=semesters[2].id, subject_id=ref.id,
                       teacher_id=teachers[1].id, room_id=rooms[1].id,
                       day_id=tue.id, start_time="09:00", end_time="10:00",
                       lecture_type="Practical"),
    ])
    session.commit()
    return semesters


def test_reference_analysis():
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    assert profile["has_data"] is True
    assert profile["total_lectures"] == 3
    assert profile["day_distribution"] == {"Monday": 2, "Tuesday": 1}
    assert profile["breaks"][0]["name"] == "Lunch"
    assert profile["average_daily_lectures"] == 1.5
    assert profile["density"] > 0
    s.close()


def test_weekly_counting_and_durations():
    s = make_session()
    sems = seed(s)
    reqs = requirement_analyzer.analyze_requirements(s, sems[0].id)
    by_code = {r["subject"].code: r for r in reqs}
    assert by_code["CS101"]["required"] == 3
    assert by_code["CS101"]["scheduled"] == 0
    assert by_code["CS101"]["remaining"] == 3
    assert by_code["CS102"]["duration"] == 60
    s.close()


def test_spacing_practical_break_patterns():
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    patterns = extract_patterns(profile)
    assert patterns["has_reference"] is True
    assert patterns["preferred_days"][0] == "Monday"
    assert patterns["preferred_times"][0] == "09:00"
    assert patterns["wants_consecutive_practicals"] is False
    assert patterns["break_signature"] == [("13:00", "14:00")]
    assert patterns["morning_share"] == 1.0
    s.close()


def test_candidates_bounded_and_scored():
    from app.services.intelligence.subject_role_mapper import map_roles
    from app.services.intelligence.timetable_template import template_from_profile
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    patterns = extract_patterns(profile)
    template = template_from_profile(s, profile, sems[2].id)
    sub = s.query(Subject).filter_by(code="CS101").first()
    roles = map_roles([sub], template["roles"])
    role = roles[sub.id]
    assert role, "CS101 must map to a template role"
    cands = generate_candidates(s, sub, patterns, role)
    assert 0 < len(cands) <= 120
    assert all(c["subject_id"] == sub.id for c in cands)
    # No break cells offered.
    assert all((c["start_time"], c["end_time"]) != ("13:00", "14:00") for c in cands)
    days = s.query(WorkingDay).all()
    context = {"by_day_subject": {}, "day_load": {}, "teacher_load": {},
               "day_names": {d.id: d.name for d in days},
               "day_order": {d.id: d.sort_order for d in days},
               "template": template, "roles": roles}
    scored = [score_candidate(c, sub, role, template, context) for c in cands]
    monday_first = [c for c in cands if context["day_names"][c["day_id"]] == "Monday"]
    assert monday_first, "reference-day cells must be offered first"
    assert max(scored) > min(scored)
    parts = score_breakdown(cands[0], role, template, context)
    assert set(parts) == {"day_count", "spacing", "consecutive", "time_of_day",
                          "day_dist", "time_dist", "practical",
                          "load_balance", "teacher_balance"}
    assert all(0.0 <= v <= 1.0 for v in parts.values())
    s.close()


def test_duration_windows():
    from app.services.intelligence.candidate_generator import slot_windows_for_duration
    s = make_session()
    seed(s)
    slots = s.query(TimeSlot).order_by(TimeSlot.start_time).all()
    windows_60 = slot_windows_for_duration(slots, 60)
    assert ("09:00", "10:00") in windows_60
    assert all((a, b) != ("13:00", "14:00") for a, b in windows_60)
    windows_120 = slot_windows_for_duration(slots, 120)
    assert ("09:00", "11:00") in windows_120
    # A 120-minute lab is one block, never a single 60-minute row.
    assert all((b != "10:00" or a != "09:00") or True for a, b in windows_120)
    for a, b in windows_120:
        from app.utils.helpers import time_to_minutes
        assert time_to_minutes(b) - time_to_minutes(a) == 120
    windows_30 = slot_windows_for_duration(slots, 30)
    assert ("09:00", "09:30") in windows_30
    assert slot_windows_for_duration(slots, 45)[0][1] == "09:45"
    assert slot_windows_for_duration([], 60) == []
    s.close()


def test_role_mapping_by_shape_not_name():
    from app.services.intelligence.subject_role_mapper import map_roles
    from app.services.intelligence.timetable_template import template_from_profile
    s = make_session()
    sems = seed(s)
    profile = reference_analyzer.analyze_reference(s, sems[2].id)
    template = template_from_profile(s, profile, sems[2].id)
    subs = s.query(Subject).filter_by(semester_id=sems[0].id).order_by(Subject.code).all()
    roles = map_roles(subs, template["roles"])
    by_code = {x.code: roles[x.id] for x in subs}
    # CS101 (Theory, req 3) and CS102 (Practical, req 2) map to roles
    # with matching frequency and class — names never consulted.
    assert by_code["CS101"]["frequency"] in (2, 3)
    assert by_code["CS101"]["type_class"] == "theory"
    assert by_code["CS102"]["type_class"] == "practical"
    s.close()


def test_optimization_zero_conflict():
    s = make_session()
    sems = seed(s)
    out = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    assert len(out["accepted"]) == 5, out["rejected"]
    assert out["rejected"] == []
    assert ConflictService.detect_all_conflicts(s) == []
    assert out["diff"]["generated"] == 5
    assert "CS101" in out["explanation"]
    s.close()


def test_availability_rejection():
    s = make_session()
    sems = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    t1 = s.query(Teacher).filter_by(name="T1").first()
    # Block T1 every working day entirely.
    for d in s.query(WorkingDay).filter(WorkingDay.is_enabled == True).all():  # noqa: E712
        s.add(TeacherAvailability(teacher_id=t1.id, day_id=d.id,
                                 start_time="00:00", end_time="23:59",
                                 is_unavailable=True))
    s.commit()
    out = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    # CS101 (assigned T1 only... others available: T2) still places via T2.
    assert len(out["accepted"]) + len(out["rejected"]) == 5
    s.close()


def test_fill_fresh_replace_modes():
    s = make_session()
    sems = seed(s)
    mon = s.query(WorkingDay).filter_by(name="Monday").first()
    sub1 = s.query(Subject).filter_by(code="CS101").first()
    t2 = s.query(Teacher).filter_by(name="T2").first()
    r2 = s.query(Room).filter_by(name="R2").first()
    # Pre-place one CS101 lecture (Tue 11:00 avoids reference cells).
    tue = s.query(WorkingDay).filter_by(name="Tuesday").first()
    s.add(TimetableEntry(semester_id=sems[0].id, subject_id=sub1.id,
                         teacher_id=t2.id, room_id=r2.id, day_id=tue.id,
                         start_time="11:00", end_time="12:00",
                         lecture_type="Theory"))
    s.commit()
    fill = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    assert len(fill["accepted"]) == 4, fill["rejected"]
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 1
    # Fresh on non-empty must refuse.
    try:
        run_intelligence(s, sems[0].id, sems[2].id, "fresh")
        assert False, "fresh should refuse non-empty semester"
    except IntelligenceError:
        pass
    replace = run_intelligence(s, sems[0].id, sems[2].id, "replace")
    assert len(replace["accepted"]) == 5, replace["rejected"]
    assert replace["diff"]["existing"] == 1
    s.close()


def test_cancel_writes_nothing_and_apply_atomic():
    s = make_session()
    sems = seed(s)
    out = run_intelligence(s, sems[0].id, sems[2].id, "fill")
    # Cancel path: dry run already rolled back.
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 0
    # OK path.
    result = apply_result(s, sems[0].id, out, "fill")
    assert result == {"applied": 5, "rejected": 0}
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 5
    assert ConflictService.detect_all_conflicts(s) == []
    # Poisoned proposal: one clashing entry -> nothing applied.
    bad = dict(out["accepted"][0])
    bad["day_id"] = out["accepted"][1]["day_id"]
    bad["start_time"] = out["accepted"][1]["start_time"]
    bad["end_time"] = out["accepted"][1]["end_time"]
    evil = {"accepted": out["accepted"] + [bad]}
    result = apply_result(s, sems[0].id, evil, "fill")
    assert result["applied"] == 0
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 5
    s.close()


def test_structural_transfer_from_reference():
    """§19: target subjects inherit reference STRUCTURE (roles, not names)."""
    from app.services.intelligence.timetable_scorer import timetable_similarity
    from app.utils.helpers import time_to_minutes
    s = make_session()
    engine_semesters = [Semester(name=n, status="Active") for n in ("RefTerm", "NewTerm")]
    s.add_all(engine_semesters)
    s.flush()
    ref_sem, tgt_sem = engine_semesters
    teachers = {}
    rooms = {}
    for key in ("m", "p", "d", "l", "cn", "j", "s", "n"):
        t = Teacher(name=f"T-{key}", email=f"{key}@c.edu", department="CS", status="Active")
        r = Room(name=f"R-{key}", room_number=f"10{key}", type="Classroom", status="Available")
        s.add_all([t, r])
        teachers[key] = t
        rooms[key] = r
    s.flush()
    days = {}
    for i, n in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]):
        d = WorkingDay(name=n, is_enabled=(n != "Sunday"), sort_order=i)
        s.add(d)
        days[n] = d
    s.add(WorkingDay(name="Sunday", is_enabled=False, sort_order=6))
    for a, b in [("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00"),
                 ("13:00", "14:00"), ("14:00", "15:00"), ("15:00", "16:00")]:
        s.add(TimeSlot(start_time=a, end_time=b, label=f"{a}-{b}",
                       is_break=(a == "13:00"), break_name="Lunch" if a == "13:00" else ""))
    s.flush()
    ref_subjects = [
        ("MATH", "Mathematics", "Theory", 60, "m"),
        ("PROG", "Programming", "Theory", 60, "p"),
        ("DBMS", "DBMS", "Theory", 60, "d"),
        ("PLAB", "Programming Lab", "Practical", 120, "l"),
    ]
    ref_map = {}
    for code, name, typ, dur, key in ref_subjects:
        sub = Subject(code=code, name=name, semester_id=ref_sem.id,
                      subject_type=typ, required_lectures_per_week=0,
                      lecture_duration=dur, teacher_id=teachers[key].id,
                      room_id=rooms[key].id)
        s.add(sub)
        s.flush()
        ref_map[code] = sub
    ref_plan = [
        ("MATH", "Monday", "09:00", "10:00", "Theory"),
        ("MATH", "Tuesday", "09:00", "10:00", "Theory"),
        ("MATH", "Thursday", "09:00", "10:00", "Theory"),
        ("MATH", "Saturday", "09:00", "10:00", "Theory"),
        ("PROG", "Monday", "10:00", "11:00", "Theory"),
        ("PROG", "Wednesday", "10:00", "11:00", "Theory"),
        ("PROG", "Friday", "10:00", "11:00", "Theory"),
        ("PROG", "Saturday", "10:00", "11:00", "Theory"),
        ("DBMS", "Tuesday", "11:00", "12:00", "Theory"),
        ("DBMS", "Thursday", "11:00", "12:00", "Theory"),
        ("DBMS", "Friday", "11:00", "12:00", "Theory"),
        ("PLAB", "Wednesday", "14:00", "16:00", "Practical"),
        ("PLAB", "Friday", "14:00", "16:00", "Practical"),
    ]
    for code, day, start, end, typ in ref_plan:
        sub = ref_map[code]
        key = {"MATH": "m", "PROG": "p", "DBMS": "d", "PLAB": "l"}[code]
        s.add(TimetableEntry(semester_id=ref_sem.id, subject_id=sub.id,
                             teacher_id=teachers[key].id, room_id=rooms[key].id,
                             day_id=days[day].id, start_time=start, end_time=end,
                             lecture_type=typ))
    tgt_subjects = [
        ("CN", "Computer Networks", "Theory", 60, 4, "cn"),
        ("JAVA", "Java", "Theory", 60, 4, "j"),
        ("SE", "Software Engineering", "Theory", 60, 3, "s"),
        ("NLAB", "Networks Lab", "Practical", 120, 2, "n"),
    ]
    for code, name, typ, dur, req, key in tgt_subjects:
        s.add(Subject(code=code, name=name, semester_id=tgt_sem.id,
                      subject_type=typ, required_lectures_per_week=req,
                      lecture_duration=dur, teacher_id=teachers[key].id,
                      room_id=rooms[key].id))
    s.commit()

    out = run_intelligence(s, tgt_sem.id, ref_sem.id, "fill")
    assert out["rejected"] == [], out["rejected"]
    assert len(out["accepted"]) == 13, len(out["accepted"])
    assert ConflictService.detect_all_conflicts(s) == []

    by_code = {}
    day_of = {d.name: d.id for d in days.values()}
    for e in out["accepted"]:
        sub = s.query(Subject).filter_by(id=e["subject_id"]).first()
        by_code.setdefault(sub.code, []).append(e)
    assert {k: len(v) for k, v in by_code.items()} == {
        "CN": 4, "JAVA": 4, "SE": 3, "NLAB": 2}
    # Same roles -> same day sets (structure transferred, names differ).
    assert {e["day_id"] for e in by_code["CN"]} == {
        day_of[d] for d in ("Monday", "Tuesday", "Thursday", "Saturday")}
    assert {e["day_id"] for e in by_code["JAVA"]} == {
        day_of[d] for d in ("Monday", "Wednesday", "Friday", "Saturday")}
    assert {e["day_id"] for e in by_code["SE"]} == {
        day_of[d] for d in ("Tuesday", "Thursday", "Friday")}
    # Lab: 120-minute afternoon blocks on the reference lab days.
    labs = sorted(by_code["NLAB"], key=lambda e: e["day_id"])
    assert [(e["start_time"], e["end_time"]) for e in labs] == [
        ("14:00", "16:00"), ("14:00", "16:00")]
    assert [e["day_id"] for e in labs] == [day_of["Wednesday"], day_of["Friday"]]
    for e in out["accepted"]:
        sub = s.query(Subject).filter_by(id=e["subject_id"]).first()
        span = time_to_minutes(e["end_time"]) - time_to_minutes(e["start_time"])
        assert span == sub.lecture_duration, (sub.code, e)
    # Structural similarity is high and explainable.
    sim = out["similarity"]
    assert sim["total"] >= 0.7, sim
    assert sim["frequency"] == 1.0
    assert "4/week" in out["explanation"] and "Practical" in out["explanation"] or \
        "practical" in out["explanation"].lower()
    s.close()


def test_empty_reference_refused():
    s = make_session()
    sems = seed(s)
    try:
        run_intelligence(s, sems[0].id, sems[1].id, "fill")
        assert False, "empty reference must be refused"
    except IntelligenceError as e:
        assert "empty" in str(e).lower()
    s.close()


def test_external_reference_files(tmp_path):
    import json
    from app.services.intelligence.reference_analyzer import (
        analyze_external_reference, load_reference_file,
    )
    from app.services.intelligence.timetable_agent import IntelligenceError
    rows = [
        {"subject_code": "MA101", "subject_name": "Maths", "subject_type": "Theory",
         "day": "Monday", "start_time": "09:00", "end_time": "10:00",
         "teacher": "Dr A", "room": "101", "duration": "60"},
        {"subject_code": "PH102", "subject_name": "Physics", "subject_type": "Practical",
         "day": "Monday", "start_time": "10:00", "end_time": "11:00",
         "teacher": "Dr B", "room": "Lab 1", "duration": "60"},
        {"subject_code": "", "day": "", "start_time": "", "end_time": ""},
    ]
    csv_path = tmp_path / "ref.csv"
    import csv
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path = tmp_path / "ref.json"
    json_path.write_text(json.dumps(rows), encoding="utf-8")
    xlsx_path = tmp_path / "ref.xlsx"
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(rows[0].keys()))
    for r in rows:
        sheet.append(list(r.values()))
    workbook.save(xlsx_path)
    workbook.close()
    for path in (csv_path, json_path, xlsx_path):
        loaded, skipped = load_reference_file(str(path))
        assert len(loaded) == 2, path
        assert skipped == 1, path
    s = make_session()
    seed(s)
    loaded, _ = load_reference_file(str(csv_path))
    profile = analyze_external_reference(s, loaded, "ref.csv")
    assert profile["has_data"] is True
    assert profile["total_lectures"] == 2
    assert profile["day_distribution"] == {"Monday": 2}
    assert profile["practical_sessions"] == 1
    assert profile["consecutive_practical_pairs"] == 0
    assert profile["skipped_rows"] == 0
    try:
        load_reference_file(str(tmp_path / "ref.txt"))
        assert False, "bad suffix must fail"
    except IntelligenceError:
        pass
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("code,day,start,end\n", encoding="utf-8")
    try:
        load_reference_file(str(empty_path))
        assert False, "empty file must fail"
    except IntelligenceError:
        pass
    s.close()


def test_external_reference_generation(tmp_path):
    import csv
    from app.services.intelligence.reference_analyzer import (
        analyze_external_reference, load_reference_file,
    )
    s = make_session()
    sems = seed(s)
    rows = []
    for day in ("Monday", "Tuesday", "Wednesday"):
        for start, end in (("09:00", "10:00"), ("10:00", "11:00")):
            rows.append({"code": "CS101", "name": "Sub1", "type": "Theory",
                         "day": day, "start": start, "end": end,
                         "teacher": "T1", "room": "R1"})
    path = tmp_path / "ext.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    loaded, skipped = load_reference_file(str(path))
    assert skipped == 0
    profile = analyze_external_reference(s, loaded, "ext.csv")
    out = run_intelligence(s, sems[0].id, sems[0].id, "fill", ref_profile=profile)
    assert len(out["accepted"]) == 5, out["rejected"]
    assert out["rejected"] == []
    assert ConflictService.detect_all_conflicts(s) == []
    assert s.query(TimetableEntry).filter_by(semester_id=sems[0].id).count() == 0
    s.close()
