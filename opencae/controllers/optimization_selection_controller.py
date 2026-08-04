from __future__ import annotations

from opencae.model.entities.optimization import (
    OptimizationConstraint,
    OptimizationIteration,
    OptimizationObjective,
    OptimizationResponse,
    OptimizationRun,
    TopologyControls,
    TopologyFilterSettings,
    TopologyOptimization,
    TopologySymmetry,
)


class OptimizationSelectionMixin:
    def _selection_changed(self, entity):
        if not isinstance(
            entity,
            (
                TopologyOptimization,
                OptimizationResponse,
                OptimizationObjective,
                OptimizationConstraint,
                TopologyFilterSettings,
                TopologySymmetry,
                TopologyControls,
                OptimizationRun,
                OptimizationIteration,
            ),
        ):
            return
        try:
            self.parent.viewport.clear_region_previews("optimization-selection")
        except (AttributeError, RuntimeError):
            pass
        if not isinstance(entity, TopologySymmetry):
            try:
                self.parent.viewport.clear_datum_reference_preview()
            except (AttributeError, RuntimeError):
                pass
        if isinstance(entity, TopologyOptimization):
            self.parent.viewport.show_region_preview(
                "optimization-selection-design",
                entity.design_domain,
                color="#4fa3d9",
                opacity=.38,
            )
            if not entity.frozen_solid.empty:
                self.parent.viewport.show_region_preview(
                    "optimization-selection-solid",
                    entity.frozen_solid,
                    color="#5fbf75",
                    opacity=.75,
                )
            if not entity.frozen_void.empty:
                self.parent.viewport.show_region_preview(
                    "optimization-selection-void",
                    entity.frozen_void,
                    color="#cf6b75",
                    opacity=.75,
                )
        elif isinstance(entity, OptimizationResponse):
            self.parent.viewport.show_region_preview(
                "optimization-selection-response",
                entity.region,
                color="#64b5f6",
                opacity=.62,
            )
        elif isinstance(entity, (OptimizationObjective, OptimizationConstraint)):
            response = self.store.project.try_resolve(entity.response_ref)
            if isinstance(response, OptimizationResponse):
                self.parent.viewport.show_region_preview(
                    "optimization-selection-response",
                    response.region,
                    color="#64b5f6",
                    opacity=.62,
                )
        elif isinstance(entity, TopologySymmetry):
            self.parent.viewport.show_datum_reference_preview((entity.reference,))
        if isinstance(entity, (OptimizationRun, OptimizationIteration)):
            self._show_selected_iteration()
