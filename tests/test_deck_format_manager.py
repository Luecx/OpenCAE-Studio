"""Regression coverage for the Input Deck Format Manager prototype."""

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
    """Primary model families remain first-class groups in the navigation tree."""
    labels = manager.navigation.top_level_labels()
    assert "Resources" not in labels
    for label in (
        "Materials",
        "Sections",
        "Profiles",
        "Coordinate Systems",
        "Loads",
        "Analysis / Loadcases",
    ):
        assert label in labels
    assert manager.navigation.tree.columnCount() == 1
    assert manager.navigation.tree.isHeaderHidden()


def test_profile_selector_contains_read_only_builtins(manager):
    """FEMaster/Abaqus/CalculiX remain immutable profiles in one canonical selector."""
    from opencae.ui.templates import PRIMARY_CONTROL_HEIGHT

    toolbar = manager.profile_toolbar
    assert not hasattr(toolbar, "format_combo")
    assert [
        toolbar.profile_combo.itemText(i)
        for i in range(toolbar.profile_combo.count())
    ] == ["FEMaster", "Abaqus", "CalculiX"]
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
    initial = manager.navigation.child_labels("loads")
    assert initial[:3] == [
        "Amplitude",
        "Concentrated Load / CLOAD",
        "Distributed Traction / DLOAD",
    ]
    assert manager.navigation.select_key("loads.concentrated")
    manager.navigation.move_down()
    assert manager.navigation.child_labels("loads")[:3] == [
        "Amplitude",
        "Distributed Traction / DLOAD",
        "Concentrated Load / CLOAD",
    ]

    manager.profile_toolbar.profile_combo.setCurrentText("FEMaster")
    assert manager.navigation.child_labels("loads") == initial


def test_femaster_element_tree_uses_requested_concrete_types(manager):
    """Element leaves contain the user-facing standard types without FRT/QSPT/C3D13."""
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
        "C3D15",
        "C3D20",
        "C3D20R",
    )
    assert tuple(item.code for item in ELEMENT_TYPES) == expected_codes
    labels = manager.navigation.child_labels("mesh.elements")
    assert labels == [f"{item.label} — {item.code}" for item in ELEMENT_TYPES]
    assert all("MITC" not in label and "FRT" not in label for label in labels)
    assert all("QSPT" not in label for label in labels)


def test_element_leaf_uses_explicit_for_loop_without_element_type_field(manager):
    """Concrete element records fix their type and express repetition in template syntax."""
    assert manager.select_key("mesh.elements.c3d4")
    page = manager.template_page
    assert page.template_text() == (
        "*ELEMENT, TYPE=C3D4, ELSET={element_set}\n"
        "{for element in elements}\n"
        "{element.id}, {element.connectivity}\n"
        "{endfor}"
    )
    assert page.available_field_names() == (
        "element_set",
        "element.id",
        "element.connectivity",
    )
    assert "element_type" not in page.available_field_names()
    assert "42, 101, 102, 103, 104" in page.preview.toPlainText()


def test_profiles_expose_complete_femaster_profile_row(manager):
    """Every OpenCAE profile shape uses all documented FEMaster PROFILE constants."""
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
        "iy",
        "iz",
        "jt",
        "iyz",
        "ey",
        "ez",
        "ref_y",
        "ref_z",
    )
    assert page.preview.toPlainText().splitlines()[1].count(",") == 8


def test_field_variants_expose_actual_address_and_value_rows(manager):
    """FIELD domains document the address columns and the stored component values."""
    assert manager.navigation.child_labels("fields") == [
        "Node Field",
        "Element Field",
        "Element-Nodal Field",
        "Integration-Point Field",
        "Material-Point Field",
        "Shell Normal Field",
    ]
    assert manager.select_key("fields.element_nodal")
    page = manager.template_page
    assert "TYPE=ELEMENT_NODAL" in page.template_text()
    assert page.available_field_names() == (
        "field_name",
        "component_count",
        "fill",
        "row.element",
        "row.local_node",
        "row.values",
    )
    preview = page.preview.toPlainText()
    assert "42, 0, 0.0, 0.0, 1.0" in preview


