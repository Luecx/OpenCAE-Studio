"""Defines ownership-transferring swaps for large persistent field values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opencae.model.core.persistent_model_field import is_project_index_field
from opencae.model.core.project_index_impact import value_affects_project_index

from .commands import ProjectCommand, _field_target


@dataclass
class OwnedFieldSwapCommand(ProjectCommand):
    """Swap a detached replacement with one live persistent field.

    This command is intended for large values such as ``Part.mesh``. The caller
    transfers exclusive ownership of ``replacement`` to the command. Applying,
    undoing, and redoing exchange references rather than deep-copying millions
    of numeric mesh values. The inactive value always lives in the history entry;
    the active value lives in the Project, so the undo buffer stores one mesh
    state per history side instead of duplicate snapshots.
    """

    entity_id: str
    field_name: str
    replacement: Any

    def is_atomic(self) -> bool:
        """The live field is touched only after address validation succeeds."""
        return True

    def affects_project_index(self, project) -> bool:
        """Return whether either side can own Entities or EntityRefs."""
        owner, field_name, field_info = _field_target(
            project.resolve(self.entity_id),
            self.field_name,
        )
        if not is_project_index_field(field_info):
            return False
        current = getattr(owner, field_name)
        return value_affects_project_index(current) or value_affects_project_index(
            self.replacement
        )

    def retains_large_payload(self) -> bool:
        """Mesh swaps keep the inactive full mesh alive for undo/redo."""
        return self.field_name == "mesh" or self.field_name.endswith(".mesh")

    def apply(self, project):
        """Exchange the live field with the command-owned replacement."""
        return self._swap(project)

    def undo(self, project):
        """Exchange the two values again to restore the previous state."""
        return self._swap(project)

    def _swap(self, project):
        owner, field_name, field_info = _field_target(
            project.resolve(self.entity_id),
            self.field_name,
        )
        current = getattr(owner, field_name)
        replacement = self.replacement
        affects_index = is_project_index_field(field_info) and (
            value_affects_project_index(current)
            or value_affects_project_index(replacement)
        )

        setattr(owner, field_name, replacement)
        self.replacement = current
        if affects_index:
            project.invalidate_index()
        return project
