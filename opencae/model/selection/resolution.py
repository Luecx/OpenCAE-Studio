from __future__ import annotations

from dataclasses import dataclass, field

from opencae.model.core.reference import EntityRef
from .definition import RegionDefinition
from .operands import (
    GeometryOperand, MeshElementOperand, MeshFacetOperand, MeshNodeOperand,
    NamedRegionOperand, ReferencePointOperand, UnresolvedOperand, WholeModelOperand,
)
from .types import RegionProjection, RegionRequirement
from .facets import element_side_indices


@dataclass(frozen=True, slots=True, order=True)
class NodeOccurrence:
    owner_id: str
    node_id: int
    instance_id: str = ""


@dataclass(frozen=True, slots=True, order=True)
class ElementOccurrence:
    owner_id: str
    element_id: int
    instance_id: str = ""


@dataclass(frozen=True, slots=True, order=True)
class FacetOccurrence:
    owner_id: str
    element_id: int
    local_face: str
    instance_id: str = ""


@dataclass(frozen=True, slots=True, order=True)
class ReferencePointOccurrence:
    reference_point_id: str
    instance_id: str = ""


@dataclass(frozen=True, slots=True)
class RegionDiagnostic:
    code: str
    message: str
    item_index: int | None = None
    severity: str = "error"


@dataclass(slots=True)
class ResolvedRegion:
    nodes: set[NodeOccurrence] = field(default_factory=set)
    elements: set[ElementOccurrence] = field(default_factory=set)
    facets: set[FacetOccurrence] = field(default_factory=set)
    reference_points: set[ReferencePointOccurrence] = field(default_factory=set)
    diagnostics: list[RegionDiagnostic] = field(default_factory=list)

    @property
    def valid(self) -> bool: return not any(item.severity == "error" for item in self.diagnostics)

    def count(self, projection: RegionProjection) -> int:
        if projection in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
            return len(self.nodes) + len(self.reference_points)
        if projection == RegionProjection.ELEMENTS: return len(self.elements)
        return len(self.facets)


