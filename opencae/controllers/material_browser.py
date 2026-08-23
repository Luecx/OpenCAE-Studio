"""Coordinates importing built-in material presets into the active Project."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog

from opencae.model.entities.resources.material_library import (
    material_from_preset,
    material_preset_rows,
)
from opencae.model.naming import name_exists, next_name
from opencae.ui.dialogs.material_browser import MaterialBrowserDialog


def add_material_from_browser(controller):
    """Open the built-in material browser and append the selected preset."""
    project = controller.store.project
    unit_system = controller.units.system
    dialog = MaterialBrowserDialog(
        material_preset_rows(unit_system),
        unit_system.symbol("pressure"),
        unit_system.symbol("density"),
        controller.parent,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    preset = dialog.selected_preset()
    if not preset:
        return None
    name = (
        preset
        if not name_exists(project.materials, preset)
        else next_name(preset, project.materials)
    )
    material = material_from_preset(
        preset,
        unit_system,
        name=name,
    )
    controller.store.add_entity(
        f"Added material {material.name} from browser",
        project.id,
        "materials",
        material,
    )
    stored = controller.store.project.resolve(material.id)
    controller.store.select(stored)
    return stored
