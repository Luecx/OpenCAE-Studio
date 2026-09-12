"""Defines the reversible creation of one Part-owned mesh node."""

from dataclasses import dataclass, field

from opencae.model.entities.fem import Node
from opencae.store.commands import ProjectCommand

from .targets import metadata, part_for, restore_metadata


@dataclass
class CreateNodeCommand(ProjectCommand):
    """Add one compact node row without snapshotting the complete mesh."""

    part_id: str
    node: Node
    _metadata: tuple | None = field(init=False, default=None, repr=False)

    def is_atomic(self) -> bool:
        """Return true because validation completes before the append."""
        return True

    def affects_project_index(self, project) -> bool:
        """Nodes are compact values and never participate in ProjectIndex."""
        return False

    def apply(self, project):
        """Append the recorded node to the addressed Part mesh."""
        mesh = part_for(project, self.part_id).mesh
        if self._metadata is None:
            self._metadata = metadata(mesh)
        mesh.add_node(self.node, self.node.id, origin=self.node.origin)
        return project

    def undo(self, project):
        """Remove the created node and restore derived mesh metadata."""
        mesh = part_for(project, self.part_id).mesh
        mesh.remove_node(self.node.id)
        restore_metadata(mesh, self._metadata)
        return project
