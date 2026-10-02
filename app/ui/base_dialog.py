"""Reusable dialog shell: title bar, scrollable body, FIXED footer.

Structure:
    BaseDialog
     ├── scroll area (body grows, scrolls when tall)
     └── footer (Cancel + OK, always visible, never inside the scroll)

Subclasses add their form to self.body_layout and keep all of their
existing validation/data logic. Footer behavior is identical everywhere:
OK is primary + default (Enter), Cancel is secondary (Escape), Cancel
never touches the database.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QScrollArea, QPushButton, QVBoxLayout, QWidget,
)

_FOOTER_QSS = "QWidget#DialogFooter { border: none; background: transparent; }"


class BaseDialog(QDialog):
    def __init__(self, parent=None, title="", min_width=440):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(min_width)
        self._fitted = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("DialogScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(20, 16, 20, 16)
        self.body_layout.setSpacing(10)
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)

        footer = QWidget()
        footer.setObjectName("DialogFooter")
        footer.setStyleSheet(_FOOTER_QSS)
        self.footer = footer
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 16)
        footer_layout.setSpacing(8)
        footer_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("SecondaryButton")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        # Cancel must never steal the default (Enter is always OK).
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        footer_layout.addWidget(self.cancel_button)
        self.ok_button = QPushButton("OK")
        self.ok_button.setObjectName("PrimaryButton")
        self.ok_button.setCursor(Qt.PointingHandCursor)
        self.ok_button.setDefault(True)
        self.ok_button.setAutoDefault(True)
        self.ok_button.clicked.connect(self.accept)
        footer_layout.addWidget(self.ok_button)
        root.addWidget(footer)

    def showEvent(self, event):
        # Fit height to content once (bounded), so no dead empty area sits
        # between body and footer; taller content scrolls instead.
        super().showEvent(event)
        if not self._fitted:
            self._fitted = True
            try:
                hint = self.sizeHint()
                self.resize(max(self.width(), hint.width()),
                            min(max(hint.height(), 240), 720))
            except Exception:
                pass
        # Re-assert deferred: showing a dialog with a scroll area clears the
        # default-button flag after showEvent (focus settling), so without
        # this Enter would do nothing. Verified to stick once deferred.
        try:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._assert_default)
        except Exception:
            pass

    def _assert_default(self):
        try:
            self.ok_button.setDefault(True)
        except Exception:
            pass
