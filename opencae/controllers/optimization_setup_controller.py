"""Coordinates creation, editing, validation and picking for topology setup entities."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from opencae.controllers.region_selection import (
    begin_region_pick,
    policy_for_projection,
    region_options,
)
from opencae.model.entities.optimization import (
    OptimizationConstraint,
    OptimizationIteration,
    OptimizationObjective,
    OptimizationResponse,
    OptimizationRun,
    SymmetryType,
    TopologyControls,
    TopologyFilterSettings,
    TopologyOptimization,
    TopologySymmetry,
)
from opencae.model.selection import RegionProjection, SelectableKind
from opencae.optimization import validate_topology_optimization
from opencae.ui.core.dialog_lifecycle import show_modeless_dialog
from opencae.ui.dialogs.optimization import (
    OptimizationConstraintDialog,
    OptimizationObjectiveDialog,
    OptimizationResponseDialog,
    TopologyControlsDialog,
    TopologyFilterDialog,
    TopologyOptimizationDialog,
    TopologySymmetryDialog,
)


class OptimizationSetupMixin:
    """Provides topology setup actions shared by the optimization controller."""

    def new_topology(self):
        selected = self.store.selection
        current = selected if isinstance(selected, TopologyOptimization) else None
        project = self.store.project
        options = region_options(
            project,
            projections=(RegionProjection.ELEMENTS,),
            include_reference_points=False,
        )
        value = current or TopologyOptimization(
            name=f"Topology Optimization-{len(project.optimizations) + 1}"
        )
        dialog = TopologyOptimizationDialog(
            project,
            value,
            pick_callback=self._region_pick,
            options=options,
            existing_names=[item.name for item in project.optimizations],
            parent=self.parent,
        )
        self._show(dialog, lambda: self._save_topology(dialog.result(), current))

    def response(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        selected = self.store.selection
        current = selected if isinstance(selected, OptimizationResponse) else None
        options = region_options(
            self.store.project,
            projections=(RegionProjection.ELEMENTS,),
            include_reference_points=False,
        )
        value = current or OptimizationResponse(
            name=f"Response-{len(optimization.responses) + 1}"
        )
        dialog = OptimizationResponseDialog(
            self.store.project,
            value,
            pick_callback=self._region_pick,
            options=options,
            existing_names=[item.name for item in optimization.responses],
            parent=self.parent,
        )
        self._show(
            dialog,
            lambda: self._save_nested(
                optimization.id,
                "responses",
                dialog.result(),
                current,
            ),
        )

    def objective(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        current = optimization.objective
        dialog = OptimizationObjectiveDialog(
            optimization,
            current,
            existing_names=[item.name for item in optimization.objectives],
            parent=self.parent,
        )
        self._show(
            dialog,
            lambda: self._save_nested(
                optimization.id,
                "objectives",
                dialog.result(),
                current,
            ),
        )

    def constraint(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        selected = self.store.selection
        current = selected if isinstance(selected, OptimizationConstraint) else None
        value = current or OptimizationConstraint(
            name=f"Constraint-{len(optimization.constraints) + 1}"
        )
        dialog = OptimizationConstraintDialog(
            optimization,
            value,
            existing_names=[item.name for item in optimization.constraints],
            parent=self.parent,
        )
        self._show(
            dialog,
            lambda: self._save_nested(
                optimization.id,
                "constraints",
                dialog.result(),
                current,
            ),
        )

    def filter_settings(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        current = optimization.filter_settings
        dialog = TopologyFilterDialog(
            current,
            existing_names=[item.name for item in optimization.filters],
            parent=self.parent,
        )
        self._show(
            dialog,
            lambda: self._save_nested(
                optimization.id,
                "filters",
                dialog.result(),
                current,
            ),
        )

    def symmetry(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        selected = self.store.selection
        current = selected if isinstance(selected, TopologySymmetry) else None
        value = current or TopologySymmetry(
            name=f"Symmetry-{len(optimization.symmetries) + 1}"
        )
        dialog = TopologySymmetryDialog(
            value,
            pick_reference=self._begin_symmetry_pick,
            clear_preview=self.parent.viewport.clear_datum_reference_preview,
            existing_names=[item.name for item in optimization.symmetries],
            parent=self.parent,
        )
        self._show(
            dialog,
            lambda: self._save_nested(
                optimization.id,
                "symmetries",
                dialog.result(),
                current,
            ),
        )

    def controls(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        current = optimization.control_settings
        dialog = TopologyControlsDialog(
            current,
            existing_names=[item.name for item in optimization.controls],
            parent=self.parent,
        )
        self._show(
            dialog,
            lambda: self._save_nested(
                optimization.id,
                "controls",
                dialog.result(),
                current,
            ),
        )

    def validate(self):
        optimization = self._optimization()
        if optimization is None:
            return self._need_optimization()
        errors, _index, _masks, operators = validate_topology_optimization(
            self.store.project,
            optimization,
            build_operators=True,
        )
        if errors:
            QMessageBox.warning(
                self.parent,
                "Topology validation failed",
                "\n".join(f"• {item}" for item in errors),
            )
            return
        QMessageBox.information(
            self.parent,
            "Topology validation",
            "Topology optimization is valid.\n\n"
            f"Density/constraint radius: {operators.density_constraint_radius:.6g}\n"
            f"Sensitivity radius: {operators.sensitivity_radius:.6g}",
        )

    def edit(self, entity):
        if not isinstance(entity, TopologySymmetry):
            try:
                self.parent.viewport.clear_datum_reference_preview()
            except (AttributeError, RuntimeError):
                pass
        handlers = {
            TopologyOptimization: self.new_topology,
            OptimizationResponse: self.response,
            OptimizationObjective: self.objective,
            OptimizationConstraint: self.constraint,
            TopologyFilterSettings: self.filter_settings,
            TopologySymmetry: self.symmetry,
            TopologyControls: self.controls,
        }
        for cls, handler in handlers.items():
            if isinstance(entity, cls):
                self.store.select(entity)
                return handler()
        if isinstance(entity, OptimizationRun):
            dialog = self._run_dialogs.get(entity.id)
            if dialog is not None:
                return dialog.reopen()
            self.store.select(entity)
            return self._show_selected_iteration()
        if isinstance(entity, OptimizationIteration):
            self.store.select(entity)
            return self._show_selected_iteration()
        return None

    def _show(self, dialog, accepted):
        self._dialogs.append(dialog)

        def apply():
            if hasattr(dialog, "validate") and not dialog.validate():
                return
            try:
                accepted()
            except Exception as exc:
                QMessageBox.warning(
                    dialog,
                    "Optimization definition",
                    str(exc),
                )
                return
            dialog.close()

        try:
            dialog.buttons.accepted.disconnect()
        except (TypeError, RuntimeError):
            pass
        dialog.buttons.accepted.connect(apply)
        dialog.finished.connect(
            lambda _code, value=dialog: self._dialog_closed(value)
        )
        show_modeless_dialog(dialog)

    def _dialog_closed(self, dialog):
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)
        self.parent.viewport.cancel_context_pick()
        self.parent.viewport.clear_datum_reference_preview()

    def _save_topology(self, candidate, current):
        project = self.store.project
        if not candidate.analysis_ref.entity_id:
            raise ValueError("Select a Linear Static analysis")
        if current is None:
            self.store.add_entity(
                f"Created {candidate.name}",
                project.id,
                "optimizations",
                candidate,
            )
        else:
            self.store.replace_entity(
                f"Edited {candidate.name}",
                project.id,
                "optimizations",
                candidate,
            )
        self.store.select(candidate)

    def _save_nested(self, optimization_id, attribute, candidate, current):
        optimization = self.store.project.try_resolve(optimization_id)
        if optimization is None:
            raise ValueError("The topology optimization no longer exists")
        if current is None:
            self.store.add_entity(
                f"Created {candidate.name}",
                optimization.id,
                attribute,
                candidate,
            )
        else:
            self.store.replace_entity(
                f"Edited {candidate.name}",
                optimization.id,
                attribute,
                candidate,
            )
        self.store.select(candidate)

    def _region_pick(self, _selector, done, finished):
        policy = policy_for_projection(
            RegionProjection.ELEMENTS,
            multiple=True,
        )
        return begin_region_pick(
            self.store.project,
            self.parent.viewport,
            policy,
            done,
            finished=finished,
        )

    def _begin_symmetry_pick(self, symmetry_type, callback, finished):
        if symmetry_type == SymmetryType.PLANAR:
            allowed = {
                SelectableKind.GEOMETRY_FACE,
                SelectableKind.DATUM_PLANE,
            }
        else:
            allowed = {
                SelectableKind.GEOMETRY_EDGE,
                SelectableKind.DATUM_VECTOR,
            }

        def selected(reference):
            callback(reference)
            self.parent.viewport.show_datum_reference_preview((reference,))

        self.parent.viewport.begin_datum_reference_pick(
            allowed,
            selected,
            finished=finished,
        )

    def _optimization(self):
        project = self.store.project
        entity = self.store.selection
        while entity is not None:
            if isinstance(entity, TopologyOptimization):
                return project.try_resolve(entity.id)
            parent_id = project.index.parent_id.get(getattr(entity, "id", ""))
            entity = project.try_resolve(parent_id) if parent_id else None
        return project.optimizations[0] if project.optimizations else None

    def _need_optimization(self):
        self.store.message.emit(
            "Create or select a topology optimization first"
        )
