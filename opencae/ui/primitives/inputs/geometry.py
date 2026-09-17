"""Shared geometry policy for primary editor controls."""

from PyQt6.QtWidgets import QSizePolicy, QWidget

from opencae.ui.foundation.metrics import PRIMARY_CONTROL_HEIGHT


def apply_primary_input_geometry(widget: QWidget) -> QWidget:
    """Apply the canonical 40 px primary-control contract."""
    widget.setProperty("primaryControl", True)
    widget.setMinimumHeight(PRIMARY_CONTROL_HEIGHT)
    widget.setMaximumHeight(PRIMARY_CONTROL_HEIGHT)
    policy = widget.sizePolicy()
    policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
    widget.setSizePolicy(policy)
    widget.updateGeometry()
    return widget
