"""Regression tests for the shared editor-dialog layout architecture."""

from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    PRIMARY_CONTROL_HEIGHT,
    FieldStack,
    Vector3Input,
    scaffold_dialog,
)


ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    """Return one repository source file as UTF-8 text for architecture assertions."""
    return (ROOT / relative).read_text(encoding="utf-8")


def test_dialog_scaffold_uses_label_above_field_stack():
    """Keep generic FormDialog and NamedEntityDialog descendants off QFormLayout."""
    app = QApplication.instance() or QApplication([])
    dialog = QDialog()
    scaffold = scaffold_dialog(dialog, "Example")
    try:
        assert isinstance(scaffold.form, FieldStack)
    finally:
        dialog.deleteLater()
        app.processEvents()


def test_canonical_combo_and_vector_inputs_share_primary_geometry():
    """Keep finite-choice and three-component controls interchangeable in field rows."""
    app = QApplication.instance() or QApplication([])
    combo = ChevronComboBox()
    vector = Vector3Input((1.0, 2.0, 3.0))
    try:
        assert combo.minimumWidth() == 0
        assert combo.minimumHeight() == PRIMARY_CONTROL_HEIGHT
        assert combo.maximumHeight() == PRIMARY_CONTROL_HEIGHT
        assert vector.minimumHeight() == PRIMARY_CONTROL_HEIGHT
        assert vector.maximumHeight() == PRIMARY_CONTROL_HEIGHT
        assert len(vector.editors) == 3
        assert {
            (editor.minimumHeight(), editor.maximumHeight())
            for editor in vector.editors
        } == {(PRIMARY_CONTROL_HEIGHT, PRIMARY_CONTROL_HEIGHT)}
        assert vector.value() == (1.0, 2.0, 3.0)
    finally:
        combo.deleteLater()
        vector.deleteLater()
        app.processEvents()


def test_migrated_editor_sources_do_not_reintroduce_legacy_form_layouts():
    """Protect the final dialog pass from local left-label form regressions."""
    migrated = (
        "opencae/ui/dialogs/material_property.py",
        "opencae/ui/dialogs/optimization_dialogs/topology_controls_dialog.py",
        "opencae/ui/dialogs/optimization_dialogs/topology_filter_dialog.py",
        "opencae/ui/dialogs/optimization_dialogs/topology_optimization_dialog.py",
        "opencae/ui/dialogs/optimization_dialogs/topology_symmetry_dialog.py",
        "opencae/ui/ribbon/result_range.py",
        "opencae/ui/ribbon/result_section.py",
    )
    for relative in migrated:
        source = _source(relative)
        assert "QFormLayout" not in source, relative
        assert "setMinimumWidth(316)" not in source, relative

    material_property = _source("opencae/ui/dialogs/material_property.py")
    assert "QDoubleSpinBox" not in material_property
    assert ".setSuffix(" not in material_property

    result_section = _source("opencae/ui/ribbon/result_section.py")
    assert "_Vector3Editor" not in result_section


def test_central_field_implementations_do_not_restore_fixed_316px_widths():
    """Let dialog layouts determine width instead of forcing the obsolete field constant."""
    fields = _source("opencae/ui/core/fields.py")
    style = _source("opencae/ui/core/styles/fields.py")
    combo = _source("opencae/ui/core/widgets/chevron_combo.py")
    assert "FIELD_WIDTH = 316" not in fields
    assert "min-width: 316px" not in style
    assert "setMinimumWidth(316)" not in combo
