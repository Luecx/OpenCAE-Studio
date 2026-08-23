from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QHBoxLayout, QLayout, QVBoxLayout, QWidget


DIALOG_MARGINS = (18, 16, 18, 14)
DIALOG_SPACING = 12
FORM_HORIZONTAL_SPACING = 18
FORM_VERTICAL_SPACING = 10
CONTROL_GROUP_SPACING = 6


def form_layout(parent: QWidget | None = None) -> QFormLayout:
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
    while layout.count():
        item = layout.takeAt(0)
        child = item.widget()
        nested = item.layout()
        if child is not None:
            child.deleteLater()
        elif nested is not None:
            clear_layout(nested)
