"""Apply process-wide visual preferences that belong to QApplication itself."""

from __future__ import annotations

from PyQt6.QtGui import QFont


def apply_application_preferences(application, settings) -> None:
    """Apply font scaling from a stable unscaled base font without compounding."""
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
