"""Controller flow for authored parametric sketch features."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog

from opencae.model.entities.mesh import MeshValidity
from opencae.model.entities.parts import PartSourceKind
from opencae.model.geometry import SketchFeature
from opencae.model.naming import next_name
from opencae.ui.sketcher import SketchFeatureDialog


class PartSketching:
    """Create and edit persistent SketchFeature history entries."""

    def __init__(self, context):
        self.ctx = context

    def create_sketch(self, mode: str | None = None):
        part = self.ctx.active_part()
        if part is None:
            self.ctx.store.message.emit("Create or activate a Part first")
            return
        if PartSourceKind.coerce(part.source_type) is PartSourceKind.ORPHAN_MESH:
            self.ctx.store.message.emit(
                "Orphan-mesh Parts cannot receive CAD sketch features"
            )
            return

        candidate = self.ctx.geometry_candidate(part)
        default_mode = mode or (
            "Planar"
            if str(part.metadata.get("part_type", "")).casefold().startswith("2d")
            else "Extrusion"
        )
        feature = SketchFeature(
            name=next_name("Sketch", candidate.geometry),
            mode=default_mode,
            operation="Add" if candidate.geometry else "New",
        )
        dialog = SketchFeatureDialog(feature, parent=self.ctx.parent)
        dialog.setWindowTitle("Create Sketch Feature")
        ok = dialog.buttons.button(dialog.buttons.StandardButton.Ok)
        if ok is not None:
            ok.setText("Create Feature")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        feature = dialog.feature
        candidate.geometry.append(feature)
        candidate.mesh.lifecycle.validity = MeshValidity.OUTDATED
        if not self.ctx.validate_geometry(candidate, "Sketch feature failed"):
            return
        if self.ctx.commit_geometry_candidate(
            candidate, f"Created {feature.name}"
        ):
            self.ctx.store.select(
                self.ctx.store.project.try_resolve(feature.id) or self.ctx.active_part()
            )

    def edit_sketch(self, feature: SketchFeature):
        candidate, target = self.ctx.feature_copy(feature)
        if candidate is None or target is None:
            return
        dialog = SketchFeatureDialog(target, parent=self.ctx.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        edited = dialog.feature
        for index, item in enumerate(candidate.geometry):
            if item.id == target.id:
                candidate.geometry[index] = edited
                break
        candidate.mesh.lifecycle.validity = MeshValidity.OUTDATED
        if not self.ctx.validate_geometry(candidate, "Sketch update failed"):
            return
        self.ctx.commit_geometry_candidate(candidate, f"Edited {edited.name}")
