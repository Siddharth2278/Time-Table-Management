from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QScrollArea, QGridLayout
from PySide6.QtCore import Qt, Signal
from app.database import get_session
from app.models import Semester, Subject
from app.services.conflict_service import ConflictService
from app.ui.widgets import page_header

TONES = ["indigo", "violet", "green", "amber", "red", "indigo"]


class SemesterCard(QFrame):
    clicked = Signal(int)

    def __init__(self, semester, completion, tone="indigo"):
        super().__init__()
        self.semester_id = semester.id
        self.setObjectName("SemCard")
        self.setProperty("tone", tone)
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel(semester.name)
        title.setObjectName("SemTitle")
        layout.addWidget(title)
        status = QLabel(semester.status or "Active")
        status.setObjectName("SemSub")
        layout.addWidget(status)
        bar = QProgressBar()
        bar.setMaximum(100)
        bar.setValue(int(completion["completion_pct"]))
        bar.setFormat(f"{completion['completion_pct']}%")
        layout.addWidget(bar)
        detail = QLabel(f"{completion['scheduled']}/{completion['required']} lectures  •  Remaining: {completion['remaining']}")
        detail.setObjectName("SemDetail")
        layout.addWidget(detail)
        hint = QLabel("Click to open timetable  →")
        hint.setObjectName("SemHint")
        layout.addWidget(hint)
        self.setMinimumHeight(150)
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
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(page_header(
            "Semesters", "Completion progress per semester. Click a card to open its timetable."))

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent; border: none;")
        self.grid = QVBoxLayout(self.container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background: transparent; border: none;")
        self.cards_layout = QGridLayout(self.cards_widget)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.grid.addWidget(self.cards_widget)
        self.grid.addStretch()

    def refresh(self):
        # Clear immediately so old cards never ghost over new ones.
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                try:
                    w.hide()
                    w.setParent(None)
                except Exception:
                    pass
                w.deleteLater()
        session = get_session()
        try:
            sems = session.query(Semester).order_by(Semester.id).all()
            for idx, sem in enumerate(sems):
                comp = ConflictService.calculate_timetable_completion(session, sem.id)
                card = SemesterCard(sem, comp, TONES[idx % len(TONES)])
                card.clicked.connect(self.openTimetable.emit)
                self.cards_layout.addWidget(card, idx // 3, idx % 3)
        finally:
            session.close()
