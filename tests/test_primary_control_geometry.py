"""Regression tests for pixel-consistent primary dialog control geometry."""

from PyQt6.QtWidgets import QApplication, QLineEdit, QSpinBox

from opencae.ui.core.file_path import FilePathEditor
from opencae.ui.core.theme import stylesheet
from opencae.ui.core.widgets import (
    ChevronComboBox,
    CompactRegionSelector,
    ComponentsWidget,
    ReferenceSelector,
)
from opencae.ui.templates import (
    COMBO_POPUP_EXTRA_HEIGHT,
    COMBO_POPUP_ROW_HEIGHT,
    INLINE_ACTION_SIZE,
    PRIMARY_CONTROL_HEIGHT,
    CheckGrid,
    CheckList,
    FieldLabel,
    NumericUnitInput,
    ReadOnlyValue,
    SectionHeading,
    VerticalSeparator,
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
    readonly = ReadOnlyValue("210000", "MPa")

    widgets = (line, combo, integer, numeric, readonly)
    for widget in widgets:
        widget.show()
    app.processEvents()

    try:
        assert {widget.height() for widget in widgets} == {PRIMARY_CONTROL_HEIGHT}
        assert numeric.editor.height() == PRIMARY_CONTROL_HEIGHT
        assert numeric.unit_label is not None
        assert numeric.unit_label.height() == PRIMARY_CONTROL_HEIGHT
        assert readonly.value_label.height() == PRIMARY_CONTROL_HEIGHT
        assert readonly.unit_label is not None
        assert readonly.unit_label.height() == PRIMARY_CONTROL_HEIGHT
    finally:
        for widget in widgets:
            widget.close()
            widget.deleteLater()
        app.setStyleSheet(previous_stylesheet)
        app.processEvents()


def test_reference_selector_actions_match_primary_control_height():
    """Keep reference combo and inline create/pick actions exactly aligned."""
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
        assert INLINE_ACTION_SIZE == PRIMARY_CONTROL_HEIGHT
        assert selector.height() == PRIMARY_CONTROL_HEIGHT
        assert selector.combo.height() == PRIMARY_CONTROL_HEIGHT
        assert selector.add_button.height() == PRIMARY_CONTROL_HEIGHT
        assert selector.add_button.width() == PRIMARY_CONTROL_HEIGHT
        assert selector.pick_button.height() == PRIMARY_CONTROL_HEIGHT
        assert selector.pick_button.width() == PRIMARY_CONTROL_HEIGHT
    finally:
        selector.close()
        selector.deleteLater()
        app.processEvents()


def test_compact_region_selector_uses_same_height_actions():
    """Keep viewport/detail actions aligned with the region summary field."""
    app = QApplication.instance() or QApplication([])
    selector = CompactRegionSelector(object())
    selector.show()
    app.processEvents()
    try:
        assert selector.summary.height() == PRIMARY_CONTROL_HEIGHT
        assert selector.pick_button.size().width() == PRIMARY_CONTROL_HEIGHT
        assert selector.pick_button.size().height() == PRIMARY_CONTROL_HEIGHT
        assert selector.extended_button.size().width() == PRIMARY_CONTROL_HEIGHT
        assert selector.extended_button.size().height() == PRIMARY_CONTROL_HEIGHT
    finally:
        selector.close()
        selector.deleteLater()
        app.processEvents()


def test_file_path_editor_uses_primary_geometry_for_both_cells():
    """Keep the browse action exactly aligned with the editable path field."""
    app = QApplication.instance() or QApplication([])
    editor = FilePathEditor("model.dat")
    editor.show()
    app.processEvents()
    try:
        assert editor.edit.height() == PRIMARY_CONTROL_HEIGHT
        assert editor.button.height() == PRIMARY_CONTROL_HEIGHT
        assert editor.button.width() == PRIMARY_CONTROL_HEIGHT
    finally:
        editor.close()
        editor.deleteLater()
        app.processEvents()


def test_component_widget_uses_segmented_units_and_three_columns():
    """Keep vector components separated and labelled with their physical units."""
    app = QApplication.instance() or QApplication([])
    components = ComponentsWidget(
        ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz"),
        (1.0, 2.0, 3.0, None, None, None),
        checkable=True,
        suffixes=("mm", "mm", "mm", "rad", "rad", "rad"),
    )
    components.show()
    app.processEvents()
    try:
        assert len(components._fields) == 6
        assert components.layout().horizontalSpacing() == 3
        assert components._fields[0].editor.height() == PRIMARY_CONTROL_HEIGHT
        assert components._fields[0].editor.unit_label.text() == "mm"
        assert components._fields[3].editor.unit_label.text() == "rad"
        assert components.values()[:3] == [1.0, 2.0, 3.0]
        assert components.values()[3:] == [None, None, None]
    finally:
        components.close()
        components.deleteLater()
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


def test_field_block_places_canonical_label_above_control_and_can_relabel():
    """Protect the shared vertical hierarchy used by dynamic constraint fields."""
    app = QApplication.instance() or QApplication([])
    control = apply_primary_control_height(QLineEdit("Value"))
    block = field_block("Name", control)
    layout = block.layout()
    assert layout is not None
    assert isinstance(layout.itemAt(0).widget(), FieldLabel)
    assert layout.itemAt(0).widget().text() == "Name"
    assert layout.itemAt(1).widget() is control
    block.set_label("Control point")
    assert block.label.text() == "Control point"
    block.deleteLater()
    app.processEvents()


def test_check_templates_preserve_declared_values():
    """Keep finite checkbox groups and checked entity lists independent of dialogs."""
    app = QApplication.instance() or QApplication([])
    grid = CheckGrid(("U1", "U2", "U3"), (True, False, True))
    listing = CheckList((("A", "a"), ("B", "b")), ("b",))
    assert grid.values() == (True, False, True)
    assert listing.selected_values() == ["b"]
    grid.deleteLater()
    listing.deleteLater()
    app.processEvents()


def test_editor_presentation_components_have_semantic_object_names():
    """Keep reusable headings and separators independent of individual dialogs."""
    heading = SectionHeading("Profile Properties")
    separator = VerticalSeparator()
    assert heading.objectName() == "EditorSectionHeading"
    assert separator.objectName() == "EditorVerticalSeparator"
    heading.deleteLater()
    separator.deleteLater()
