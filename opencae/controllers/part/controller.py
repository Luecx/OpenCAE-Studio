from opencae.model.geometry import GeometryFeature

from .context import PartContext
from .geometry_settings import PartGeometrySettings
from .datums import PartDatums
from .lifecycle import PartLifecycle
from .mesh_controls import PartMeshControls
from .mesh_generation import PartMeshGeneration
from .mesh_seeds import PartMeshSeeds
from .partitions import PartPartitions
from .regions import PartRegions


class PartController:
    def __init__(self, store, parent):
        self.context = PartContext(store, parent)
        self.service = self.context.service
        self.lifecycle = PartLifecycle(self.context)
        self.partitions = PartPartitions(self.context)
        self.settings = PartGeometrySettings(self.context)
        self.seeds = PartMeshSeeds(self.context)
        self.controls = PartMeshControls(self.context)
        self.generation = PartMeshGeneration(self.context)
        self.regions = PartRegions(self.context)
        self.datums = PartDatums(self.context)
        self._delegates = (
            self.lifecycle, self.partitions, self.settings, self.seeds,
            self.controls, self.generation, self.regions, self.datums,
        )

    def active_part(self):
        return self.context.active_part()

    def edit_geometry_feature(self, feature: GeometryFeature):
        if feature.feature_type.startswith("Imported"):
            return self.lifecycle.edit_import(feature)
        if feature.feature_type in {"Partition by Plane", "Partition Cell", "Partition Face", "Partition Edge"}:
            return self.partitions.edit_partition(feature)
        self.context.store.message.emit(f"No editor is available for {feature.feature_type}")

    def __getattr__(self, name):
        for delegate in self._delegates:
            if hasattr(delegate, name):
                return getattr(delegate, name)
        raise AttributeError(name)
