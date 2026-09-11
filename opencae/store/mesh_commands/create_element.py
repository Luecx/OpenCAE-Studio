"""Defines reversible creation of one Part-owned finite element."""

from dataclasses import dataclass, field

from opencae.model.entities.fem import Element
from opencae.store.commands import ProjectCommand

from .targets import metadata, part_for, restore_metadata


@dataclass
class CreateElementCommand(ProjectCommand):
    """Create one compact element row and its canonical definition if needed."""

    part_id: str
    element: Element
    _metadata: tuple | None = field(init=False, default=None, repr=False)

    def is_atomic(self) -> bool:
        """Return true because element validation precedes compact mutation."""
        return True

    def apply(self, project):
        """Append the recorded element to the addressed Part mesh."""
        mesh = part_for(project, self.part_id).mesh
        if self._metadata is None:
            self._metadata = metadata(mesh)
        mesh.add_element(
            type(self.element),
            self.element.nodes,
            self.element.id,
            origin=self.element.origin,
        )
        project.invalidate_index()
        return project

    def undo(self, project):
        """Remove the created element and restore derived mesh metadata."""
        mesh = part_for(project, self.part_id).mesh
        mesh.remove_element(self.element.id)
        restore_metadata(mesh, self._metadata)
        project.invalidate_index()
        return project
