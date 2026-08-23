"""Regression tests for pixel-consistent primary dialog control geometry."""

from PyQt6.QtWidgets import QApplication, QLineEdit, QSpinBox

from opencae.ui.core.theme import stylesheet
from opencae.ui.core.widgets import ChevronComboBox, ReferenceSelector
from opencae.ui.templates import (
    PRIMARY_CONTROL_HEIGHT,
    NumericUnitInput,
    apply_primary_control_height,
    field_block,
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


def test_reference_selector_actions_match_combo_height():
    """Keep inline create/pick buttons aligned with the reference combo."""
    app = QApplication.instance() or QApplication([])
    selector = ReferenceSelector(
        (("Steel", "steel"),),
        "steel",
        create_callback=lambda *_args: None,
        pick_callback=lambda *_args: None,
    )
    selector.show()
    app.processEvents()
    try:
        heights = {
            selector.height(),
            selector.combo.height(),
            selector.add_button.height(),
            selector.pick_button.height(),
        }
        assert heights == {PRIMARY_CONTROL_HEIGHT}
    finally:
        selector.close()
        selector.deleteLater()
        app.processEvents()


def test_combo_popup_requests_every_available_entry():
    """Avoid scrolling short dropdowns when screen space can show all rows."""
    app = QApplication.instance() or QApplication([])
    combo = ChevronComboBox()
    combo.addItems([f"Option {index}" for index in range(18)])
    combo.show()
    app.processEvents()
    try:
        combo.showPopup()
        app.processEvents()
        assert combo.maxVisibleItems() >= combo.count()
        combo.hidePopup()
    finally:
        combo.close()
        combo.deleteLater()
        app.processEvents()


def test_field_block_places_label_above_control():
    """Protect the vertical label hierarchy shared by resource dialogs."""
    app = QApplication.instance() or QApplication([])
    control = apply_primary_control_height(QLineEdit("Value"))
    block = field_block("Name", control)
    layout = block.layout()
    assert layout is not None
    assert layout.itemAt(0).widget().text() == "Name"
    assert layout.itemAt(1).widget() is control
    block.deleteLater()
    app.processEvents()
