"""Apply process-wide visual preferences that belong to QApplication itself."""

from __future__ import annotations

import re

from PyQt6.QtGui import QFont


_FONT_SIZE_RE = re.compile(
    r"(?P<prefix>\bfont-size\s*:\s*)(?P<value>\d+(?:\.\d+)?)(?P<unit>pt|px)\b",
    re.IGNORECASE,
)


def _scaled_stylesheet(stylesheet: str, scale: int) -> str:
    """Scale explicit QSS font sizes without compounding repeated live applies."""
    factor = max(80, min(140, int(scale))) / 100.0
    if not stylesheet or abs(factor - 1.0) <= 1.0e-12:
        return str(stylesheet or "")

    def replace(match: re.Match) -> str:
        value = float(match.group("value")) * factor
        rendered = f"{value:.3f}".rstrip("0").rstrip(".")
        return f"{match.group('prefix')}{rendered}{match.group('unit')}"

    return _FONT_SIZE_RE.sub(replace, str(stylesheet))


def _apply_widget_stylesheet_scale(application, scale: int) -> None:
    """Scale local widget QSS declarations from stable, unscaled baselines."""
    for widget in tuple(application.allWidgets()):
        current = str(widget.styleSheet() or "")
        if not current and not hasattr(widget, "_opencae_base_stylesheet"):
            continue
        last_scaled = getattr(widget, "_opencae_scaled_stylesheet", None)
        if current != last_scaled:
            widget._opencae_base_stylesheet = current
        base = str(getattr(widget, "_opencae_base_stylesheet", current) or "")
        scaled = _scaled_stylesheet(base, scale)
        widget._opencae_scaled_stylesheet = scaled
        if current != scaled:
            widget.setStyleSheet(scaled)


def apply_application_preferences(application, settings) -> None:
    """Apply font scaling from stable unscaled font and stylesheet baselines."""
    base = getattr(application, "_opencae_base_font", None)
    if base is None:
        base = QFont(application.font())
        application._opencae_base_font = QFont(base)

    scale = max(80, min(140, int(settings.preference("appearance/font_scale", 100))))
    font = QFont(base)
    if base.pointSizeF() > 0:
        font.setPointSizeF(base.pointSizeF() * scale / 100.0)
    elif base.pixelSize() > 0:
        font.setPixelSize(max(1, round(base.pixelSize() * scale / 100.0)))
    application.setFont(font)

    # A large part of OpenCAE deliberately uses explicit font-size declarations
    # for visual hierarchy. QApplication.setFont() cannot override those QSS
    # declarations, so scale the active theme stylesheet from an unscaled copy as
    # well. Remember the last generated stylesheet so changing the percentage
    # never compounds an already-scaled value.
    current_stylesheet = str(application.styleSheet() or "")
    last_scaled = getattr(application, "_opencae_scaled_stylesheet", None)
    if current_stylesheet != last_scaled:
        application._opencae_base_stylesheet = current_stylesheet
    base_stylesheet = str(
        getattr(application, "_opencae_base_stylesheet", current_stylesheet) or ""
    )
    scaled_stylesheet = _scaled_stylesheet(base_stylesheet, scale)
    application._opencae_font_scale = scale
    application._opencae_scaled_stylesheet = scaled_stylesheet
    if current_stylesheet != scaled_stylesheet:
        application.setStyleSheet(scaled_stylesheet)

    # Local widget styles (viewport overlays, ribbon labels, compact headings,
    # etc.) can also contain explicit point/pixel sizes. Scale those from their
    # own stable baselines so the preference is genuinely application-wide.
    _apply_widget_stylesheet_scale(application, scale)
