from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QScrollArea, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
from app.database import get_session
from app.models import Semester, Subject, TimetableEntry
from app.services.conflict_service import ConflictService

class SemesterCard(QFrame):
    clicked = Signal(int)
    def __init__(self, semester, completion):
        super().__init__()
        self.semester_id = semester.id
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QFrame:hover {
                border: 1px solid #2F5496;
                background: #F8FAFC;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel(semester.name)
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #1E2A3A; border: none;")
        layout.addWidget(title)
        status = QLabel(semester.status or "Active")
        status.setStyleSheet("font-size: 11px; color: #64748B; border: none;")
        layout.addWidget(status)
        # Progress
        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setValue(int(completion["completion_pct"]))
        bar.setFormat(f"{completion['completion_pct']}%")
        bar.setStyleSheet("""
            QProgressBar { border: 1px solid #E2E8F0; border-radius: 8px; background: #F1F5F9; text-align: center; height: 14px; font-size: 10px; }
            QProgressBar::chunk { background: #2F5496; border-radius: 7px; }
        """)
        layout.addWidget(bar)
        detail = QLabel(f"{completion['scheduled']}/{completion['required']} lectures  •  Remaining: {completion['remaining']}")
        detail.setStyleSheet("font-size: 11px; color: #475569; border: none;")
        layout.addWidget(detail)
        hint = QLabel("Click to open timetable →")
        hint.setStyleSheet("font-size: 10px; color: #2F5496; font-weight: 600; border: none;")
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
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        title = QLabel("Semesters Overview")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: var(--text-primary);")
        layout.addWidget(title)
        sub = QLabel("Click a semester to open its timetable. Each semester has one timetable.")
        sub.setStyleSheet("color: #64748B; font-size: 12px;")
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
            for idx, sem in enumerate(sems):
                comp = ConflictService.calculate_timetable_completion(session, sem.id)
                card = SemesterCard(sem, comp)
                card.clicked.connect(self.openTimetable.emit)
                row = idx // 3
                col = idx % 3
                self.cards_layout.addWidget(card, row, col)
        finally:
            session.close()
