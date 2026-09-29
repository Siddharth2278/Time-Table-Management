"""Central SVG icon set (stroke style, 24x24) with tint + size cache.

Icons are monochrome white glyphs; callers tint per theme/usage.
No emoji anywhere.
"""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_S = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
)
_E = "</svg>"

SVG = {
    "dashboard": _S + (
        '<rect x="3" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1.5"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1.5"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'
    ) + _E,
    "calendar": _S + (
        '<rect x="3" y="5" width="18" height="16" rx="2"/>'
        '<path d="M3 10h18"/><path d="M8 3v4M16 3v4"/>'
    ) + _E,
    "users": _S + (
        '<circle cx="9" cy="8" r="3.5"/>'
        '<path d="M3.5 20c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5"/>'
        '<circle cx="17" cy="9" r="2.5"/>'
        '<path d="M16 15.2c2.3.3 3.9 1.9 4.4 4.3"/>'
    ) + _E,
    "book": _S + (
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5Z"/>'
        '<path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>'
    ) + _E,
    "building": _S + (
        '<rect x="5" y="3" width="14" height="18" rx="1"/>'
        '<path d="M9 7h2M13 7h2M9 11h2M13 11h2M10 21v-3h4v3"/>'
    ) + _E,
    "layers": _S + (
        '<path d="M12 3 3 8l9 5 9-5Z"/>'
        '<path d="M3 13l9 5 9-5"/>'
    ) + _E,
    "clock": _S + (
        '<circle cx="12" cy="12" r="8.5"/>'
        '<path d="M12 7v5l3.5 2"/>'
    ) + _E,
    "help": _S + (
        '<circle cx="12" cy="12" r="8.5"/>'
        '<path d="M9.5 9.5a2.5 2.5 0 0 1 4.9.8c0 1.7-2.4 2.2-2.4 3.7"/>'
        '<path d="M12 17.5h.01"/>'
    ) + _E,
    "sliders": _S + (
        '<path d="M4 7h8M18 7h2M4 17h2M12 17h8"/>'
        '<circle cx="15" cy="7" r="2.2"/>'
        '<circle cx="9" cy="17" r="2.2"/>'
    ) + _E,
    "menu": _S + '<path d="M4 7h16M4 12h16M4 17h16"/>' + _E,
    "plus": _S + '<path d="M12 5v14M5 12h14"/>' + _E,
    "pencil": _S + (
        '<path d="M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19Z"/>'
        '<path d="M14.5 6.5l3 3"/>'
    ) + _E,
    "trash": _S + (
        '<path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
        '<path d="M6.5 7l1 13h9l1-13"/>'
        '<path d="M10 11v6M14 11v6"/>'
    ) + _E,
    "download": _S + (
        '<path d="M12 4v11M7 11l5 5 5-5"/>'
        '<path d="M4 20h16"/>'
    ) + _E,
    "alert": _S + (
        '<path d="M12 4 2.5 20h19Z"/>'
        '<path d="M12 10v4M12 17.5h.01"/>'
    ) + _E,
    "arrow-right": _S + '<path d="M4 12h15M13 6l6 6-6 6"/>' + _E,
    "chevron-left": _S + '<path d="M14.5 6 8.5 12l6 6"/>' + _E,
    "search": _S + (
        '<circle cx="11" cy="11" r="6.5"/>'
        '<path d="M16 16l4.5 4.5"/>'
    ) + _E,
    "x": _S + '<path d="M6 6l12 12M18 6L6 18"/>' + _E,
    "check": _S + '<path d="M4.5 12.5l5 5 10-11"/>' + _E,
}

_cache: dict = {}


def _render(name: str, size: int) -> QPixmap:
    data = SVG.get(name, SVG["help"])
    renderer = QSvgRenderer(QByteArray(data.encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return pix


def _tint(pix: QPixmap, color: str) -> QPixmap:
    out = QPixmap(pix)
    painter = QPainter(out)
    try:
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(out.rect(), QColor(color))
    finally:
        painter.end()
    return out


def icon(name: str, color: str = "#F4F7FA", size: int = 18) -> QIcon:
    """Return a tinted QIcon for a white-glyph SVG. Cached per (name,color,size)."""
    key = (name, color, size)
    hit = _cache.get(key)
    if hit is not None:
        return hit
    result = QIcon(_tint(_render(name, size), color))
    _cache[key] = result
    return result


def nav_icon(name: str, off_color: str, on_color: str, size: int = 18) -> QIcon:
    """Two-state icon for checkable nav buttons (Off=inactive, On=active)."""
    key = ("nav", name, off_color, on_color, size)
    hit = _cache.get(key)
    if hit is not None:
        return hit
    base = _render(name, size)
    result = QIcon()
    result.addPixmap(_tint(base, off_color), QIcon.Normal, QIcon.Off)
    result.addPixmap(_tint(base, on_color), QIcon.Normal, QIcon.On)
    result.addPixmap(_tint(base, on_color), QIcon.Selected, QIcon.On)
    result.addPixmap(_tint(base, on_color), QIcon.Selected, QIcon.Off)
    _cache[key] = result
    return result
