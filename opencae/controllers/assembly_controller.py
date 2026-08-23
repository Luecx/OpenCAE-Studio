"""Provides the stable action-facing facade for Assembly editing workflows.

Instance, datum/reference-point, constraint, and region implementations live in
focused companion modules. This class owns only shared controller state and the
modeless dialog lifecycle expected by the main application.
"""

from __future__ import annotations

from .assembly_controller_constraints import show_constraint_dialog
from .assembly_controller_datums import (
    create_coordinate_system,
    create_reference_point,
)
from .assembly_controller_instances import (
    duplicate_instance,
    show_instance_dialog,
    toggle_instance_suppression,
    transform_instance,
)
from .assembly_regions import AssemblyRegions


class AssemblyController:
    """Action facade coordinating Assembly-specific application workflows."""

    def __init__(self, store, parent, part_controller=None):
        """Bind Assembly workflows to the project store and main window."""
        self.store = store
        self.parent = parent
        self.part_controller = part_controller
        self.regions = AssemblyRegions(self)
        self._dialogs = []

    def _create_part(self, parent, done) -> None:
        """Create a Part from an Instance dialog and report the new object."""
        before = {part.id for part in self.store.project.parts}
        self.part_controller.new_part(parent=parent)
        done(
            next(
                (
                    part
                    for part in self.store.project.parts
                    if part.id not in before
                ),
                None,
            )
        )

    def _finish_dialog(self, dialog) -> None:
        """Release viewport picking and forget one finished modeless dialog."""
        if hasattr(self.parent, "viewport"):
            self.parent.viewport.cancel_context_pick()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

    def add_instance(self) -> None:
        """Open the create-Instance workflow."""
        show_instance_dialog(self)

    def edit_instance(self, instance) -> None:
        """Open the edit-Instance workflow for ``instance``."""
        show_instance_dialog(self, instance)

    def duplicate_instance(self) -> None:
        """Duplicate the current fallback Assembly Instance."""
        duplicate_instance(self)

    def transform(self) -> None:
        """Open the Instance transform workflow."""
        transform_instance(self)

    def suppress_instance(self) -> None:
        """Toggle suppression on the current fallback Assembly Instance."""
        toggle_instance_suppression(self)

    def node_set(self) -> None:
        """Create an Assembly node Region through the shared region controller."""
        self.regions.node_set()

    def element_set(self) -> None:
        """Create an Assembly element Region through the shared region controller."""
        self.regions.element_set()

    def surface(self) -> None:
        """Create an Assembly surface Region through the shared region controller."""
        self.regions.surface()

    def edit_region(self, region):
        """Edit one existing Assembly Region."""
        return self.regions.edit(region)

    def coordinate_system(self) -> None:
        """Open the Assembly CoordinateSystem workflow."""
        create_coordinate_system(self)

    def reference_point(self) -> None:
        """Open the Assembly ReferencePoint workflow."""
        create_reference_point(self)

    def constraint(self, constraint_type="Kinematic Coupling") -> None:
        """Create an Assembly constraint of ``constraint_type``."""
        show_constraint_dialog(self, constraint_type)

    def edit_constraint(self, constraint) -> None:
        """Edit one existing Assembly constraint."""
        show_constraint_dialog(self, constraint.constraint_type, constraint)
