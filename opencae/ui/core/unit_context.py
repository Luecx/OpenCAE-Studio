from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from opencae.units import default_systems


_FALLBACK_SYSTEM = default_systems()[0]


def unit_system_for(widget: QWidget | None):
    """Return the active project unit system for a widget."""
    current = widget
    while current is not None:
        context = getattr(current, "context", None)
        if context is not None:
            project = getattr(context.store, "project", None)
            return context.settings.unit_system(getattr(project, "unit_system", ""))
        parent_widget = getattr(current, "parentWidget", None)
        current = parent_widget() if callable(parent_widget) else None
    return _FALLBACK_SYSTEM


def unit_suffix(widget: QWidget | None, quantity: str) -> str:
    symbol = unit_system_for(widget).symbol(quantity)
    return f" {symbol}" if symbol else ""
