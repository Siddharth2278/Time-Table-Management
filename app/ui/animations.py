"""Tiny animation helpers — fade-ins, staggered entrances, count-ups.

Everything here is parented to the animated widget so no manual
lifetime management is needed. Animations are short and subtle:
the app should feel alive, never slow.
"""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect


def _alive(widget) -> bool:
    try:
        from shiboken6 import isValid
        return isValid(widget)
    except Exception:
        return True


def fade_in(widget, duration: int = 230, delay: int = 0):
    """Fade a widget in from transparent to opaque. Safe on deleted widgets."""
    if not _alive(widget):
        return None
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(max(60, duration))
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    widget.setProperty("_fade_anim", anim)

    def _finish():
        try:
            if _alive(widget):
                widget.setGraphicsEffect(None)
        except Exception:
            pass

    try:
        anim.finished.connect(_finish)
    except Exception:
        pass

    def _start():
        try:
            if _alive(widget) and _alive(effect):
                anim.start()
            else:
                _finish()
        except Exception:
            pass

    if delay > 0:
        QTimer.singleShot(delay, _start)
    else:
        _start()
    return anim


def stagger_in(widgets, base_delay: int = 30, step: int = 70, duration: int = 230):
    """Fade a row of widgets in one after another."""
    for i, w in enumerate(widgets):
        try:
            if not _alive(w):
                continue
            fade_in(w, duration=duration, delay=base_delay + i * step)
        except Exception:
            continue


def count_up(label, target, duration: int = 650, delay: int = 0):
    """Animate a QLabel's number from 0 up to target."""
    try:
        target = int(target)
    except Exception:
        label.setText(str(target))
        return
    if target <= 0:
        label.setText("0")
        return
    steps = max(1, min(target, 40))
    interval = max(15, duration // steps)
    state = {"i": 0}
    timer = QTimer(label)

    def tick():
        state["i"] += 1
        if state["i"] >= steps:
            label.setText(str(target))
            timer.stop()
        else:
            label.setText(str(round(target * state["i"] / steps)))

    def start():
        if not _alive(label):
            return
        timer.timeout.connect(tick)
        timer.start(interval)

    if delay > 0:
        def _dstart():
            try:
                if _alive(label):
                    start()
            except Exception:
                pass
        QTimer.singleShot(delay, _dstart)
    else:
        start()
