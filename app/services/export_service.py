import csv
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import TimetableEntry, Semester, Setting, WorkingDay

def _get_setting(session: Session, key: str, default: str = "") -> str:
    s = session.query(Setting).filter(Setting.key == key).first()
    if s is None or s.value is None:
        return default
    return s.value

def _ensure_parent(filepath: Path) -> Path:
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    return filepath

def _safe_sheet_title(name: str) -> str:
    import re
    name = (name or "Timetable").strip() or "Timetable"
    name = re.sub(r'[:/\\\?\*\[\]]', '-', name)
    return name[:31]

def export_csv(session: Session, semester_id: int, filepath: Path):
    filepath = _ensure_parent(filepath)
    entries = session.query(TimetableEntry).filter(TimetableEntry.semester_id == semester_id).order_by(TimetableEntry.day_id, TimetableEntry.start_time).all()
    semester = session.query(Semester).filter(Semester.id == semester_id).first()
    college = _get_setting(session, "college_name", "College")
    dept = _get_setting(session, "department", "Department")
    year = _get_setting(session, "academic_year", "2026-27")
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([f"{college} - {dept} - {year}"])
        writer.writerow([semester.name if semester else f"Semester {semester_id}"])
        writer.writerow([])
        writer.writerow(["Day", "Time", "Subject", "Subject Code", "Teacher", "Room", "Type"])
        for e in entries:
            writer.writerow([
                e.day.name if e.day else "",
                f"{e.start_time}-{e.end_time}",
                e.subject.name if e.subject else "",
                e.subject.code if e.subject else "",
                e.teacher.name if e.teacher else "",
                e.room.name if e.room else "",
                e.lecture_type
            ])

def export_excel(session: Session, semester_id: int, filepath: Path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    filepath = _ensure_parent(filepath)
    entries = session.query(TimetableEntry).filter(TimetableEntry.semester_id == semester_id).order_by(TimetableEntry.day_id, TimetableEntry.start_time).all()
    semester = session.query(Semester).filter(Semester.id == semester_id).first()
    college = _get_setting(session, "college_name", "College")
    dept = _get_setting(session, "department", "Department")
    year = _get_setting(session, "academic_year", "2026-27")
    wb = Workbook()
    ws = wb.active
    ws.title = _safe_sheet_title(semester.name if semester else "Timetable")
    ws.merge_cells('A1:G1')
    ws['A1'] = college
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A2:G2')
    ws['A2'] = f"{dept} - Academic Year: {year}"
    ws['A2'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A3:G3')
    ws['A3'] = semester.name if semester else ""
    ws['A3'].font = Font(bold=True, size=12)
    ws['A3'].alignment = Alignment(horizontal='center')
    headers = ["Day", "Time", "Subject", "Code", "Teacher", "Room", "Type"]
    fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    font = Font(color="FFFFFF", bold=True, size=10)
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col, value=h)
        cell.font = font
        cell.fill = fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    row = 6
    for e in entries:
        vals = [
            e.day.name if e.day else "",
            f"{e.start_time}-{e.end_time}",
            e.subject.name if e.subject else "",
            e.subject.code if e.subject else "",
            e.teacher.name if e.teacher else "",
            e.room.name if e.room else "",
            e.lecture_type
        ]
        for col, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=v)
            c.border = border
            c.alignment = Alignment(horizontal='center', vertical='center')
        row += 1
    if row == 6:
        ws.merge_cells(f'A6:G6')
        ws['A6'] = "No lectures scheduled"
        ws['A6'].alignment = Alignment(horizontal='center')
    for col in range(1, 8):
        ws.column_dimensions[chr(64+col)].width = 18
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['E'].width = 22
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    wb.save(filepath)

