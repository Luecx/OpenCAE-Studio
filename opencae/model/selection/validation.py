from __future__ import annotations

from dataclasses import dataclass, field

from .definition import RegionDefinition
from .operands import (
    GeometryOperand,
    MeshElementOperand,
    MeshFacetOperand,
    MeshNodeOperand,
    NamedRegionOperand,
    ReferencePointOperand,
    UnresolvedOperand,
    WholeModelOperand,
)
from .resolution import RegionDiagnostic
from .types import RegionProjection, RegionRequirement


@dataclass(slots=True)
class _ValidationState:
    project: object
    requirement: RegionRequirement
    allow_part_local: bool
    terminal_count: int = 0
    occurrence_ids: set[str] = field(default_factory=set)


def validate_region_definition(
    project,
    definition,
    requirement: RegionRequirement,
    *,
    instance_id: str = "",
    allow_part_local: bool = False,
) -> list[RegionDiagnostic]:
    """Validate references and selection semantics without materializing members.

    Dialogs and normal model mutations keep the immutable ``RegionDefinition``
    intact.  Geometry-to-node/element/facet projection is deliberately left to
    solver deck generation, where a current mesh is guaranteed to be relevant.
    """

    if requirement is None:
        requirement = RegionRequirement()
    elif not isinstance(requirement, RegionRequirement):
        requirement = RegionRequirement(**requirement)
    state = _ValidationState(project, requirement, bool(allow_part_local))
    diagnostics: list[RegionDiagnostic] = []
    _walk(
        state,
        RegionDefinition.from_values(definition),
        diagnostics,
        stack=set(),
        inherited_instance=str(instance_id or ""),
    )

    if state.terminal_count < requirement.min_count:
        diagnostics.append(RegionDiagnostic(
            "too_few_operands",
            f"Target contains {state.terminal_count} valid selection operand(s); "
            f"at least {requirement.min_count} required",
        ))
    if requirement.max_count is not None and state.terminal_count > requirement.max_count:
        diagnostics.append(RegionDiagnostic(
            "too_many_operands",
            f"Target contains {state.terminal_count} selection operand(s); "
            f"at most {requirement.max_count} allowed",
        ))
    if requirement.require_unique_occurrence and len(state.occurrence_ids) > 1:
        diagnostics.append(RegionDiagnostic(
            "multiple_occurrences",
            "Target spans multiple assembly occurrences",
        ))
    return diagnostics


def region_definition_error(
    project,
    definition,
    requirement: RegionRequirement,
    *,
    instance_id: str = "",
    allow_part_local: bool = False,
) -> str:
    diagnostics = validate_region_definition(
        project,
        definition,
        requirement,
        instance_id=instance_id,
        allow_part_local=allow_part_local,
    )
    return "\n".join(dict.fromkeys(item.message for item in diagnostics if item.severity == "error"))


def _walk(state, definition, diagnostics, *, stack, inherited_instance):
    for index, item in enumerate(definition.items):
        operand = item.operand
        if isinstance(operand, UnresolvedOperand):
            diagnostics.append(RegionDiagnostic(
                "unresolved_legacy_selection",
                f"Unresolved legacy selection: {operand.legacy_label}",
                index,
            ))
            continue
        if isinstance(operand, NamedRegionOperand):
            region = state.project.try_resolve(operand.region_ref)
            if region is None:
                diagnostics.append(RegionDiagnostic(
                    "missing_region",
                    f"Region '{operand.region_ref.entity_id}' does not exist",
                    index,
                ))
                continue
            if region.id in stack:
                diagnostics.append(RegionDiagnostic(
                    "region_cycle",
                    f"Region cycle involving '{region.name}'",
                    index,
                ))
                continue
            nested_instance = _id(operand.instance_ref) or inherited_instance
            occurrence_error = _occurrence_error(state.project, nested_instance)
            if occurrence_error:
                diagnostics.append(RegionDiagnostic(
                    occurrence_error[0], occurrence_error[1], index
                ))
                continue
            _walk(
                state,
                RegionDefinition.from_values(region.definition),
                diagnostics,
                stack={*stack, region.id},
                inherited_instance=nested_instance,
            )
            continue

        error = _validate_terminal(state, operand, inherited_instance)
        if error:
            diagnostics.append(RegionDiagnostic(error[0], error[1], index))
            continue
        state.terminal_count += 1
        occurrence = _occurrence_id(operand, inherited_instance)
        if occurrence:
            state.occurrence_ids.add(occurrence)