def test_coordinate_system_variants_follow_femaster_data_semantics(manager):
    """Rectangular has directions only while cylindrical exposes its three points."""
    assert manager.navigation.child_labels("coordinate_systems") == [
        "Rectangular",
        "Cylindrical",
    ]
    assert manager.select_key("coordinate_systems.rectangular")
    rectangular = manager.template_page
    assert "TYPE=RECTANGULAR" in rectangular.template_text()
    assert "base_x" not in rectangular.available_field_names()
    assert "axis_1_x" in rectangular.available_field_names()
    assert "axis_3_z" in rectangular.available_field_names()

    assert manager.select_key("coordinate_systems.cylindrical")
    cylindrical = manager.template_page
    assert "TYPE=CYLINDRICAL" in cylindrical.template_text()
    for field in ("base_x", "radial_x", "theta_x"):
        assert field in cylindrical.available_field_names()


def test_mpc_is_an_ordinary_visible_record_but_disabled_for_femaster(manager):
    """MPC uses the normal editor and Enabled control instead of a support warning page."""
    labels = manager.navigation.child_labels("constraints")
    assert "MPC" in labels
    assert not manager.navigation.is_supported("constraints.mpc")
    assert manager.select_key("constraints.mpc")
    assert manager.stack.currentWidget() is manager.template_page
    assert not manager.template_page.enabled.isChecked()
    assert not manager.template_page.enabled.isEnabled()
    item = manager.navigation.tree.currentItem()
    assert item is not None
    assert item.toolTip(0) == ""
    assert not item.font(0).italic()
    assert "Not Supported" not in manager.breadcrumb.text()

    manager.profile_toolbar.profile_combo.setCurrentText("Abaqus")
    assert manager.navigation.is_supported("constraints.mpc")
    assert manager.stack.currentWidget() is manager.template_page
    assert manager.template_page.enabled.isChecked()
    assert not manager.template_page.enabled.isEnabled()


def test_unsupported_record_stays_forced_off_in_custom_femaster_profile(manager):
    """Copying FEMaster does not make an unsupported solver record enableable."""
    manager.profile_toolbar.copy_profile()
    assert manager.select_key("constraints.mpc")
    page = manager.template_page
    assert not page.enabled.isChecked()
    assert not page.enabled.isEnabled()
    assert not page.template.isEnabled()


def test_enabled_and_float_format_are_profile_local_record_state(manager):
    """Record controls persist when navigating within an editable custom profile."""
    manager.profile_toolbar.copy_profile()
    assert manager.select_key("loads.pressure")
    page = manager.template_page
    assert page.enabled.isChecked()
    page.enabled.setChecked(False)
    page.float_format.setCurrentText(".12e")
    assert page.preview.toPlainText() == "<record disabled>"

    manager.select_key("loads.concentrated")
    manager.select_key("loads.pressure")
    assert not page.enabled.isChecked()
    assert page.float_format.currentText() == ".12e"


def test_equation_uses_term_count_and_individual_term_fields(manager):
    """Equation follows the accepted count-plus-target/DOF/coefficient grammar."""
    assert manager.select_key("constraints.equation")
    page = manager.template_page
    assert page.template_text() == (
        "*EQUATION\n"
        "{term_count}\n"
        "{for term in terms}\n"
        "{term.target}, {term.dof}, {term.coefficient}\n"
        "{endfor}"
    )
    assert page.available_field_names() == (
        "term_count",
        "term.target",
        "term.dof",
        "term.coefficient",
    )
    preview = page.preview.toPlainText()
    assert preview.splitlines()[1] == "2"
    assert "NODE_A, 1, 1" in preview
    assert "NODE_B, 1, -1" in preview


def test_equation_domain_has_explicit_terms():
    """Equation constraints expose typed term entries outside the formatter UI too."""
    from opencae.model.entities.constraints import EquationConstraint, EquationTerm

    equation = EquationConstraint(
        name="Equation-1",
        terms=[EquationTerm(dof=2, coefficient=-3.5)],
    )
    assert len(equation.terms) == 1
    assert equation.terms[0].dof == 2
    assert equation.terms[0].coefficient == -3.5
    with pytest.raises(ValueError):
        EquationTerm(dof=7)