class RegionResolver:
    def __init__(self, project):
        self.project = project

    def resolve(self, definition: RegionDefinition, requirement: RegionRequirement, *, instance_id: str = "", allow_part_local: bool = False) -> ResolvedRegion:
        """Resolve a region definition for the requested solver projection.

        ``instance_id`` supplies the assembly occurrence for part-local inline
        definitions such as section assignments. Explicit occurrence references
        on operands always take precedence.
        """
        result = ResolvedRegion()
        self._resolve_definition(RegionDefinition.from_values(definition), requirement, result, set(), instance_id or None, allow_part_local)
        self._derive(requirement, result)
        self._validate(requirement, result)
        return result

    def _resolve_definition(self, definition, requirement, result, stack, inherited_instance, allow_part_local):
        for index, item in enumerate(definition.items):
            try:
                self._resolve_operand(item.operand, requirement, result, stack, inherited_instance, allow_part_local)
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                result.diagnostics.append(RegionDiagnostic("resolution_error", str(exc), index))

    def _resolve_operand(self, operand, requirement, result, stack, inherited_instance, allow_part_local):
        if isinstance(operand, UnresolvedOperand):
            result.diagnostics.append(RegionDiagnostic("unresolved_legacy_selection", f"Unresolved legacy selection: {operand.legacy_label}")); return
        if isinstance(operand, NamedRegionOperand):
            region = self.project.try_resolve(operand.region_ref)
            if region is None:
                result.diagnostics.append(RegionDiagnostic("missing_region", f"Region '{operand.region_ref.entity_id}' does not exist")); return
            if region.id in stack:
                result.diagnostics.append(RegionDiagnostic("region_cycle", f"Region cycle involving '{region.name}'")); return
            instance = _id(operand.instance_ref) or inherited_instance
            self._resolve_definition(region.definition, requirement, result, {*stack, region.id}, instance, allow_part_local); return
        if isinstance(operand, ReferencePointOperand):
            point = self.project.try_resolve(operand.reference_point_ref)
            if point is None:
                result.diagnostics.append(RegionDiagnostic("missing_reference_point", "Reference point no longer exists"))
                return
            instance_id = _id(operand.instance_ref) or inherited_instance or ""
            parent_id = self.project.index.parent_id.get(point.id)
            parent = self.project.try_resolve(parent_id)
            from opencae.model.entities.parts import Part
            if isinstance(parent, Part) and not instance_id and not allow_part_local:
                result.diagnostics.append(RegionDiagnostic(
                    "missing_occurrence",
                    f"Part reference point '{point.name}' requires an assembly instance occurrence",
                ))
                return
            result.reference_points.add(ReferencePointOccurrence(point.id, instance_id))
            return
        if isinstance(operand, WholeModelOperand):
            self._resolve_whole_model(operand, requirement, result, inherited_instance)
            return
        owner, part, instance_id = self._owner(operand, inherited_instance)
        if part is None:
            result.diagnostics.append(RegionDiagnostic("missing_owner", "Selection owner no longer exists")); return
        revision = getattr(part.mesh, "revision", "")
        selected_revision = getattr(operand, "mesh_revision", "")
        if selected_revision and revision and selected_revision != revision:
            result.diagnostics.append(RegionDiagnostic("stale_mesh_selection", f"Mesh selection in '{part.name}' belongs to an older mesh revision")); return
        if isinstance(operand, GeometryOperand):
            if operand.topology_revision:
                try:
                    from opencae.geometry.fingerprint import part_fingerprint
                    current_revision = part_fingerprint(part, include_mesh=False)
                except (AttributeError, TypeError, ValueError):
                    current_revision = ""
                if current_revision and current_revision != operand.topology_revision:
                    result.diagnostics.append(RegionDiagnostic(
                        "stale_geometry_selection",
                        f"Geometry selection in '{part.name}' belongs to an older geometry revision",
                    ))
                    return
            label = _geometry_label(operand.dimension, operand.tag)
            if operand.dimension not in requirement.allowed_dimensions:
                result.diagnostics.append(RegionDiagnostic("invalid_dimension", f"{label} is not allowed for this target")); return
            if requirement.projection in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
                result.nodes.update(NodeOccurrence(part.id, int(node), instance_id) for node in part.mesh.entity_nodes.get(label, ()))
            elif requirement.projection == RegionProjection.ELEMENTS:
                result.elements.update(ElementOccurrence(part.id, int(element), instance_id) for element in part.mesh.entity_elements.get(label, ()))
            elif requirement.projection == RegionProjection.FACETS:
                if operand.dimension == 2:
                    facets = _geometry_facets(part, label, instance_id)
                    if not facets:
                        result.diagnostics.append(RegionDiagnostic(
                            "missing_facet_association",
                            f"Geometry face '{label}' has no persisted mesh-facet association in '{part.name}'",
                        ))
                    result.facets.update(facets)
                else:
                    result.elements.update(ElementOccurrence(part.id, int(element), instance_id) for element in part.mesh.entity_elements.get(label, ()))
            return
        if isinstance(operand, MeshNodeOperand):
            if operand.node_id not in set(part.mesh.nodes.ids):
                result.diagnostics.append(RegionDiagnostic("missing_node", f"Node {operand.node_id} does not exist in '{part.name}'")); return
            result.nodes.add(NodeOccurrence(part.id, operand.node_id, instance_id)); return
        if isinstance(operand, MeshElementOperand):
            connectivity = _element_connectivity(part, operand.element_id)
            if connectivity is None:
                result.diagnostics.append(RegionDiagnostic("missing_element", f"Element {operand.element_id} does not exist in '{part.name}'"))
                return
            if requirement.projection in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
                result.nodes.update(NodeOccurrence(part.id, int(node), instance_id) for node in connectivity)
            else:
                result.elements.add(ElementOccurrence(part.id, operand.element_id, instance_id))
            return
        if isinstance(operand, MeshFacetOperand):
            block = _element_block(part, operand.element_id)
            if block is None:
                result.diagnostics.append(RegionDiagnostic("missing_element", f"Element {operand.element_id} does not exist in '{part.name}'"))
                return
            allowed = {"SPOS", "SNEG"} if block.definition.category in {"Shell Elements", "2D Elements"} else {side for side, _ in element_side_indices(block.definition.topology)}
            if operand.local_face not in allowed:
                result.diagnostics.append(RegionDiagnostic(
                    "invalid_element_face",
                    f"Element {operand.element_id} has no local face '{operand.local_face}'",
                ))
                return
            facet = FacetOccurrence(part.id, operand.element_id, operand.local_face, instance_id)
            result.facets.add(facet)
            if requirement.projection in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
                connectivity = _facet_connectivity(part, operand.element_id, operand.local_face)
                result.nodes.update(NodeOccurrence(part.id, int(node), instance_id) for node in connectivity)
            return

    def _resolve_whole_model(self, operand, requirement, result, inherited_instance):
        explicit_instance = _id(getattr(operand, "instance_ref", None)) or inherited_instance or ""
        owner_ref = getattr(operand, "owner_ref", None)
        if explicit_instance:
            instance = self.project.try_resolve(explicit_instance)
            part = self.project.try_resolve(getattr(instance, "part_ref", None)) if instance else None
            if part is None:
                result.diagnostics.append(RegionDiagnostic("missing_owner", "Whole-model occurrence no longer exists"))
                return
            self._add_entire_part(part, explicit_instance, result)
            return
        owner = self.project.try_resolve(owner_ref) if owner_ref else None
        from opencae.model.entities.assembly import Instance
        from opencae.model.entities.parts import Part
        if isinstance(owner, Instance):
            part = self.project.try_resolve(owner.part_ref)
            if part is not None: self._add_entire_part(part, owner.id, result)
            return
        if isinstance(owner, Part):
            self._add_entire_part(owner, "", result)
            return
        active = [item for item in self.project.assembly.instances if not item.suppressed]
        if active:
            for instance in active:
                part = self.project.try_resolve(instance.part_ref)
                if part is not None: self._add_entire_part(part, instance.id, result)
            return
        for part in self.project.parts:
            self._add_entire_part(part, "", result)

    @staticmethod
    def _add_entire_part(part, instance_id, result):
        result.nodes.update(NodeOccurrence(part.id, int(node), instance_id) for node in part.mesh.nodes.ids)
        for block in part.mesh.element_blocks:
            result.elements.update(ElementOccurrence(part.id, int(element), instance_id) for element in block.ids)

    def _owner(self, operand, inherited_instance):
        instance_id = _id(getattr(operand, "instance_ref", None)) or inherited_instance or ""
        owner = self.project.try_resolve(getattr(operand, "owner_ref", None))
        if owner is None and instance_id: owner = self.project.try_resolve(instance_id)
        from opencae.model.entities.assembly import Instance
        from opencae.model.entities.parts import Part
        if isinstance(owner, Instance):
            instance_id = owner.id; return owner, self.project.try_resolve(owner.part_ref), instance_id
        if instance_id:
            instance = self.project.try_resolve(instance_id)
            if isinstance(instance, Instance): return instance, self.project.try_resolve(instance.part_ref), instance.id
        return owner, owner if isinstance(owner, Part) else None, instance_id

    def _derive(self, requirement, result):
        if requirement.projection in {RegionProjection.NODES, RegionProjection.SINGLE_CONTROL_NODE}:
            for element in tuple(result.elements):
                part = self.project.try_resolve(element.owner_id)
                connectivity = _element_connectivity(part, element.element_id) if part else None
                if connectivity:
                    result.nodes.update(NodeOccurrence(element.owner_id, int(node), element.instance_id) for node in connectivity)
        elif requirement.projection == RegionProjection.FACETS:
            groups = {}
            for element in result.elements:
                groups.setdefault((element.owner_id, element.instance_id), set()).add(element.element_id)
            for (owner_id, instance_id), element_ids in groups.items():
                part = self.project.try_resolve(owner_id)
                if part:
                    result.facets.update(_boundary_facets(part, element_ids, instance_id))

    def _validate(self, requirement, result):
        count = result.count(requirement.projection)
        if count < requirement.min_count:
            result.diagnostics.append(RegionDiagnostic("too_few_members", f"Target resolves to {count} member(s), at least {requirement.min_count} required"))
        if requirement.max_count is not None and count > requirement.max_count:
            result.diagnostics.append(RegionDiagnostic("too_many_members", f"Target resolves to {count} member(s), at most {requirement.max_count} allowed"))
        if requirement.require_unique_occurrence:
            instances = {item.instance_id for item in (*result.nodes, *result.elements, *result.facets, *result.reference_points)}
            if len(instances) > 1:
                result.diagnostics.append(RegionDiagnostic("multiple_occurrences", "Target spans multiple assembly occurrences"))


