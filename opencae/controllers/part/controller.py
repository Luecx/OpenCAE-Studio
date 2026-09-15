from opencae.model.geometry import (
    GeometryFeature,
    ImportedStepFeature,
    PartitionCellFeature,
    PartitionEdgeFeature,
    PartitionFaceFeature,
    PartitionPlaneFeature,
    SketchFeature,
)
from opencae.model.selection import (
    SelectableKind,
    SelectionPolicy,
    ViewportSelection,
)

from .context import PartContext
from .geometry_settings import PartGeometrySettings
from .element_controls import PartElementControls
from .datums import PartDatums
from .lifecycle import PartLifecycle
from .mesh_generation import PartMeshGeneration
from .mesh_editing import PartMeshEditing
from .mesh_settings import PartMeshSettings
from .mesh_seeds import PartMeshSeeds
from .partitions import PartPartitions
from .regions import PartRegions
from .sketching import PartSketching
from .visibility import PartVisibility


class PartController:
    def __init__(self, store, parent, units=None):
        self.context = PartContext(store, parent, units)
        self.service = self.context.service
        self.lifecycle = PartLifecycle(self.context)
        self.sketching = PartSketching(self.context)
        self.partitions = PartPartitions(self.context)
        self.settings = PartGeometrySettings(self.context)
        self.seeds = PartMeshSeeds(self.context)
        self.mesh_settings_manager = PartMeshSettings(self.context)
        self.element_control_manager = PartElementControls(self.context)
        self.generation = PartMeshGeneration(self.context)
        self.mesh_editing = PartMeshEditing(self.context)
        self.regions = PartRegions(self.context)
        self.datums = PartDatums(self.context)
        self.visibility_manager = PartVisibility(self.context)
        self._delegates = (
            self.lifecycle,
            self.sketching,
            self.partitions,
            self.settings,
            self.seeds,
            self.mesh_settings_manager,
            self.element_control_manager,
            self.generation,
            self.mesh_editing,
            self.regions,
            self.datums,
            self.visibility_manager,
        )

    def active_part(self):
        return self.context.active_part()

    def edit_node(self):
        """Edit selected mesh nodes or start a one-node viewport pick on demand."""
        selection = self.context.store.selection
        selected = (
            tuple(
                hit
                for hit in selection.hits
                if hit.kind is SelectableKind.MESH_NODE and hit.mesh_id is not None
            )
            if isinstance(selection, ViewportSelection)
            else ()
        )
        if selected:
            return self.mesh_editing.edit_node()

        part = self.active_part()
        if part is None:
            self.context.store.message.emit("Create or activate a Part first")
            return None
        if not part.mesh.node_count:
            self.context.store.message.emit("Create or generate mesh nodes first")
            return None

        viewport = getattr(self.context.parent, "viewport", None)
        if viewport is None:
            self.context.store.message.emit("Viewport node picking is unavailable")
            return None

        viewport.set_display_mode("mesh")
        policy = SelectionPolicy.create(
            {SelectableKind.MESH_NODE},
            multiple=False,
        )

        def picked(hit):
            self.context.store.select(ViewportSelection.from_hits((hit,)))
            self.mesh_editing.edit_node()

        viewport.begin_selection_session(policy, picked)
        return None

    def edit_geometry_feature(self, feature: GeometryFeature):
        if isinstance(feature, SketchFeature):
            return self.sketching.edit_sketch(feature)
        if isinstance(feature, ImportedStepFeature):
            return self.lifecycle.edit_import(feature)
        if isinstance(
            feature,
            (
                PartitionPlaneFeature,
                PartitionCellFeature,
                PartitionFaceFeature,
                PartitionEdgeFeature,
            ),
        ):
            return self.partitions.edit_partition(feature)
        self.context.store.message.emit(
            f"No editor is available for {feature.feature_type}"
        )

    def __getattr__(self, name):
        for delegate in self._delegates:
            if hasattr(delegate, name):
                return getattr(delegate, name)
        raise AttributeError(name)
