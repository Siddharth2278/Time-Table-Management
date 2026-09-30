"""Single modern modal system for the whole desktop app.

Every user-facing popup goes through here — confirmations, information,
warnings and errors share one rounded component with a bottom action area:

    [ Cancel ]    [ OK ]

- Enter = OK (default button), Escape = Cancel (native reject).
- Destructive confirmations style OK as a red Danger button and only
  proceed when OK is pressed; Cancel always dismisses safely.
- Validation logic and message text at call sites are untouched; only
  the presentation is unified (no native QMessageBox look).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)


class AppModal(QDialog):
    """Rounded modal with title, description and a Cancel/OK action row."""

    def __init__(self, parent=None, title="", description="",
                 ok_text="OK", show_cancel=True, destructive=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("ModalTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        if description:
            desc_label = QLabel(str(description))
            desc_label.setObjectName("ModalDesc")
            desc_label.setWordWrap(True)
            desc_label.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            layout.addWidget(desc_label)
        row = QHBoxLayout()
        row.setContentsMargins(0, 6, 0, 0)
        row.setSpacing(8)
        row.addStretch()
        self.cancel_btn = None
        if show_cancel:
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.setObjectName("SecondaryButton")
            self.cancel_btn.setCursor(Qt.PointingHandCursor)
            self.cancel_btn.clicked.connect(self.reject)
            row.addWidget(self.cancel_btn)
        self.ok_btn = QPushButton(ok_text)
        self.ok_btn.setObjectName("DangerButton" if destructive else "PrimaryButton")
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.setDefault(True)
        self.ok_btn.setAutoDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        row.addWidget(self.ok_btn)
        layout.addLayout(row)
        try:
            self.resize(max(self.width(), 420),
                        min(max(self.sizeHint().height(), 180), 560))
        except Exception:
            pass


def ask(parent, title, description, ok_text="OK", destructive=False) -> bool:
    """Cancel/OK confirmation. Returns True ONLY when OK is pressed."""
    return AppModal(parent, title, description,
                    ok_text=ok_text, show_cancel=True,
                    destructive=destructive).exec() == QDialog.Accepted


def info(parent, title, description):
    """Information / success message with a single OK (nothing to decide)."""
    AppModal(parent, title, description, ok_text="OK",
             show_cancel=False, destructive=(kind == "error")).exec()


def warn(parent, title, description):
    """Warning / error message with Cancel + OK (both dismiss safely)."""
    AppModal(parent, title, description, ok_text="OK",
             show_cancel=True, destructive=False).exec()


def error(parent, title, description):
    """Error message with Cancel + OK (both dismiss safely)."""
    AppModal(parent, title, description, ok_text="OK",
             show_cancel=True, destructive=True).exec()