def _id(ref) -> str: return ref.entity_id if ref else ""

def _geometry_label(dimension, tag): return f"{('Vertex','Edge','Face','Cell')[int(dimension)]}-{int(tag)}"

def _element_block(part, element_id):
    if part is None: return None
    for block in part.mesh.element_blocks:
        if any(int(current) == int(element_id) for current in block.ids): return block
    return None


def _element_connectivity(part, element_id):
    if part is None: return None
    for block in part.mesh.element_blocks:
        for current, connectivity in zip(block.ids, block.connectivity):
            if int(current) == int(element_id): return tuple(int(value) for value in connectivity)
    return None



def _facet_connectivity(part, element_id, local_face):
    if part is None: return ()
    for block in part.mesh.element_blocks:
        for current, connectivity in zip(block.ids, block.connectivity):
            if int(current) != int(element_id): continue
            if block.definition.category in {"Shell Elements", "2D Elements"}:
                return tuple(int(value) for value in connectivity) if local_face in {"SPOS", "SNEG"} else ()
            indices = dict(element_side_indices(block.definition.topology)).get(str(local_face), ())
            return tuple(int(connectivity[index]) for index in indices if index < len(connectivity))
    return ()

def _geometry_facets(part, label, instance_id):
    """Return the mesh-time persisted CAD-face association only.

    Runtime node-subset guessing is intentionally forbidden: it loses face
    orientation and can select internal or ambiguous element sides.
    """

    return {
        FacetOccurrence(part.id, int(element_id), str(local_face), instance_id)
        for element_id, local_face in getattr(part.mesh, "entity_facets", {}).get(label, ())
    }


def _boundary_facets(part, element_ids, instance_id):
    """Return the exterior oriented facets of one selected element region."""

    selected = {int(value) for value in element_ids}
    shell_facets = set()
    occurrences = {}
    for block in part.mesh.element_blocks:
        category = block.definition.category
        for element_id, connectivity in zip(block.ids, block.connectivity):
            element_id = int(element_id)
            if element_id not in selected:
                continue
            if category in {"Shell Elements", "2D Elements"}:
                shell_facets.add(FacetOccurrence(part.id, element_id, "SPOS", instance_id))
                continue
            for side, indices in element_side_indices(block.definition.topology):
                face_nodes = tuple(sorted(int(connectivity[index]) for index in indices if index < len(connectivity)))
                if not face_nodes:
                    continue
                occurrences.setdefault(face_nodes, []).append((element_id, side))
    volume_facets = {
        FacetOccurrence(part.id, element_id, side, instance_id)
        for entries in occurrences.values()
        if len(entries) == 1
        for element_id, side in entries
    }
    return shell_facets | volume_facets
