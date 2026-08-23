"""Regression tests for pixel-consistent primary dialog control geometry."""

from PyQt6.QtWidgets import QApplication, QLineEdit, QSpinBox

from opencae.ui.core.theme import stylesheet
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    PRIMARY_CONTROL_HEIGHT,
    NumericUnitInput,
    apply_primary_control_height,
)


def test_primary_dialog_controls_share_exact_height():
    """Keep text, combo, integer and segmented numeric fields interchangeable."""
    app = QApplication.instance() or QApplication([])
    previous_stylesheet = app.styleSheet()
    app.setStyleSheet(stylesheet())

    line = apply_primary_control_height(QLineEdit("Name"))
    combo = apply_primary_control_height(ChevronComboBox())
    combo.addItem("Option")
    integer = apply_primary_control_height(QSpinBox())
    numeric = NumericUnitInput(210000.0, "MPa")

    widgets = (line, combo, integer, numeric)
    for widget in widgets:
        widget.show()
    app.processEvents()

    try:
        assert {widget.height() for widget in widgets} == {PRIMARY_CONTROL_HEIGHT}
        assert numeric.editor.height() == PRIMARY_CONTROL_HEIGHT
        assert numeric.unit_label is not None
        assert numeric.unit_label.height() == PRIMARY_CONTROL_HEIGHT
    finally:
        for widget in widgets:
            widget.close()
            widget.deleteLater()
        app.setStyleSheet(previous_stylesheet)
        app.processEvents()