def test_support_records_use_native_six_component_support_syntax(manager):
    """Fixed/displacement/symmetry records expose the native generalized SUPPORT row."""
    for key in (
        "boundary_conditions.fixed",
        "boundary_conditions.displacement",
        "boundary_conditions.symmetry",
    ):
        assert manager.select_key(key)
        page = manager.template_page
        assert page.template_text().startswith(
            "*SUPPORT, SUPPORT_COLLECTOR={support_collector}\n"
        )
        assert "target" in page.available_field_names()
        assert "orientation" in page.available_field_names()
    manager.select_key("boundary_conditions.fixed")
    assert manager.template_page.preview.toPlainText().endswith(
        "FIXED, 0., 0., 0., 0., 0., 0."
    )


def test_load_group_covers_every_native_femaster_load_command(manager):
    """Loads include amplitude plus CLOAD/DLOAD/PLOAD/VLOAD/TLOAD/INERTIALOAD."""
    expected = {
        "loads.amplitude": "*AMPLITUDE",
        "loads.concentrated": "*CLOAD",
        "loads.distributed": "*DLOAD",
        "loads.pressure": "*PLOAD",
        "loads.volume": "*VLOAD",
        "loads.temperature": "*TLOAD",
        "loads.inertia": "*INERTIALOAD",
    }
    for key, keyword in expected.items():
        assert manager.select_key(key)
        assert manager.template_page.template_text().startswith(keyword)

    manager.select_key("loads.concentrated")
    for field in ("fx", "fy", "fz", "mx", "my", "mz", "orientation", "amplitude"):
        assert field in manager.template_page.available_field_names()


def test_coupling_connector_contact_and_rbm_forms_are_explicit(manager):
    """Constraint variants use literal TYPE/slave forms rather than hidden conditions."""
    cases = {
        "constraints.kinematic.node_set": "TYPE=KINEMATIC",
        "constraints.kinematic.surface": "SFSET={surface_set}",
        "constraints.distributing.node_set": "TYPE=STRUCTURAL",
        "constraints.distributing.surface": "SFSET={surface_set}",
        "constraints.connector.hinge": "TYPE=HINGE",
        "constraints.contact": "*CONTACT",
        "constraints.rigid": "*RBM",
    }
    for key, fragment in cases.items():
        assert manager.select_key(key)
        assert fragment in manager.template_page.template_text()


def test_loadcases_cover_all_documented_native_analysis_types(manager):
    """Every FEMaster LOADCASE type has its own concrete hierarchy leaf."""
    expected = {
        "linear_static": "LINEARSTATIC",
        "nonlinear_static": "NONLINEARSTATIC",
        "linear_buckling": "LINEARBUCKLING",
        "topology_static": "LINEARSTATICTOPO",
        "eigenfrequency": "EIGENFREQ",
        "linear_transient": "LINEARTRANSIENT",
        "linear_harmonic": "LINEARHARMONIC",
    }
    for key, loadcase_type in expected.items():
        assert manager.select_key(f"analysis.loadcases.{key}")
        assert manager.template_page.template_text().startswith(
            f"*LOADCASE, TYPE={loadcase_type}"
        )


def test_analysis_controls_include_collectors_frequency_and_diagnostics(manager):
    """Previously missing loadcase child commands are all present in the editor."""
    checks = {
        "analysis.selections.supports": "*SUPPORTS",
        "analysis.selections.loads": "*LOADS",
        "analysis.controls.solver": "*SOLVER",
        "analysis.controls.constraint_method": "*CONSTRAINTMETHOD",
        "analysis.controls.nonlinear": "*NONLINEAR",
        "analysis.controls.time": "*TIME",
        "analysis.controls.newmark": "*NEWMARK",
        "analysis.controls.damping": "*DAMPING",
        "analysis.controls.frequencies": "*FREQUENCIES",
        "analysis.controls.num_eigenvalues": "*NUMEIGENVALUES",
        "analysis.controls.sigma": "*SIGMA",
        "analysis.controls.write_every": "*WRITEEVERY",
        "analysis.controls.initial_velocity": "*INITIALVELOCITY",
        "analysis.controls.inertia_relief": "*INERTIARELIEF",
        "analysis.controls.rebalance_loads": "*REBALANCELOADS",
        "analysis.diagnostics.overview": "*OVERVIEW",
        "analysis.diagnostics.stiffness": "*REQUESTSTIFFNESS",
        "analysis.diagnostics.geometric_stiffness": "*REQUESTSTGEOM",
        "analysis.diagnostics.constraint_summary": "*CONSTRAINTSUMMARY",
        "analysis.end": "*END",
    }
    for key, prefix in checks.items():
        assert manager.select_key(key)
        assert manager.template_page.template_text().startswith(prefix)


