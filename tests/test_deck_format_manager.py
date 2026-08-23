"""Regression coverage for the UI-only input deck format manager prototype."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def manager():
    """Create one offscreen deck format manager and clean it up after each test."""
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets")
    from opencae.ui.deck_format_manager import DeckFormatManagerDialog

    application = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    dialog = DeckFormatManagerDialog()
    application.processEvents()
    yield dialog
    dialog.close()
    application.processEvents()


def test_primary_format_groups_are_not_wrapped_in_resources(manager):
    """Materials, sections and coordinate systems stay first-class tree groups."""
    labels = manager.navigation.top_level_labels()
    assert "Resources" not in labels
    assert "Materials" in labels
    assert "Sections" in labels
    assert "Profiles" in labels
    assert "Coordinate Systems" in labels
    assert manager.navigation.tree.columnCount() == 1
    assert manager.navigation.tree.isHeaderHidden()


def test_profile_selector_contains_builtins_without_separate_format_selector(manager):
    """FEMaster/Abaqus are immutable profiles in one canonical selector."""
    from opencae.ui.templates import PRIMARY_CONTROL_HEIGHT

    toolbar = manager.profile_toolbar
    assert not hasattr(toolbar, "format_combo")
    assert [toolbar.profile_combo.itemText(i) for i in range(toolbar.profile_combo.count())] == [
        "FEMaster",
        "Abaqus",
    ]
    assert toolbar.profile_name() == "FEMaster"
    assert toolbar.is_builtin()
    assert not manager.template_page.template.isEnabled()
    assert not manager.navigation.move_up_button.isEnabled()
    assert not toolbar.delete_button.isEnabled()
    assert not toolbar.save_button.isEnabled()
    assert toolbar.copy_button.isEnabled()
    for control in (
        toolbar.profile_combo,
        toolbar.new_button,
        toolbar.copy_button,
        toolbar.delete_button,
        toolbar.save_button,
    ):
        assert control.minimumHeight() == PRIMARY_CONTROL_HEIGHT
        assert control.maximumHeight() == PRIMARY_CONTROL_HEIGHT


def test_copying_builtin_creates_editable_profile(manager):
    """Built-ins can be copied and the resulting profile becomes editable."""
    name = manager.profile_toolbar.copy_profile()
    assert name == "FEMaster Copy"
    assert manager.profile_toolbar.profile_name() == name
    assert manager.profile_toolbar.is_editable()
    assert manager.template_page.template.isEnabled()
    assert manager.profile_toolbar.delete_button.isEnabled()
    assert manager.profile_toolbar.save_button.isEnabled()
    assert manager.apply_button.isEnabled()


def test_move_buttons_reorder_only_user_profile_and_builtin_stays_default(manager):
    """Tree order is changed visually without an order-number column or built-in mutation."""
    manager.profile_toolbar.copy_profile()
    before = manager.navigation.child_labels("materials")
    assert before[:3] == ["Material Header", "Isotropic Elastic", "Density"]

    assert manager.navigation.select_key("materials.isotropic_elastic")
    manager.navigation.move_down()
    assert manager.navigation.child_labels("materials")[:3] == [
        "Material Header",
        "Density",
        "Isotropic Elastic",
    ]

    manager.profile_toolbar.profile_combo.setCurrentText("FEMaster")
    assert manager.navigation.child_labels("materials")[:3] == [
        "Material Header",
        "Isotropic Elastic",
        "Density",
    ]


def test_isotropic_elastic_uses_one_template_and_documents_fields(manager):
    """Keyword options and data lines share one editor with explicit placeholders."""
    assert manager.select_key("materials.isotropic_elastic")
    page = manager.template_page
    assert manager.stack.currentWidget() is page
    assert page.template_text() == "*ELASTIC, TYPE=ISO\n{youngs_modulus}, {poisson_ratio}"
    assert page.available_field_names() == (
        "youngs_modulus",
        "poisson_ratio",
        "material_name",
        "temperature",
    )
    assert "*MATERIAL, NAME=STEEL" in page.preview.toPlainText()
    assert "*ELASTIC, TYPE=ISO" in page.preview.toPlainText()
    assert "210000, 0.3" in page.preview.toPlainText()
    assert not page.is_repeatable()
    assert page.repeat_rows.isHidden()


def test_available_field_can_be_inserted_in_user_profile(manager):
    """The field helper inserts valid placeholders after a built-in is copied."""
    from PyQt6.QtGui import QTextCursor

    manager.profile_toolbar.copy_profile()
    manager.select_key("materials.isotropic_elastic")
    page = manager.template_page
    cursor = page.template.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("\nE=")
    page.template.setTextCursor(cursor)
    page.insert_field("youngs_modulus")
    assert page.template_text().endswith("E={youngs_modulus}")


def test_surface_template_separates_element_side_and_repeats_facets(manager):
    """Surface formatting exposes facet members separately and models repeated rows."""
    manager.select_key("surfaces")
    page = manager.template_page
    assert page.template_text() == "*SURFACE, NAME={surface_name}\n{element_id}, {side_id}"
    assert page.available_field_names() == ("surface_name", "element_id", "side_id")
    assert "surface_entries" not in page.available_field_names()
    assert page.is_repeatable()
    assert page.repeat_rows.isChecked()
    assert not page.repeat_rows.isHidden()
    preview = page.preview.toPlainText()
    assert "*SURFACE, NAME=PRESSURE_FACE" in preview
    assert "42, S1" in preview
    assert "43, S2" in preview
    assert page.fields.topLevelItem(1).text(2) == "Repeated row"
    assert page.fields.topLevelItem(2).text(2) == "Repeated row"


def test_global_format_options_only_appear_under_general_settings(manager):
    """Formatter-wide options do not clutter record-specific template pages."""
    from PyQt6.QtWidgets import QCheckBox

    manager.select_key("general.formatting")
    assert manager.stack.currentWidget() is manager.global_page
    labels = [item.text() for item in manager.global_page.findChildren(QCheckBox)]
    assert "Uppercase generated keywords" in labels
    assert "Insert a blank line between top-level blocks" in labels
    assert all(not item.isEnabled() for item in manager.global_page.findChildren(QCheckBox))
