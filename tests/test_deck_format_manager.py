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


def test_profile_selector_contains_read_only_builtins(manager):
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


def test_move_buttons_reorder_only_user_profile(manager):
    """Tree order changes without an order-number column and stays profile-local."""
    manager.profile_toolbar.copy_profile()
    assert manager.navigation.child_labels("materials")[:3] == [
        "Material Header",
        "Isotropic Elastic",
        "Density",
    ]
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


def test_femaster_elements_only_show_requested_concrete_types(manager):
    """The editor omits MITC/FRT/QSPT variants and keeps reduced solid variants."""
    from opencae.ui.deck_format_manager.element_type_catalog import ELEMENT_TYPES

    expected_codes = (
        "T3",
        "B33",
        "S3",
        "S4",
        "S6",
        "S8",
        "C3D4",
        "C3D5",
        "C3D6",
        "C3D8",
        "C3D8R",
        "C3D10",
        "C3D13",
        "C3D15",
        "C3D20",
        "C3D20R",
    )
    assert tuple(item.code for item in ELEMENT_TYPES) == expected_codes
    labels = manager.navigation.child_labels("mesh.elements")
    assert labels == [item.label for item in ELEMENT_TYPES]
    assert all("MITC" not in label and "FRT" not in label for label in labels)
    assert all("QSPT" not in label for label in labels)


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
    preview = page.preview.toPlainText()
    assert "*ELEMENT, TYPE=C3D4" in preview
    assert "42, 101, 102, 103, 104" in preview
    assert "43, 201, 202, 203, 204" in preview


def test_literal_element_codes_include_reduced_variants(manager):
    """Representative records own their literal FEMaster type codes."""
    for key, code in (
        ("mesh.elements.t3", "T3"),
        ("mesh.elements.s8", "S8"),
        ("mesh.elements.c3d8r", "C3D8R"),
        ("mesh.elements.c3d20r", "C3D20R"),
    ):
        assert manager.select_key(key)
        first_line = manager.template_page.template_text().splitlines()[0]
        assert first_line == f"*ELEMENT, TYPE={code}"


def test_profiles_cover_open_cae_types_and_femaster_properties(manager):
    """Every profile uses FEMaster's generic PROFILE property row."""
    assert manager.navigation.child_labels("profiles") == [
        "Rectangle",
        "Box",
        "Pipe",
        "Circle",
        "I-Profile",
        "H-Profile",
        "C-Profile",
        "U-Profile",
        "General Profile",
        "Graph Profile",
    ]
    assert manager.select_key("profiles.circle")
    page = manager.template_page
    assert page.template_text().startswith("*PROFILE, NAME={profile_name}\n")
    assert page.available_field_names() == (
        "profile_name",
        "area",
        "iyy",
        "izz",
        "torsion_constant",
        "iyz",
        "centroid_y",
        "centroid_z",
    )
    preview = page.preview.toPlainText()
    assert "*PROFILE, NAME=PROFILE-1" in preview
    assert "800" in preview


def test_field_record_exposes_tabular_field_values(manager):
    """FIELD records document and preview the actual tabular data rows."""
    assert manager.select_key("fields")
    page = manager.template_page
    assert "{for row in rows}" in page.template_text()
    assert page.available_field_names() == (
        "field_name",
        "location",
        "components",
        "fill_value",
        "row.entity_id",
        "row.values",
    )
    preview = page.preview.toPlainText()
    assert "*FIELD, NAME=TEMPERATURE, TYPE=NODE, COLS=2, FILL=NAN" in preview
    assert "101, 2.5, 3.5" in preview
    assert "102, 4.5, 5.5" in preview


def test_coordinate_systems_have_rectangular_and_cylindrical_records(manager):
    """FEMaster coordinate-system kinds are explicit leaves with all vector fields."""
    assert manager.navigation.child_labels("coordinate_systems") == [
        "Rectangular",
        "Cylindrical",
    ]
    expected_fields = (
        "name",
        "origin_x",
        "origin_y",
        "origin_z",
        "axis_1_x",
        "axis_1_y",
        "axis_1_z",
        "axis_2_x",
        "axis_2_y",
        "axis_2_z",
    )
    for key, kind in (
        ("coordinate_systems.rectangular", "RECTANGULAR"),
        ("coordinate_systems.cylindrical", "CYLINDRICAL"),
    ):
        assert manager.select_key(key)
        page = manager.template_page
        assert page.template_text().splitlines()[0] == (
            f"*ORIENTATION, NAME={{name}}, TYPE={kind}"
        )
        assert page.available_field_names() == expected_fields


def test_femaster_constraints_omit_mpc_and_equation_exposes_terms(manager):
    """FEMaster omits MPC while Equation documents target/DOF/coefficient terms."""
    labels = manager.navigation.child_labels("constraints")
    assert "MPC" not in labels
    assert "Equation" in labels
    assert manager.select_key("constraints.equation")
    page = manager.template_page
    assert page.template_text() == (
        "*EQUATION, NAME={equation_name}\n"
        "{for term in terms}\n"
        "{term.target}, {term.dof}, {term.coefficient}\n"
        "{endfor}"
    )
    assert page.available_field_names() == (
        "equation_name",
        "term.target",
        "term.dof",
        "term.coefficient",
    )
    assert "NODE_A, 1, 1" in page.preview.toPlainText()
    assert "NODE_B, 1, -1" in page.preview.toPlainText()


def test_equation_domain_has_explicit_terms():
    """Equation constraints expose typed term entries outside the formatter UI too."""
    from opencae.model.entities.constraints import EquationConstraint, EquationTerm

    equation = EquationConstraint(terms=[EquationTerm(dof=2, coefficient=-3.5)])
    assert len(equation.terms) == 1
    assert equation.terms[0].dof == 2
    assert equation.terms[0].coefficient == -3.5
    with pytest.raises(ValueError):
        EquationTerm(dof=7)


def test_float_format_changes_preview_and_available_examples(manager):
    """The selected float format is applied rather than being a visual-only control."""
    manager.profile_toolbar.copy_profile()
    assert manager.select_key("materials.isotropic_elastic")
    page = manager.template_page
    page.float_format.setCurrentText(".12e")
    preview = page.preview.toPlainText()
    assert "2.100000000000e+05, 3.000000000000e-01" in preview
    assert page.fields.topLevelItem(0).text(3) == "2.100000000000e+05"
    assert page.fields.topLevelItem(1).text(3) == "3.000000000000e-01"


def test_template_and_preview_use_line_numbered_monospace_editors(manager):
    """Both deck panes expose a readable code-editor treatment."""
    from PyQt6.QtGui import QFont
    from opencae.ui.deck_format_manager.code_editor import DeckCodeEditor

    page = manager.template_page
    assert isinstance(page.template, DeckCodeEditor)
    assert isinstance(page.preview, DeckCodeEditor)
    assert page.template.line_number_area_width() > 0
    assert page.preview.line_number_area_width() > 0
    assert page.template.font().styleHint() == QFont.StyleHint.Monospace
    assert page.preview.font().styleHint() == QFont.StyleHint.Monospace


def test_isotropic_elastic_uses_one_template_and_documents_fields(manager):
    """Keyword options and data lines share one editor with explicit placeholders."""
    assert manager.select_key("materials.isotropic_elastic")
    page = manager.template_page
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
    preview = page.preview.toPlainText()
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
