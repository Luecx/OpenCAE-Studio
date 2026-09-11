"""Defines reversible replacement of one finite element's type or connectivity."""

from dataclasses import dataclass, field

from opencae.model.entities.fem import Element
from opencae.store.commands import ProjectCommand

from .targets import (
    associations,
    metadata,
    part_for,
    restore_associations,
    restore_metadata,
)


@dataclass
class ReplaceElementCommand(ProjectCommand):
    """Replace one element while preserving stable element identity."""

    part_id: str
    before: Element
    after: Element
    _metadata: tuple | None = field(init=False, default=None, repr=False)
    _associations: dict | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        """Reject replacements that would silently renumber the element."""
        if self.before.id != self.after.id:
            raise ValueError("Replacing an element must preserve its ID")

    def is_atomic(self) -> bool:
        """Return true because the replacement is validated before mutation."""
        return True

    def apply(self, project):
        """Install the new type/connectivity and detach CAD membership."""
        mesh = part_for(project, self.part_id).mesh
        if mesh.element(self.before.id) != self.before:
            raise ValueError(f"Element {self.before.id} changed before this edit")
        if self._metadata is None:
            self._metadata = metadata(mesh)
            self._associations = associations(
                mesh,
                element_ids=(self.before.id,),
            )
        mesh.replace_element(
            self.after.id,
            type(self.after),
            self.after.nodes,
        )
        project.invalidate_index()
        return project

    def undo(self, project):
        """Restore the original element plus CAD membership and metadata."""
        mesh = part_for(project, self.part_id).mesh
        mesh.replace_element(
            self.before.id,
            type(self.before),
            self.before.nodes,
        )
        block = mesh._block_for_element(self.before.id)
        block.origins[block.position(self.before.id)] = self.before.origin
        restore_associations(mesh, self._associations or {})
        restore_metadata(mesh, self._metadata)
        project.invalidate_index()
        return project