def _validate_terminal(state, operand, inherited_instance):
    requirement = state.requirement
    projection = requirement.projection

    if isinstance(operand, ReferencePointOperand):
        point = state.project.try_resolve(operand.reference_point_ref)
        if point is None:
            return "missing_reference_point", "Reference point no longer exists"
        if projection not in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
            return "invalid_target_kind", "Reference points are not valid for this target"
        parent = state.project.try_resolve(state.project.index.parent_id.get(point.id))
        occurrence = _id(operand.instance_ref) or inherited_instance
        occurrence_error = _occurrence_error(
            state.project, occurrence, parent if _is_part(parent) else None
        )
        if occurrence_error:
            return occurrence_error
        if _is_part(parent) and not (occurrence or state.allow_part_local):
            return "missing_occurrence", f"Part reference point '{point.name}' requires an assembly instance occurrence"
        return None

    if isinstance(operand, WholeModelOperand):
        owner = state.project.try_resolve(operand.owner_ref) if operand.owner_ref else None
        occurrence = _id(operand.instance_ref) or inherited_instance
        occurrence_error = _occurrence_error(
            state.project, occurrence, owner if _is_part(owner) else None
        )
        if occurrence_error:
            return occurrence_error
        if operand.owner_ref and owner is None:
            return "missing_owner", "Whole-model selection owner no longer exists"
        if _is_part(owner) and not (occurrence or state.allow_part_local):
            return "missing_occurrence", f"Whole-part selection in '{owner.name}' requires an assembly instance occurrence"
        return None

    owner_ref = getattr(operand, "owner_ref", None)
    declared_owner = state.project.try_resolve(owner_ref)
    if owner_ref and declared_owner is None:
        return "missing_owner", "Selection owner no longer exists"
    declared_part = (
        declared_owner
        if _is_part(declared_owner)
        else state.project.try_resolve(declared_owner.part_ref)
        if _is_instance(declared_owner)
        else None
    )

    owner, part, occurrence = _owner(state.project, operand, inherited_instance)
    if part is None:
        return "missing_owner", "Selection owner no longer exists"
    occurrence_error = _occurrence_error(
        state.project, occurrence, declared_part or part
    )
    if occurrence_error:
        return occurrence_error
    if _is_part(owner) and not occurrence and not state.allow_part_local:
        return "missing_occurrence", f"Part selection in '{part.name}' requires an assembly instance occurrence"

    if isinstance(operand, GeometryOperand):
        if int(operand.dimension) not in requirement.allowed_dimensions:
            return "invalid_dimension", f"{_geometry_label(operand.dimension, operand.tag)} is not allowed for this target"
        stale = _stale_geometry(part, operand)
        if stale:
            return "stale_geometry_selection", stale
        return None

    if isinstance(operand, MeshNodeOperand):
        if projection not in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
            return "invalid_target_kind", "Mesh nodes are not valid for this target"
        stale = _stale_mesh(part, operand)
        if stale:
            return "stale_mesh_selection", stale
        if operand.node_id not in {int(value) for value in part.mesh.nodes.ids}:
            return "missing_node", f"Node {operand.node_id} does not exist in '{part.name}'"
        return None

    if isinstance(operand, MeshElementOperand):
        if projection not in {RegionProjection.NODES, RegionProjection.ELEMENTS, RegionProjection.FACETS}:
            return "invalid_target_kind", "Mesh elements are not valid for this target"
        stale = _stale_mesh(part, operand)
        if stale:
            return "stale_mesh_selection", stale
        if not _element_exists(part, operand.element_id):
            return "missing_element", f"Element {operand.element_id} does not exist in '{part.name}'"
        return None

    if isinstance(operand, MeshFacetOperand):
        if projection not in {RegionProjection.NODES, RegionProjection.FACETS}:
            return "invalid_target_kind", "Mesh facets are not valid for this target"
        stale = _stale_mesh(part, operand)
        if stale:
            return "stale_mesh_selection", stale
        if not _element_exists(part, operand.element_id):
            return "missing_element", f"Element {operand.element_id} does not exist in '{part.name}'"
        return None

    return "invalid_target_kind", f"Unsupported target operand: {type(operand).__name__}"


def _owner(project, operand, inherited_instance):
    occurrence = _id(getattr(operand, "instance_ref", None)) or inherited_instance or ""
    owner = project.try_resolve(getattr(operand, "owner_ref", None))
    if owner is None and occurrence:
        owner = project.try_resolve(occurrence)
    if _is_instance(owner):
        occurrence = owner.id
        return owner, project.try_resolve(owner.part_ref), occurrence
    if occurrence:
        instance = project.try_resolve(occurrence)
        if _is_instance(instance):
            return instance, project.try_resolve(instance.part_ref), instance.id
    return owner, owner if _is_part(owner) else None, occurrence


def _occurrence_id(operand, inherited_instance):
    return _id(getattr(operand, "instance_ref", None)) or inherited_instance or ""


def _occurrence_error(project, occurrence, expected_part=None):
    if not occurrence:
        return None
    instance = project.try_resolve(occurrence)
    if not _is_instance(instance):
        return "missing_occurrence", f"Assembly occurrence '{occurrence}' does not exist"
    if expected_part is not None:
        actual_part = project.try_resolve(instance.part_ref)
        if actual_part is None or actual_part.id != expected_part.id:
            return (
                "occurrence_owner_mismatch",
                f"Occurrence '{instance.name}' does not instantiate part '{expected_part.name}'",
            )
    return None


def _stale_mesh(part, operand):
    current = str(getattr(part.mesh, "revision", "") or "")
    selected = str(getattr(operand, "mesh_revision", "") or "")
    if selected and current and selected != current:
        return f"Mesh selection in '{part.name}' belongs to an older mesh revision"
    return ""


def _stale_geometry(part, operand):
    selected = str(getattr(operand, "topology_revision", "") or "")
    if not selected:
        return ""
    try:
        from opencae.geometry.fingerprint import part_fingerprint
        current = part_fingerprint(part, include_mesh=False)
    except (AttributeError, TypeError, ValueError):
        current = ""
    if current and current != selected:
        return f"Geometry selection in '{part.name}' belongs to an older geometry revision"
    return ""


def _element_exists(part, element_id):
    target = int(element_id)
    return any(target in {int(value) for value in block.ids} for block in part.mesh.element_blocks)


def _geometry_label(dimension, tag):
    labels = {0: "Vertex", 1: "Edge", 2: "Face", 3: "Cell"}
    return f"{labels.get(int(dimension), 'Geometry')}-{int(tag)}"


def _id(ref):
    return str(ref.entity_id) if ref else ""


def _is_part(value):
    from opencae.model.entities.parts import Part
    return isinstance(value, Part)


def _is_instance(value):
    from opencae.model.entities.assembly import Instance
    return isinstance(value, Instance)
