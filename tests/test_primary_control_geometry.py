"""Regression tests for pixel-consistent primary dialog control geometry."""

from PyQt6.QtWidgets import QApplication, QLineEdit, QSpinBox

from opencae.ui.core.theme import stylesheet
from opencae.ui.core.widgets import ChevronComboBox, ReferenceSelector
from opencae.ui.templates import (
    COMBO_POPUP_EXTRA_HEIGHT,
    COMBO_POPUP_ROW_HEIGHT,
    INLINE_ACTION_SIZE,
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


def test_reference_selector_uses_near_primary_sized_actions():
    """Keep create/pick actions substantial while visually secondary to fields."""
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
        assert selector.height() == PRIMARY_CONTROL_HEIGHT
        assert selector.combo.height() == PRIMARY_CONTROL_HEIGHT
        assert INLINE_ACTION_SIZE == 36
        assert selector.add_button.height() == INLINE_ACTION_SIZE
        assert selector.add_button.width() == INLINE_ACTION_SIZE
        assert selector.pick_button.height() == INLINE_ACTION_SIZE
        assert selector.pick_button.width() == INLINE_ACTION_SIZE
    finally:
        selector.close()
        selector.deleteLater()
        app.processEvents()


def test_combo_popup_uses_tall_rows_and_bottom_reserve():
    """Keep popup rows readable and preserve room below the final item border."""
    app = QApplication.instance() or QApplication([])
    previous_stylesheet = app.styleSheet()
    app.setStyleSheet(stylesheet())
    combo = ChevronComboBox()
    combo.addItems([f"Option {index}" for index in range(6)])
    combo.show()
    app.processEvents()
    try:
        combo.showPopup()
        app.processEvents()
        row_height = combo.view().sizeHintForRow(0)
        assert max(COMBO_POPUP_ROW_HEIGHT, row_height) >= 36
        minimum_complete_height = (
            combo.count() * COMBO_POPUP_ROW_HEIGHT + COMBO_POPUP_EXTRA_HEIGHT
        )
        assert combo.view().height() >= minimum_complete_height
        assert combo.maxVisibleItems() >= combo.count()
        combo.hidePopup()
    finally:
        combo.close()
        combo.deleteLater()
        app.setStyleSheet(previous_stylesheet)
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
