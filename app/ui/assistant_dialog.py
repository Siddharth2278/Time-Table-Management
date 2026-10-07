"""AI Assistant dialog: typed chat + optional push-to-talk voice.

Every control is wired to real functionality: typed messages and (when a
local engine is installed) microphone input share the same intent -> strict
tool -> existing service pipeline. Voice-only engines are lazy/optional;
the dialog never requires them.
"""
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout,
)

from app.services.assistant.service import AssistantService
from app.services.local_agent.schemas import LearningError as AgentError
from app.ui.base_dialog import BaseDialog
from app.ui.modals import error as modal_error
from app.ui.widgets import show_toast


class _ChatWorker(QThread):
    done_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, service: AssistantService, text: str):
        super().__init__()
        self._service = service
        self._text = text

    def run(self):
        try:
            self.done_ok.emit(self._service.handle_text(self._text))
        except Exception as e:
            self.failed.emit(str(e) if isinstance(e, AgentError)
                             else "Assistant failed; nothing was changed.")


class _ListenWorker(QThread):
    done_ok = Signal(str)
    failed = Signal(str)

    def run(self):
        try:
            from app.services.assistant import voice_io
            self.done_ok.emit(voice_io.transcribe_once())
        except Exception as e:
            self.failed.emit(str(e) if isinstance(e, AgentError)
                             else "Voice input failed.")


class AssistantDialog(BaseDialog):
    """Professional assistant UI: history, mic/type/stop, indicators."""

    def __init__(self, parent, context=None):
        super().__init__(parent, "AI Assistant", min_width=640)
        self.setMinimumHeight(520)
        self._service = AssistantService(context=context or {})
        self._worker = None
        self._listening = None
        self._speak_back = False

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setMinimumHeight(280)
        self.body_layout.addWidget(self.history)

        self.status = QLabel("AI: Hello. What would you like to do?")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.body_layout.addWidget(self.status)

        row = QHBoxLayout()
        self.mic_btn = QPushButton("Microphone")
        self.mic_btn.setObjectName("SecondaryButton")
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setToolTip("Push-to-talk (needs an optional local "
                                "speech engine; typed chat always works).")
        self.mic_btn.clicked.connect(self._toggle_listen)
        row.addWidget(self.mic_btn)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message…")
        self.input.returnPressed.connect(self._send_typed)
        row.addWidget(self.input, 1)
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send_typed)
        row.addWidget(self.send_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("SecondaryButton")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.stop_btn)
        self.body_layout.addLayout(row)

        speak_row = QHBoxLayout()
        self.speak_btn = QPushButton("Response playback: off")
        self.speak_btn.setObjectName("SecondaryButton")
        self.speak_btn.setCursor(Qt.PointingHandCursor)
        self.speak_btn.clicked.connect(self._toggle_speak)
        speak_row.addWidget(self.speak_btn)
        speak_row.addStretch()
        self.body_layout.addLayout(speak_row)
        self._append("AI", "Hello. What would you like to do?")

    # ---- input ------------------------------------------------------
    def _send_typed(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append("You", text)
        self._ask(text)

    def _toggle_listen(self):
        try:
            if self._listening is not None and self._listening.isRunning():
                return
        except Exception:
            pass
        self.status.setText("Listening…")
        self.mic_btn.setEnabled(False)
        self._listening = _ListenWorker()
        self._listening.done_ok.connect(self._on_heard)
        self._listening.failed.connect(self._on_listen_failed)
        self._listening.start()

    def _on_heard(self, text: str):
        self.mic_btn.setEnabled(True)
        self.status.setText("Processing…")
        if not text.strip():
            self._append("AI", "I could not hear anything. Please try again.")
            return
        self._append("You", text)
        self._ask(text)

    def _on_listen_failed(self, message: str):
        self.mic_btn.setEnabled(True)
        self.status.setText("Ready.")
        modal_error(self, "Voice Input", message)

    def _ask(self, text: str):
        self.status.setText("Processing…")
        self.send_btn.setEnabled(False)
        self._worker = _ChatWorker(self._service, text)
        self._worker.done_ok.connect(self._on_answer)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_answer(self, out: dict):
        self.send_btn.setEnabled(True)
        reply = str(out.get("reply", ""))
        self._append("AI", reply)
        self.status.setText("Speaking…" if self._speak_back else "Ready.")
        if self._speak_back and reply:
            try:
                from app.services.assistant import voice_io
                voice_io.speak(reply, enabled=True)
            except Exception:
                pass
            self.status.setText("Ready.")

    def _on_failed(self, message: str):
        self.send_btn.setEnabled(True)
        self.status.setText("Ready.")
        modal_error(self, "Assistant Failed",
                    f"{message}\n\nNothing was changed.")

    def _stop(self):
        for worker in (self._worker, self._listening):
            try:
                if worker is not None and worker.isRunning():
                    worker.wait(500)
            except Exception:
                pass
        self.send_btn.setEnabled(True)
        self.mic_btn.setEnabled(True)
        self.status.setText("Ready.")
        show_toast(self, "Stopped.")

    def _toggle_speak(self):
        self._speak_back = not self._speak_back
        self.speak_btn.setText(
            f"Response playback: {'on' if self._speak_back else 'off'}")

    def _append(self, who: str, text: str):
        try:
            self.history.append(f"{who}: {text}")
        except Exception:
            pass


def open_assistant_dialog(parent, context=None):
    dialog = AssistantDialog(parent, context=context)
    dialog.exec()
