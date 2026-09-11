"""Defines reversible deletion of one Part-owned finite element."""

from dataclasses import dataclass, field

from opencae.model.entities.fem import Element
from opencae.store.commands import ProjectCommand

from .targets import (
    associations,
    metadata,
    part_for,
    remove_region_references,
    restore_associations,
    restore_metadata,
    restore_region_references,
)


@dataclass
class DeleteElementCommand(ProjectCommand):
    """Delete one element and repair direct Element/Surface regions."""

    part_id: str
    element: Element
    _metadata: tuple | None = field(init=False, default=None, repr=False)
    _associations: dict | None = field(init=False, default=None, repr=False)
    _regions: dict | None = field(init=False, default=None, repr=False)

    def is_atomic(self) -> bool:
        """Return true because the addressed element is validated first."""
        return True

    def apply(self, project):
        """Remove the element and every direct invalidated membership."""
        part = part_for(project, self.part_id)
        mesh = part.mesh
        if mesh.element(self.element.id) != self.element:
            raise ValueError(f"Element {self.element.id} changed before deletion")
        if self._metadata is None:
            self._metadata = metadata(mesh)
            self._associations = associations(
                mesh,
                element_ids=(self.element.id,),
            )
        mesh.remove_element(self.element.id)
        self._regions = remove_region_references(
            part,
            element_ids=(self.element.id,),
        )
        project.invalidate_index()
        return project

    def undo(self, project):
        """Restore the element and every removed membership."""
        part = part_for(project, self.part_id)
        part.mesh.add_element(
            type(self.element),
            self.element.nodes,
            self.element.id,
            origin=self.element.origin,
        )
        restore_associations(part.mesh, self._associations or {})
        restore_region_references(part, self._regions or {})
        restore_metadata(part.mesh, self._metadata)
        project.invalidate_index()
        return project