def test_shell_abd_exposes_every_documented_matrix_entry(manager):
    """ABD shell formatting exposes all 36 generalized and four shear entries."""
    assert manager.select_key("sections.shell.abd")
    names = manager.template_page.available_field_names()
    stiffness_names = [name for name in names if name.startswith(("k", "s"))]
    assert len(stiffness_names) == 40
    for name in ("k11", "k16", "k61", "k66", "s11", "s12", "s21", "s22"):
        assert name in names
        assert "{" + name + "}" in manager.template_page.template_text()


def test_float_format_changes_preview_and_available_examples(manager):
    """The selected float format affects preview and helper examples."""
    manager.profile_toolbar.copy_profile()
    assert manager.select_key("materials.elastic.isotropic")
    page = manager.template_page
    page.float_format.setCurrentText(".12e")
    preview = page.preview.toPlainText()
    assert "2.100000000000e+05, 3.000000000000e-01" in preview
    assert page.fields.topLevelItem(0).text(3) == "2.100000000000e+05"
    assert page.fields.topLevelItem(1).text(3) == "3.000000000000e-01"


def test_template_and_preview_use_line_numbered_monospace_editors(manager):
    """Both deck panes expose the common line-numbered monospace editor."""
    from PyQt6.QtGui import QFont
    from opencae.ui.deck_format_manager.code_editor import DeckCodeEditor

    page = manager.template_page
    assert isinstance(page.template, DeckCodeEditor)
    assert isinstance(page.preview, DeckCodeEditor)
    assert page.template.line_number_area_width() > 0
    assert page.preview.line_number_area_width() > 0
    assert page.template.font().styleHint() == QFont.StyleHint.Monospace
    assert page.preview.font().styleHint() == QFont.StyleHint.Monospace


def test_available_field_can_be_inserted_in_user_profile(manager):
    """The field helper inserts valid placeholders after a built-in is copied."""
    from PyQt6.QtGui import QTextCursor

    manager.profile_toolbar.copy_profile()
    manager.select_key("materials.elastic.isotropic")
    page = manager.template_page
    cursor = page.template.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("\nE=")
    page.template.setTextCursor(cursor)
    page.insert_field("youngs_modulus")
    assert page.template_text().endswith("E={youngs_modulus}")


def test_surface_template_uses_explicit_element_and_side_loop(manager):
    """Surface formatting exposes element and side independently inside a for loop."""
    manager.select_key("surfaces.definition")
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
    assert all(not item.isEnabled() for item in manager.global_page.findChildren(QCheckBox))


def test_every_navigation_leaf_has_an_explicit_template():
    """No record leaf may silently fall back to an invented keyword template."""
    from opencae.ui.deck_format_manager.catalog import GLOBAL_PAGES, TREE_SPEC
    from opencae.ui.deck_format_manager.template_catalog import TEMPLATE_SPECS

    def leaves(nodes):
        for node in nodes:
            children = tuple(node.get("children", ()))
            if children:
                yield from leaves(children)
            else:
                yield node["key"]

    record_leaves = set(leaves(TREE_SPEC)) - set(GLOBAL_PAGES)
    assert record_leaves <= set(TEMPLATE_SPECS)


def test_documented_femaster_flat_command_coverage_is_complete():
    """The editor covers every documented native command after the flattening boundary."""
    from opencae.ui.deck_format_manager.femaster_command_index import (
        FEMASTER_DOCUMENTED_COMMANDS,
        OPENCAE_ADDITIONAL_COMMANDS,
        STRUCTURED_MODEL_COMMANDS,
    )
    from opencae.ui.deck_format_manager.template_catalog import template_command_names

    commands = template_command_names()
    assert len(FEMASTER_DOCUMENTED_COMMANDS) == 59
    assert FEMASTER_DOCUMENTED_COMMANDS <= commands
    assert OPENCAE_ADDITIONAL_COMMANDS <= commands
    assert STRUCTURED_MODEL_COMMANDS.isdisjoint(commands)
