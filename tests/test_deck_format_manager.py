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
    assert [
        toolbar.profile_combo.itemText(i)
        for i in range(toolbar.profile_combo.count())
    ] == ["FEMaster", "Abaqus"]
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


def test_elements_are_concrete_deck_types_without_family_subgroups(manager):
    """Elements list concrete formatter types rather than topology/category folders."""
    from opencae.ui.deck_format_manager.element_type_catalog import ELEMENT_TYPES

    expected_codes = (
        "T3",
        "B33",
        "S3",
        "MITC3FRT",
        "S6",
        "MITC6FRT",
        "S4",
        "MITC4",
        "MITC4FRT",
        "S8",
        "MITC8",
        "MITC8FRT",
        "QSPT",
        "C3D4",
        "C3D10",
        "C3D5",
        "C3D13",
        "C3D6",
        "C3D15",
        "C3D8",
        "C3D8R",
        "C3D20",
        "C3D20R",
    )
    assert tuple(item.code for item in ELEMENT_TYPES) == expected_codes
    labels = manager.navigation.child_labels("mesh.elements")
    assert labels == [item.label for item in ELEMENT_TYPES]
    assert labels[:3] == [
        "Linear Truss — T3",
        "Bernoulli Beam — B33",
        "Linear Triangular Shell — S3",
    ]
    assert "Line Elements" not in labels
    assert "Shell Elements" not in labels
    assert "2D Elements" not in labels
    assert "Solid Elements" not in labels


def test_element_leaf_uses_explicit_for_loop_without_element_type_field(manager):
    """Concrete element records fix the type code and express repetition in syntax."""
    assert manager.select_key("mesh.elements.c3d4")
    page = manager.template_page
    assert page.template_text() == (
        "*ELEMENT, TYPE=C3D4\n"
        "{for element in elements}\n"
        "{element.id}, {element.connectivity}\n"
        "{endfor}"
    )
    assert page.available_field_names() == (
        "element.id",
        "element.connectivity",
    )
    assert "element_type" not in page.available_field_names()
    assert not hasattr(page, "repeat_rows")

    loop_item = page.fields.topLevelItem(0)
    assert loop_item.text(0) == "{for element in elements} … {endfor}"
    assert loop_item.text(2) == "Loop"
    assert loop_item.child(0).text(0) == "{element.id}"
    assert loop_item.child(1).text(0) == "{element.connectivity}"
    assert loop_item.child(0).text(2) == "element in elements"

    preview = page.preview.toPlainText()
    assert "*ELEMENT, TYPE=C3D4" in preview
    assert "42, 101, 102, 103, 104" in preview
    assert "43, 201, 202, 203, 204" in preview
    assert "{for" not in preview
    assert "{endfor}" not in preview


def test_each_element_type_owns_its_literal_keyword_code(manager):
    """Representative concrete element leaves do not rely on a type placeholder."""
    for key, code in (
        ("mesh.elements.t3", "T3"),
        ("mesh.elements.b33", "B33"),
        ("mesh.elements.s3", "S3"),
        ("mesh.elements.c3d20r", "C3D20R"),
    ):
        assert manager.select_key(key)
        first_line = manager.template_page.template_text().splitlines()[0]
        assert first_line == f"*ELEMENT, TYPE={code}"
        assert "{element_type}" not in manager.template_page.template_text()


def test_element_order_is_isolated_per_user_profile(manager):
    """Concrete element records can be reordered and built-in order stays immutable."""
    manager.profile_toolbar.copy_profile()
    parent_key = "mesh.elements"
    assert manager.navigation.child_labels(parent_key)[:3] == [
        "Linear Truss — T3",
        "Bernoulli Beam — B33",
        "Linear Triangular Shell — S3",
    ]
    assert manager.navigation.select_key("mesh.elements.t3")
    manager.navigation.move_down()
    assert manager.navigation.child_labels(parent_key)[:2] == [
        "Bernoulli Beam — B33",
        "Linear Truss — T3",
    ]

    manager.profile_toolbar.profile_combo.setCurrentText("FEMaster")
    assert manager.navigation.child_labels(parent_key)[:2] == [
        "Linear Truss — T3",
        "Bernoulli Beam — B33",
    ]


def test_isotropic_elastic_uses_one_template_and_documents_fields(manager):
    """Keyword options and data lines share one editor with explicit placeholders."""
    assert manager.select_key("materials.isotropic_elastic")
    page = manager.template_page
    assert manager.stack.currentWidget() is page
    assert page.template_text() == (
        "*ELASTIC, TYPE=ISO\n{youngs_modulus}, {poisson_ratio}"
    )
    assert page.available_field_names() == (
        "youngs_modulus",
        "poisson_ratio",
        "material_name",
        "temperature",
    )
    assert "*MATERIAL, NAME=STEEL" in page.preview.toPlainText()
    assert "*ELASTIC, TYPE=ISO" in page.preview.toPlainText()
    assert "210000, 0.3" in page.preview.toPlainText()
    assert not hasattr(page, "repeat_rows")


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


def test_surface_template_uses_explicit_facet_loop(manager):
    """Surface formatting exposes element/side fields inside a visible facet loop."""
    manager.select_key("surfaces")
    page = manager.template_page
    assert page.template_text() == (
        "*SURFACE, NAME={surface_name}\n"
        "{for facet in facets}\n"
        "{facet.element_id}, {facet.side_id}\n"
        "{endfor}"
    )
    assert page.available_field_names() == (
        "surface_name",
        "facet.element_id",
        "facet.side_id",
    )
    assert "surface_entries" not in page.available_field_names()
    assert not hasattr(page, "repeat_rows")

    record_item = page.fields.topLevelItem(0)
    loop_item = page.fields.topLevelItem(1)
    assert record_item.text(0) == "{surface_name}"
    assert loop_item.text(0) == "{for facet in facets} … {endfor}"
    assert loop_item.child(0).text(0) == "{facet.element_id}"
    assert loop_item.child(1).text(0) == "{facet.side_id}"

    preview = page.preview.toPlainText()
    assert "*SURFACE, NAME=PRESSURE_FACE" in preview
    assert "42, S1" in preview
    assert "43, S2" in preview


def test_global_format_options_only_appear_under_general_settings(manager):
    """Formatter-wide options do not clutter record-specific template pages."""
    from PyQt6.QtWidgets import QCheckBox

    manager.select_key("general.formatting")
    assert manager.stack.currentWidget() is manager.global_page
    labels = [item.text() for item in manager.global_page.findChildren(QCheckBox)]
    assert "Uppercase generated keywords" in labels
    assert "Insert a blank line between top-level blocks" in labels
    assert all(
        not item.isEnabled()
        for item in manager.global_page.findChildren(QCheckBox)
    )