def export_pdf(session: Session, semester_id: int, filepath: Path):
    """Government Polytechnic style PDF — matches sample WhatsApp image."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.colors import HexColor
    from datetime import datetime

    entries = session.query(TimetableEntry).filter(TimetableEntry.semester_id == semester_id).order_by(TimetableEntry.day_id, TimetableEntry.start_time).all()
    semester = session.query(Semester).filter(Semester.id == semester_id).first()
    college = _get_setting(session, "college_name", "Government Polytechnic, Awasari")
    dept = _get_setting(session, "department", "Computer Engineering")
    year = _get_setting(session, "academic_year", "2026-27")

    # Abbreviations
    def _abbr(name: str) -> str:
        if not name:
            return ""
        parts = name.replace(".", " ").split()
        if len(parts) == 1:
            return parts[0][:3].upper()
        return "".join(p[0] for p in parts[:3]).upper()

    # College header in all caps like sample
    college_up = college.upper()
    dept_up = dept.upper()

    doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4), leftMargin=10*mm, rightMargin=10*mm, topMargin=8*mm, bottomMargin=8*mm, title=f"{semester.name if semester else 'Timetable'} - {year}")
    styles = getSampleStyleSheet()

    story = []

    # Top title block — Government style
    title_style = ParagraphStyle('GovTitle', parent=styles['Normal'], fontSize=13, alignment=TA_CENTER, textColor=HexColor(0x0F172A), fontName='Helvetica-Bold', leading=14, spaceAfter=1*mm)
    dept_style = ParagraphStyle('GovDept', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=HexColor(0x1E293B), fontName='Helvetica-Bold', leading=11, spaceAfter=1*mm)
    sub_style = ParagraphStyle('GovSub', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=HexColor(0x334155), fontName='Helvetica', leading=10, spaceAfter=1*mm)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=HexColor(0x64748B), leading=8)

    # Effective date — like sample 24/8/2026
    wef = datetime.now().strftime("%d/%m/%Y")
    # Try to get from settings if exists
    wef_setting = _get_setting(session, "wef_date", wef)
    if wef_setting:
        wef = wef_setting

    # Class label — map semester to year like THIRD YEAR COMPUTER (CO 5K)
    # Keep simple: use semester name
    class_label = f"CLASS: {semester.name.upper() if semester else 'SEMESTER'}"
    # Try to map to friendly — Sem 5 -> THIRD YEAR
    mapping = {"Semester 1": "FIRST YEAR", "Semester 2": "FIRST YEAR", "Semester 3": "SECOND YEAR", "Semester 4": "SECOND YEAR", "Semester 5": "THIRD YEAR", "Semester 6": "THIRD YEAR"}
    if semester and semester.name in mapping:
        class_label = f"CLASS: {mapping[semester.name]} COMPUTER ({semester.name.replace('Semester ', 'CO ')}K)"

    story.append(Paragraph(college_up, ParagraphStyle('t1', parent=title_style, fontSize=14)))
    story.append(Paragraph(f"DEPARTMENT OF {dept_up}", dept_style))
    story.append(Paragraph(f"TIME TABLE FOR ODD SEMESTER {year}", ParagraphStyle('t2', parent=dept_style, textColor=HexColor(0x2563EB), fontSize=9)))
    story.append(Paragraph(f"With Effect From: {wef} &nbsp;&nbsp;|&nbsp;&nbsp; {class_label} &nbsp;&nbsp;|&nbsp;&nbsp; Academic Year: {year}", sub_style))
    story.append(Spacer(1, 3*mm))

    # Days
    days = session.query(WorkingDay).filter(WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()
    day_names = [d.name.upper()[:3] for d in days]  # MON, TUE etc like sample has MONDAY etc but we use short
    # Full names for header
    day_full = [d.name.upper() for d in days]

    # Build time rows — use distinct times sorted, include BREAK
    from app.models import TimeSlot
    breaks = { (b.start_time, b.end_time): b.break_name or "BREAK" for b in session.query(TimeSlot).filter(TimeSlot.is_break==True, TimeSlot.is_enabled==True).all() }
    # Get all time ranges from entries + slots
    time_set = set()
    for e in entries:
        time_set.add((e.start_time, e.end_time))
    # Also add defined slots for structure even if no entry
    for s in session.query(TimeSlot).filter(TimeSlot.is_enabled==True).order_by(TimeSlot.start_time).all():
        time_set.add((s.start_time, s.end_time))
    # Sort
    def _to_min(t): 
        h,m = map(int, t.split(":"))
        return h*60+m
    time_list = sorted(time_set, key=lambda x: _to_min(x[0]))
    # If still empty, default
    if not time_list:
        time_list = [("10:15","11:15"),("11:15","12:15"),("12:15","13:15"),("13:15","13:45"),("13:45","14:45"),("14:45","15:45"),("15:45","16:45")]

    # Build lookup for entries
    lookup = {}
    for e in entries:
        key = (e.start_time, e.end_time, e.day.name if e.day else "")
        # Abbreviation like OSY(315319) — code + name
        code = e.subject.code if e.subject else ""
        # Teacher abbrev from name
        t_abbr = _abbr(e.teacher.name) if e.teacher else ""
        # Room
        room = e.room.room_number if e.room else ""
        # Lab batch like C1-STE/PR-LAB-2B (AAS) — we simplify to CODE - TeacherAbbr - Room
        # Use small font with line breaks
        txt = f"{code}<br/><font size=6>{t_abbr}</font><br/><font size=6>{room}</font>"
        if e.lecture_type in ("Lab", "Practical"):
            txt = f"{code}-LAB<br/><font size=6>{t_abbr}-{room}</font>"
        lookup[key] = Paragraph(txt, ParagraphStyle('cell', parent=styles['Normal'], fontSize=7, leading=7, alignment=TA_CENTER, fontName='Helvetica'))

    # Header row: Time + Days + maybe Subject key?
    header = [Paragraph("<b>TIME</b><br/><font size=6>Days →</font>", ParagraphStyle('hdr', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.white, fontName='Helvetica-Bold'))]
    for dn in day_full:
        header.append(Paragraph(f"<b>{dn}</b>", ParagraphStyle('hdr2', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.white, fontName='Helvetica-Bold')))

    data = [header]
    for st, et in time_list:
        time_label = f"{st} To<br/>{et}"
        is_break = (st, et) in breaks
        if is_break:
            # BREAK row spanning all days
            row = [Paragraph(f"<b>{st} To {et}</b>", ParagraphStyle('brk_time', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, fontName='Helvetica-Bold'))]
            brk = Paragraph(f"<b>{breaks[(st,et)]}</b>", ParagraphStyle('brk', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=HexColor(0x0F172A)))
            # Create row with BREAK spanning
            # For Table, we need to add BREAK cell and span via TableStyle SPAN
            row.append(brk)
            # Fill remaining with empty for span logic — we'll handle via SPAN in style
            for _ in range(len(day_full)-1):
                row.append(Paragraph("", small_style))
            data.append(row)
        else:
            row = [Paragraph(time_label, ParagraphStyle('tlabel', parent=styles['Normal'], fontSize=6, leading=7, alignment=TA_CENTER, fontName='Helvetica'))]
            for d in days:
                key = (st, et, d.name)
                cell = lookup.get(key, Paragraph("", small_style))
                row.append(cell)
            data.append(row)

    # Column widths: Time narrow, days equal
    total_w = 275*mm
    time_w = 22*mm
    day_w = (total_w - time_w) / max(len(day_full), 1) if day_full else 30*mm
    col_widths = [time_w] + [day_w]*len(day_full)

    # Row heights — BREAK row taller
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0,0), (-1,0), HexColor(0x0F172A)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BOX', (0,0), (-1,-1), 0.8, colors.black),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, HexColor(0xF8FAFC)]),
    ]
    # Add SPAN for BREAK rows and highlight
    for idx, (st,et) in enumerate(time_list, start=1):
        if (st,et) in breaks:
            # Span from col 1 to end
            style.append(('SPAN', (1, idx), (-1, idx)))
            style.append(('BACKGROUND', (0, idx), (-1, idx), HexColor(0xE2E8F0)))
            style.append(('TEXTCOLOR', (1, idx), (1, idx), HexColor(0x0F172A)))
            style.append(('FONTNAME', (1, idx), (1, idx), 'Helvetica-Bold'))
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 4*mm))

    # Footer: Subject Teacher with Abbreviation + Load + Signatures — like sample
    # Collect unique subjects in this semester
    from app.models import Subject
    subjects = session.query(Subject).filter(Subject.semester_id==semester_id).order_by(Subject.code).all()
    # Build abbreviation map
    subj_rows = []
    for s in subjects:
        t_name = s.assigned_teacher.name if s.assigned_teacher else "-"
        t_abbr = _abbr(t_name) if t_name != "-" else "-"
        subj_rows.append([f"{s.code} - {s.name}", f"{t_name} ({t_abbr})", s.subject_type])
    # If no subjects, add placeholder
    if not subj_rows:
        subj_rows = [["No subjects", "-", "-"]]

    # Two-column footer: left Subject-Teacher table, right Load/signature
    footer_data = []
    # Header for subject table
    left_header = [Paragraph("<b>Subject Name & Teacher with Abbreviation</b>", ParagraphStyle('fh', parent=small_style, fontSize=7, alignment=TA_CENTER, fontName='Helvetica-Bold'))]
    # Build left table data
    left_table_data = [[Paragraph("<b>Subject (Code)</b>", small_style), Paragraph("<b>Teacher (Abbr)</b>", small_style), Paragraph("<b>Type</b>", small_style)]]
    for code_name, teacher_abbr, typ in subj_rows:
        left_table_data.append([Paragraph(code_name, small_style), Paragraph(teacher_abbr, small_style), Paragraph(typ, small_style)])
    left_tbl = Table(left_table_data, colWidths=[45*mm, 40*mm, 18*mm])
    left_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor(0x0F172A)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, HexColor(0xF1F5F9)]),
    ]))

    # Right side: Practical Load / Theory Load + signatures
    # Count practical vs theory
    prac = sum(1 for s in subjects if s.subject_type in ("Lab", "Practical"))
    theory = len(subjects) - prac
    right_data = [
        [Paragraph(f"<b>Practical Load:</b> {prac*2} hrs", small_style), Paragraph(f"<b>Theory Load:</b> {theory*4} hrs", small_style)],
        [Spacer(1, 6*mm), Spacer(1, 6*mm)],
        [Paragraph("Mrs. Asha S Patil<br/><font size=6>Time Table Co-ordinator</font>", ParagraphStyle('sig', parent=small_style, alignment=TA_CENTER, leading=7)), Paragraph("G. P. Awasari<br/><font size=6>Head of Department</font>", ParagraphStyle('sig2', parent=small_style, alignment=TA_CENTER, leading=7))],
        [Paragraph("Dr. V B Jawade<br/><font size=6>Academic Coordinator</font>", ParagraphStyle('sig', parent=small_style, alignment=TA_CENTER, leading=7)), Paragraph("Dr. Vitthal S Bandal<br/><font size=6>Principal</font>", ParagraphStyle('sig2', parent=small_style, alignment=TA_CENTER, leading=7))],
    ]
    right_tbl = Table(right_data, colWidths=[35*mm, 35*mm])
    right_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))

    footer = Table([[left_tbl, right_tbl]], colWidths=[103*mm, 72*mm])
    footer.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(footer)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Generated by College Timetable Manager • {college} • {year} • {datetime.now().strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('foot', parent=small_style, fontSize=6, textColor=HexColor(0x94A3B8), alignment=TA_CENTER)))

    doc.build(story)
