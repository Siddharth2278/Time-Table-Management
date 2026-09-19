from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QScrollArea, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from app.database import get_session
from app.models import Semester, Subject, TimetableEntry
from app.services.conflict_service import ConflictService

SEM_ACCENTS = ["#4F46E5", "#0EA5E9", "#059669", "#D97706", "#7C3AED", "#DB2777"]


class SemesterCard(QFrame):
    clicked = Signal(int)
    def __init__(self, semester, completion, accent="#4F46E5"):
        super().__init__()
        self.semester_id = semester.id
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-top: 4px solid {accent};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1.5px solid {accent};
                border-top: 4px solid {accent};
                background: #F8FAFC;
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel(semester.name)
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A; border: none; background: transparent;")
        layout.addWidget(title)
        status = QLabel(semester.status or "Active")
        status.setStyleSheet("font-size: 11px; color: #64748B; border: none; background: transparent;")
        layout.addWidget(status)
        # Progress
        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setValue(int(completion["completion_pct"]))
        bar.setFormat(f"{completion['completion_pct']}%")
        bar.setStyleSheet("""
            QProgressBar { border: 1px solid #E2E8F0; border-radius: 8px; background: #F1F5F9; text-align: center; height: 14px; font-size: 10px; color: #1E293B; }
            QProgressBar::chunk { background: #4F46E5; border-radius: 7px; }
        """)
        layout.addWidget(bar)
        detail = QLabel(f"{completion['scheduled']}/{completion['required']} lectures  \u2022  Remaining: {completion['remaining']}")
        detail.setStyleSheet("font-size: 11px; color: #475569; border: none; background: transparent;")
        layout.addWidget(detail)
        hint = QLabel("Click to open timetable \u2192")
        hint.setStyleSheet(f"font-size: 11px; color: {accent}; font-weight: 700; border: none; background: transparent;")
        layout.addWidget(hint)
        self.setMinimumHeight(140)
        self.setMinimumWidth(220)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.semester_id)
        super().mousePressEvent(event)

class SemesterView(QWidget):
    openTimetable = Signal(int)
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)
        title = QLabel("Semesters Overview")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("Click a semester to open its timetable. Each semester has one timetable.")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(sub)

        # Grid
        self.container = QWidget()
        self.grid = QVBoxLayout(self.container)
        # We'll use scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.container)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(self.scroll)

        # Internal grid for cards (2 rows 3 cols)
        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background: transparent;")
        from PySide6.QtWidgets import QGridLayout
        self.cards_layout = QGridLayout(self.cards_widget)
        self.cards_layout.setSpacing(16)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.grid.addWidget(self.cards_widget)
        self.grid.addStretch()

    def refresh(self):
        # Clear
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        session = get_session()
        try:
            sems = session.query(Semester).order_by(Semester.id).all()
            made = []
            for idx, sem in enumerate(sems):
                comp = ConflictService.calculate_timetable_completion(session, sem.id)
                card = SemesterCard(sem, comp, SEM_ACCENTS[idx % len(SEM_ACCENTS)])
                card.clicked.connect(self.openTimetable.emit)
                row = idx // 3
                col = idx % 3
                self.cards_layout.addWidget(card, row, col)
                made.append(card)
            from app.ui.animations import stagger_in
            stagger_in(made)
        finally:
            session.close()
