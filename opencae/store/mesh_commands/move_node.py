"""Defines reversible movement of one Part-owned mesh node."""

from dataclasses import dataclass, field

from opencae.model.entities.fem import Node
from opencae.store.commands import ProjectCommand

from .targets import (
    associations,
    metadata,
    part_for,
    restore_associations,
    restore_metadata,
)


@dataclass
class MoveNodeCommand(ProjectCommand):
    """Move one node while retaining only command-local undo data."""

    part_id: str
    before: Node
    after: Node
    _metadata: tuple | None = field(init=False, default=None, repr=False)
    _associations: dict | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        """Require immutable node identity across the replacement."""
        if self.before.id != self.after.id:
            raise ValueError("Moving a node must preserve its ID")

    def is_atomic(self) -> bool:
        """Return true because the move validates before changing storage."""
        return True

    def affects_project_index(self, project) -> bool:
        """Node coordinates are outside ProjectIndex."""
        return False

    def apply(self, project):
        """Move the node and detach affected optional CAD associations."""
        mesh = part_for(project, self.part_id).mesh
        if mesh.node(self.before.id) != self.before:
            raise ValueError(f"Node {self.before.id} changed before this edit")
        if self._metadata is None:
            incident = mesh.incident_element_ids(self.before.id)
            self._metadata = metadata(mesh)
            self._associations = associations(
                mesh,
                node_ids=(self.before.id,),
                element_ids=incident,
            )
        mesh.move_node(self.after.id, self.after.coordinates)
        return project

    def undo(self, project):
        """Restore the previous position, provenance, and CAD memberships."""
        mesh = part_for(project, self.part_id).mesh
        mesh.nodes.update(
            self.before.id,
            self.before.coordinates,
            origin=self.before.origin,
        )
        restore_associations(mesh, self._associations or {})
        restore_metadata(mesh, self._metadata)
        return project
