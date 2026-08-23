"""Provides shared layout geometry for OpenCAE dialogs and control groups."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QHBoxLayout, QLayout, QVBoxLayout, QWidget


# Material, Section and Profile established the canonical editor geometry. Keep
# every later dialog on the same outer rhythm instead of carrying two systems.
DIALOG_MARGINS = (24, 20, 24, 18)
DIALOG_SPACING = 16
FORM_HORIZONTAL_SPACING = 18
FORM_VERTICAL_SPACING = 12
CONTROL_GROUP_SPACING = 6


def form_layout(parent: QWidget | None = None) -> QFormLayout:
    """Return the legacy left-label form layout for specialized compatibility paths.

    New create/edit dialogs should prefer FieldStack/field_block. This helper
    remains for table/matrix-oriented editors that have not yet been expressed
    as semantic field blocks.
    """
    form = QFormLayout(parent) if parent is not None else QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setHorizontalSpacing(FORM_HORIZONTAL_SPACING)
    form.setVerticalSpacing(FORM_VERTICAL_SPACING)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
    return form


def dialog_layout(parent: QWidget) -> QVBoxLayout:
    """Return the canonical root layout used by editor dialogs."""
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(*DIALOG_MARGINS)
    layout.setSpacing(DIALOG_SPACING)
    return layout


def horizontal_group(
    *widgets: QWidget,
    spacing: int = CONTROL_GROUP_SPACING,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    stretch: bool = False,
) -> QWidget:
    """Return a compact horizontal group of peer widgets."""
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    if stretch:
        layout.addStretch(1)
    return host


def vertical_group(
    *widgets: QWidget,
    spacing: int = CONTROL_GROUP_SPACING,
    margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    stretch: bool = False,
) -> QWidget:
    """Return a compact vertical group of peer widgets."""
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    if stretch:
        layout.addStretch(1)
    return host


def clear_layout(layout: QLayout) -> None:
    """Delete every widget/layout item currently owned by a layout."""
    while layout.count():
        item = layout.takeAt(0)
        child = item.widget()
        nested = item.layout()
        if child is not None:
            child.deleteLater()
        elif nested is not None:
            clear_layout(nested)
