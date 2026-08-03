from pathlib import Path
from types import SimpleNamespace

from opencae.controllers.region_selection import begin_region_pick
from opencae.model.core import EntityRef
from opencae.model.entities.constraints import direct_control_point_error
from opencae.model.selection import (
    GeometryOperand,
    NamedRegionOperand,
    ReferencePointOperand,
    RegionDefinition,
    RegionRequirement,
    SelectableKind,
    SelectionMultiplicity,
    SelectionOperation,
    SelectionPolicy,
    ViewportHit,
)
from opencae.ui.viewport.context_pick import ContextPickManager


class _Messages:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class _Owner:
    def __init__(self):
        self.selection_mode = "auto"
        self.display_mode = "geometry"
        self.message = _Messages()
        self.modes = []

    def set_selection_mode(self, value):
        self.selection_mode = value
        self.modes.append(value)


def _policy(*, multiple):
    return SelectionPolicy.create(
        {SelectableKind.GEOMETRY_VERTEX},
        multiple=multiple,
        requirement=RegionRequirement(),
    )


def test_single_pick_finishes_after_first_hit():
    owner = _Owner()
    manager = ContextPickManager(owner)
    selected = []
    finished = []
    manager.begin(_policy(multiple=False), selected.append, finished=lambda: finished.append(True))

    manager.consume((ViewportHit(SelectableKind.GEOMETRY_VERTEX, topology_tag=7),))

    assert len(selected) == 1
    assert finished == [True]
    assert manager.active is False
    assert owner.selection_mode == "auto"


def test_starting_another_field_finishes_previous_session():
    owner = _Owner()
    manager = ContextPickManager(owner)
    first_finished = []
    second_finished = []
    manager.begin(_policy(multiple=True), lambda _hit: None, finished=lambda: first_finished.append(True))
    manager.begin(_policy(multiple=False), lambda _hit: None, finished=lambda: second_finished.append(True))

    assert first_finished == [True]
    assert second_finished == []
    assert manager.active is True
    assert manager.policy.multiplicity == SelectionMultiplicity.SINGLE


def test_single_region_pick_always_replaces_even_with_shift_operation():
    callbacks = {}

    class _Viewport:
        def begin_selection_session(self, policy, callback, finished=None):
            callbacks.update(policy=policy, callback=callback, finished=finished)

        def cancel_context_pick(self):
            pass

    done = []
    policy = SelectionPolicy.create({SelectableKind.REFERENCE_POINT}, multiple=False)
    project = SimpleNamespace()
    begin_region_pick(project, _Viewport(), policy, lambda definition, operation: done.append((definition, operation)))
    callbacks["callback"](
        ViewportHit(
            SelectableKind.REFERENCE_POINT,
            entity_id="rp-1",
            selection_operation=SelectionOperation.ADD,
        )
    )

    assert done[0][1] == SelectionOperation.REPLACE
    assert len(done[0][0].items) == 1


def test_control_point_rejects_named_regions_and_accepts_direct_points():
    named = RegionDefinition.from_values((NamedRegionOperand(EntityRef("region-1", "Region")),))
    vertex = RegionDefinition.from_values((GeometryOperand(EntityRef("part-1", "Part"), 0, 3),))
    point = RegionDefinition.from_values((ReferencePointOperand(EntityRef("rp-1", "ReferencePoint")),))

    assert "named regions are not allowed" in direct_control_point_error(named)
    assert direct_control_point_error(vertex) == ""
    assert direct_control_point_error(point) == ""


def test_region_widget_defers_resolution_and_dialogs_keep_previews():
    root = Path(__file__).resolve().parents[1]
    widget = (root / "opencae/ui/core/widgets/region_selection.py").read_text()
    compact = (root / "opencae/ui/core/widgets/compact_region_selector.py").read_text()
    constraint = (root / "opencae/ui/dialogs/constraint.py").read_text()
    assembly = (root / "opencae/controllers/assembly_controller.py").read_text()
    sections = (root / "opencae/controllers/part/regions.py").read_text()
    section_dialog = (root / "opencae/ui/dialogs/section_assignment.py").read_text()

    assert "RegionResolver" not in widget
    assert "Projection to nodes, elements or facets is checked on Apply/OK" in widget
    assert "QPushButton:checked" in compact
    assert "Select in View" in compact and "Extended…" in compact
    assert "RegionResolver" not in compact
    assert "preview_changed" in constraint
    assert "set_extended_visible(tie)" in constraint
    assert "constraint-dialog-" in assembly
    assert "section-assignment-dialog-" in sections
    assert "value_changed.connect(self._filter_sections)" not in section_dialog


def test_coupling_control_point_policy_is_direct_single_point_only():
    from opencae.model.entities.constraints import ConstraintType, constraint_selection_policy

    policy = constraint_selection_policy(ConstraintType.KINEMATIC, "master")
    assert policy.multiplicity == SelectionMultiplicity.SINGLE
    assert policy.accepted_kinds == {
        SelectableKind.GEOMETRY_VERTEX,
        SelectableKind.MESH_NODE,
        SelectableKind.REFERENCE_POINT,
    }


def test_coupled_region_policy_is_multi_selection():
    from opencae.model.entities.constraints import ConstraintType, constraint_selection_policy

    policy = constraint_selection_policy(ConstraintType.KINEMATIC, "slave")
    assert policy.multiplicity == SelectionMultiplicity.MULTIPLE
    assert SelectableKind.GEOMETRY_FACE in policy.accepted_kinds
    assert SelectableKind.MESH_NODE in policy.accepted_kinds
