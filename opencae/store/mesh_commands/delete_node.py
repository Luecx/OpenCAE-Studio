"""Defines reversible deletion of one unused Part-owned mesh node."""

from dataclasses import dataclass, field

from opencae.model.entities.fem import Node
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
class DeleteNodeCommand(ProjectCommand):
    """Delete one unused node and repair direct NodeRegion membership."""

    part_id: str
    node: Node
    _metadata: tuple | None = field(init=False, default=None, repr=False)
    _associations: dict | None = field(init=False, default=None, repr=False)
    _regions: dict | None = field(init=False, default=None, repr=False)

    def is_atomic(self) -> bool:
        """Return true because connected-node deletion is rejected up front."""
        return True

    def affects_project_index(self, project) -> bool:
        """Region definitions contain refs but retain the same graph topology."""
        return False

    def apply(self, project):
        """Remove the node, direct region operands, and CAD memberships."""
        part = part_for(project, self.part_id)
        mesh = part.mesh
        if mesh.node(self.node.id) != self.node:
            raise ValueError(f"Node {self.node.id} changed before deletion")
        if self._metadata is None:
            self._metadata = metadata(mesh)
            self._associations = associations(mesh, node_ids=(self.node.id,))
        mesh.remove_node(self.node.id)
        self._regions = remove_region_references(
            part,
            node_ids=(self.node.id,),
        )
        return project

    def undo(self, project):
        """Restore the node and every removed membership."""
        part = part_for(project, self.part_id)
        part.mesh.add_node(self.node, self.node.id, origin=self.node.origin)
        restore_associations(part.mesh, self._associations or {})
        restore_region_references(part, self._regions or {})
        restore_metadata(part.mesh, self._metadata)
        return project
