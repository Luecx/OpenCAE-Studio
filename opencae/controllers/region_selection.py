from __future__ import annotations

from opencae.model.selection import (
    RegionDefinition, RegionProjection, SelectionMultiplicity, SelectionOperation, SelectionPolicy, ViewportHit, definition_from_hit,
    named_region_definition, reference_point_definition,
)


def region_options(project, *, owner=None, include_reference_points=True, projections=None):
    """Return reusable region occurrences as ``(label, RegionDefinition)``."""
    result = []
    allowed = {
        projection
        for value in (projections or ())
        if (projection := RegionProjection.coerce(value)) is not None
    }
    allow_reference_points = bool(
        include_reference_points
        and (not allowed or RegionProjection.NODES in allowed)
    )

    def accepts(region): return not allowed or region.preferred_projection in allowed

    if owner is not None and hasattr(owner, "regions"):
        for region in owner.regions:
            if accepts(region): result.append((region.name, named_region_definition(region)))
        if allow_reference_points:
            for point in getattr(owner, "reference_points", ()): result.append((point.name, reference_point_definition(point)))
        return result

    for region in project.assembly.regions:
        if accepts(region): result.append((f"Assembly.{region.name}", named_region_definition(region)))
    if allow_reference_points:
        for point in project.assembly.reference_points: result.append((f"Assembly.{point.name}", reference_point_definition(point)))
    for instance in project.assembly.instances:
        if instance.suppressed: continue
        part = project.try_resolve(instance.part_ref)
        if part is None: continue
        for region in part.regions:
            if accepts(region): result.append((f"{instance.name}.{region.name}", named_region_definition(region, instance)))
        if allow_reference_points:
            for point in part.reference_points: result.append((f"{instance.name}.{point.name}", reference_point_definition(point, instance)))
    return result


def begin_region_pick(project, viewport, policy: SelectionPolicy, done, *, default_owner=None, finished=None):
    """Start one typed region-pick session.

    The selection is intentionally *not* resolved here.  A viewport hit becomes
    one immutable region operand and semantic node/element/facet resolution is
    deferred to solver deck generation.
    """
    def selected(raw):
        if not isinstance(raw, ViewportHit):
            raise TypeError("Region picking requires a typed ViewportHit")
        definition = definition_from_hit(project, raw, default_owner)
        operation = (
            SelectionOperation.REPLACE
            if policy.multiplicity == SelectionMultiplicity.SINGLE
            else getattr(raw, "selection_operation", SelectionOperation.ADD)
        )
        done(definition, operation)

    viewport.begin_selection_session(policy, selected, finished=finished)
    return viewport.cancel_context_pick


def policy_for_projection(projection, *, multiple=True):
    from opencae.model.selection import RegionProjection, RegionRequirement, SelectableKind, SelectionPolicy
    projection = RegionProjection(projection)
    if projection == RegionProjection.NODES:
        kinds = {
            SelectableKind.GEOMETRY_VERTEX, SelectableKind.GEOMETRY_EDGE,
            SelectableKind.GEOMETRY_FACE, SelectableKind.GEOMETRY_CELL,
            SelectableKind.MESH_NODE, SelectableKind.MESH_ELEMENT,
            SelectableKind.REFERENCE_POINT,
        }
        dimensions = (0, 1, 2, 3)
    elif projection == RegionProjection.ELEMENTS:
        kinds = {
            SelectableKind.GEOMETRY_EDGE, SelectableKind.GEOMETRY_FACE,
            SelectableKind.GEOMETRY_CELL, SelectableKind.MESH_ELEMENT,
        }
        dimensions = (1, 2, 3)
    else:
        kinds = {SelectableKind.GEOMETRY_FACE, SelectableKind.MESH_ELEMENT, SelectableKind.MESH_FACET}
        dimensions = (2,)
    return SelectionPolicy.create(kinds, multiple=multiple, requirement=RegionRequirement(projection, dimensions, 1))
