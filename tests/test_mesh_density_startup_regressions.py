"""Regressions for generated face facets, density precision, and startup mapping."""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from opencae.controllers.part.mesh_persistence import _derive_entity_facets
from opencae.ui.dialogs.material_property import MaterialPropertyDialog
from opencae.ui.monitors.topology_threshold_control import TopologyThresholdControl


ROOT = Path(__file__).resolve().parents[1]


def test_solid_face_mapping_ignores_lower_dimensional_gmsh_element_ids(
    project_factory,
):
    """Gmsh surface-element ids must not filter OpenCAE volume elements."""
    data = project_factory(include_constraints=False)
    part = data["part"]

    # Face-1 is the first tetra face in the fixture.  In a real 3D Gmsh mesh,
    # getElements(2, face_tag) returns separate 2D surface-element ids rather
    # than the volume-element id stored in OpenCAE.  Reproduce that mismatch.
    part.mesh.entity_nodes["Face-1"] = [1, 2, 3]
    part.mesh.entity_elements["Face-1"] = [900001]

    facets = _derive_entity_facets(part)
    assert (1, "S1") in facets["Face-1"]


def test_density_inputs_preserve_small_engineering_values():
    """Density editors must not quantize realistic engineering-unit values."""
    app = QApplication.instance() or QApplication([])
    dialog = MaterialPropertyDialog(category="Density")
    control = TopologyThresholdControl()
    try:
        density = dialog._pages["Constant density"][0]
        assert density.editor.decimals() >= 15
        density.setValue(7.851234567e-9)
        assert density.value() == pytest.approx(7.851234567e-9, abs=5e-16)

        assert control.value_input.decimals() >= 10
        control.value_input.setValue(0.1234567891)
        assert control.value == pytest.approx(0.1234567891, abs=5e-11)
    finally:
        dialog.close()
        control.close()
        app.processEvents()


def test_startup_does_not_pump_events_with_hidden_qvtk_main_window():
    """The queued first VTK render may only run after the main window is mapped."""
    source = (ROOT / "opencae/app/application.py").read_text(encoding="utf-8")
    after_construction = source.split("window = MainWindow(context)", 1)[1]
    before_show = after_construction.split("window.show()", 1)[0]

    assert "app.processEvents()" not in before_show
    assert "_progress(app, startup, 94" not in before_show
    assert before_show.index("startup.hide()") >= 0
