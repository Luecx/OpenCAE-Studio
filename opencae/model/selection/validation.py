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
    """Validate object relationships and selection semantics without projection."""
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
        diagnostics.append(
            RegionDiagnostic(
                "too_few_operands",
                f"Target contains {state.terminal_count} valid selection operand(s); "
                f"at least {requirement.min_count} required",
            )
        )
    if requirement.max_count is not None and state.terminal_count > requirement.max_count:
        diagnostics.append(
            RegionDiagnostic(
                "too_many_operands",
                f"Target contains {state.terminal_count} selection operand(s); "
                f"at most {requirement.max_count} allowed",
            )
        )
    if requirement.require_unique_occurrence and len(state.occurrence_ids) > 1:
        diagnostics.append(
            RegionDiagnostic("multiple_occurrences", "Target spans multiple assembly occurrences")
        )
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
    return "\n".join(
        dict.fromkeys(item.message for item in diagnostics if item.severity == "error")
    )


def _walk(state, definition, diagnostics, *, stack, inherited_instance):
    for index, item in enumerate(definition.items):
        operand = item.operand
        if isinstance(operand, UnresolvedOperand):
            diagnostics.append(
                RegionDiagnostic(
                    "unresolved_legacy_selection",
                    f"Unresolved legacy selection: {operand.legacy_label}",
                    index,
                )
            )
            continue
        if isinstance(operand, NamedRegionOperand):
            region = operand.region
            if region is None or state.project.try_resolve(region) is not region:
                diagnostics.append(
                    RegionDiagnostic("missing_region", "Region no longer exists", index)
                )
                continue
            if region.id in stack:
                diagnostics.append(
                    RegionDiagnostic(
                        "region_cycle", f"Region cycle involving '{region.name}'", index
                    )
                )
                continue
            expected_projection = state.requirement.projection
            if (
                expected_projection
                in {
                    RegionProjection.NODES,
                    RegionProjection.ELEMENTS,
                    RegionProjection.FACETS,
                }
                and region.preferred_projection != expected_projection
            ):
                diagnostics.append(
                    RegionDiagnostic(
                        "incompatible_region_type",
                        f"{region.name} is typed as {_projection_label(region.preferred_projection)}; "
                        f"this target requires {_projection_label(expected_projection)}",
                        index,
                    )
                )
                continue
            nested_instance = _id(operand.instance) or inherited_instance
            occurrence_error = _occurrence_error(state.project, nested_instance)
            if occurrence_error:
                diagnostics.append(
                    RegionDiagnostic(occurrence_error[0], occurrence_error[1], index)
                )
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
        point = operand.reference_point
        if point is None or state.project.try_resolve(point) is not point:
            return "missing_reference_point", "Reference point no longer exists"
        if projection not in {
            RegionProjection.NODES,
            RegionProjection.SINGLE_CONTROL_NODE,
        }:
            return "invalid_target_kind", "Reference points are not valid for this target"
        parent = state.project.try_resolve(state.project.index.parent_id.get(point.id))
        occurrence = _id(operand.instance) or inherited_instance
        occurrence_error = _occurrence_error(
            state.project,
            occurrence,
            parent if _is_part(parent) else None,
        )
        if occurrence_error:
            return occurrence_error
        if _is_part(parent) and not (occurrence or state.allow_part_local):
            return (
                "missing_occurrence",
                f"Part reference point '{point.name}' requires an assembly instance occurrence",
            )
        return None

    if isinstance(operand, WholeModelOperand):
        owner = operand.owner
        occurrence = _id(operand.instance) or inherited_instance
        occurrence_error = _occurrence_error(
            state.project,
            occurrence,
            owner if _is_part(owner) else None,
        )
        if occurrence_error:
            return occurrence_error
        if owner is not None and state.project.try_resolve(owner) is not owner:
            return "missing_owner", "Whole-model selection owner no longer exists"
        if _is_part(owner) and not (occurrence or state.allow_part_local):
            return (
                "missing_occurrence",
                f"Whole-part selection in '{owner.name}' requires an assembly instance occurrence",
            )
        return None

    declared_owner = getattr(operand, "owner", None)
    if declared_owner is not None and state.project.try_resolve(declared_owner) is not declared_owner:
        return "missing_owner", "Selection owner no longer exists"
    declared_part = (
        declared_owner
        if _is_part(declared_owner)
        else declared_owner.part
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
        return (
            "missing_occurrence",
            f"Part selection in '{part.name}' requires an assembly instance occurrence",
        )

    if isinstance(operand, GeometryOperand):
        if int(operand.dimension) not in requirement.allowed_dimensions:
            return (
                "invalid_dimension",
                f"{_geometry_label(operand.dimension, operand.tag)} is not allowed for this target",
            )
        stale = _stale_geometry(part, operand)
        return ("stale_geometry_selection", stale) if stale else None

    if isinstance(operand, MeshNodeOperand):
        if projection not in {
            RegionProjection.NODES,
            RegionProjection.SINGLE_CONTROL_NODE,
        }:
            return "invalid_target_kind", "Mesh nodes are not valid for this target"
        stale = _stale_mesh(part, operand)
        if stale:
            return "stale_mesh_selection", stale
        node = operand.node
        try:
            canonical = part.mesh.node(node.id)
        except (AttributeError, KeyError, TypeError, ValueError):
            canonical = None
        if canonical is not node:
            return "missing_node", "Selected Node does not exist in the Part"
        return None

    if isinstance(operand, MeshElementOperand):
        if projection not in {
            RegionProjection.NODES,
            RegionProjection.ELEMENTS,
            RegionProjection.FACETS,
        }:
            return "invalid_target_kind", "Mesh elements are not valid for this target"
        stale = _stale_mesh(part, operand)
        if stale:
            return "stale_mesh_selection", stale
        element_id = getattr(operand.element, "id", -1)
        if not _element_exists(part, element_id):
            return "missing_element", "Selected Element does not exist in the Part"
        return None

    if isinstance(operand, MeshFacetOperand):
        if projection not in {RegionProjection.NODES, RegionProjection.FACETS}:
            return "invalid_target_kind", "Mesh facets are not valid for this target"
        stale = _stale_mesh(part, operand)
        if stale:
            return "stale_mesh_selection", stale
        element_id = getattr(operand.element, "id", -1)
        if not _element_exists(part, element_id):
            return "missing_element", "Selected Element does not exist in the Part"
        return None

    return "invalid_target_kind", f"Unsupported target operand: {type(operand).__name__}"


def _owner(project, operand, inherited_instance):
    instance = getattr(operand, "instance", None)
    occurrence = _id(instance) or inherited_instance or ""
    owner = getattr(operand, "owner", None)
    if _is_instance(owner):
        return owner, owner.part, owner.id
    if instance is None and occurrence:
        instance = project.try_resolve(occurrence)
    if _is_instance(instance):
        return instance, instance.part, instance.id
    return owner, owner if _is_part(owner) else None, occurrence


def _occurrence_id(operand, inherited_instance):
    return _id(getattr(operand, "instance", None)) or inherited_instance or ""


def _occurrence_error(project, occurrence, expected_part=None):
    if not occurrence:
        return None
    instance = project.try_resolve(occurrence)
    if not _is_instance(instance):
        return "missing_occurrence", f"Assembly occurrence '{occurrence}' does not exist"
    if expected_part is not None:
        actual_part = instance.part
        if actual_part is None or actual_part is not expected_part:
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
    return any(target in set(map(int, block.ids)) for block in part.mesh.element_blocks)


def _projection_label(value):
    labels = {
        RegionProjection.NODES: "Node Region",
        RegionProjection.ELEMENTS: "Element Region",
        RegionProjection.FACETS: "Surface Region",
        RegionProjection.SINGLE_CONTROL_NODE: "Control Point",
    }
    return labels.get(RegionProjection(value), "region")


def _geometry_label(dimension, tag):
    labels = {0: "Vertex", 1: "Edge", 2: "Face", 3: "Cell"}
    return f"{labels.get(int(dimension), 'Geometry')}-{int(tag)}"


def _id(value):
    return str(getattr(value, "id", "") or "")


def _is_part(value):
    from opencae.model.entities.parts import Part
    return isinstance(value, Part)


def _is_instance(value):
    from opencae.model.entities.assembly import Instance
    return isinstance(value, Instance)
