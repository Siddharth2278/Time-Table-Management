"""Tiny animation helpers — fade-ins, staggered entrances, count-ups.

Everything here is parented to the animated widget so no manual
lifetime management is needed. Animations are short and subtle:
the app should feel alive, never slow.
"""
from PySide6.QtCore import QTimer


def _alive(widget) -> bool:
    try:
        from shiboken6 import isValid
        return isValid(widget)
    except Exception:
        return True


def fade_in(widget, duration: int = 230, delay: int = 0):
    """No-op: web parity without Qt opacity effects.

    Web animates the page container with CSS fadeIn. Per-widget
    QGraphicsOpacityEffect on QStackedWidget pages ghost-paints hidden
    pages over the current one (delayed timers re-install effects after
    navigation), so desktop pages render fully opaque instead.
    Kept as a no-op so existing callers are untouched.
    """
    return None


def stagger_in(widgets, base_delay: int = 30, step: int = 70, duration: int = 230):
    """No-op companion to fade_in — pages render fully opaque, never ghost."""
    return None


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
