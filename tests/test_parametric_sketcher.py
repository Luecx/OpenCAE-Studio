from copy import deepcopy

import pytest

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.geometry.errors import GeometryError
from opencae.model.core import decode_model, encode_model
from opencae.model.entities.geometry import (
    SketchBooleanOperation,
    SketchCircle,
    SketchConstraint,
    SketchConstraintKind,
    SketchDefinition,
    SketchFeature,
    SketchFeatureMode,
    SketchLine,
    SketchPoint,
)
from opencae.model.entities.parts import Part
from opencae.sketch import solve_sketch


def _rectangle(width=20.0, height=10.0, y0=2.0, x0=0.0):
    sketch = SketchDefinition(grid_spacing=5.0)
    points = [
        SketchPoint(x=x0, y=y0),
        SketchPoint(x=x0 + width, y=y0),
        SketchPoint(x=x0 + width, y=y0 + height),
        SketchPoint(x=x0, y=y0 + height),
    ]
    sketch.points.extend(points)
    lines = [
        SketchLine(start=points[0], end=points[1]),
        SketchLine(start=points[1], end=points[2]),
        SketchLine(start=points[2], end=points[3]),
        SketchLine(start=points[3], end=points[0]),
    ]
    sketch.entities.extend(lines)
    return sketch, points, lines


def _circle_sketch(x: float, y: float, radius: float):
    sketch = SketchDefinition(grid_spacing=5.0)
    center = SketchPoint(x=x, y=y)
    sketch.points.append(center)
    sketch.entities.append(SketchCircle(center=center, radius=radius))
    return sketch


def test_sketch_model_round_trips_object_identity_and_typed_domains():
    sketch, points, lines = _rectangle()
    circle = SketchCircle(center=points[0], radius=3.0, construction=True)
    sketch.entities.append(circle)
    sketch.constraints.extend(
        (
            SketchConstraint(
                kind=SketchConstraintKind.HORIZONTAL,
                refs=(lines[0],),
            ),
            SketchConstraint(
                kind=SketchConstraintKind.DISTANCE,
                refs=(lines[0],),
                value=20.0,
            ),
        )
    )
    feature = SketchFeature(
        name="Base",
        mode=SketchFeatureMode.EXTRUSION,
        operation=SketchBooleanOperation.NEW,
        sketch=sketch,
        depth=8.0,
        symmetric=True,
    )

    encoded = encode_model(feature)
    decoded = decode_model(encoded)

    assert isinstance(decoded, SketchFeature)
    assert decoded.mode is SketchFeatureMode.EXTRUSION
    assert decoded.operation is SketchBooleanOperation.NEW
    assert isinstance(decoded.sketch.entities[0], SketchLine)
    assert isinstance(decoded.sketch.entities[-1], SketchCircle)
    assert decoded.sketch.constraints[0].kind is SketchConstraintKind.HORIZONTAL
    assert decoded.sketch.constraints[1].value == pytest.approx(20.0)
    assert decoded.symmetric is True

    # Topology identity is restored, not reconstructed from strings later.
    assert decoded.sketch.entities[0].start is decoded.sketch.points[0]
    assert decoded.sketch.entities[0].end is decoded.sketch.points[1]
    assert decoded.sketch.entities[-1].center is decoded.sketch.points[0]
    assert decoded.sketch.constraints[0].refs[0] is decoded.sketch.entities[0]
    assert decoded.sketch.constraints[1].refs[0] is decoded.sketch.entities[0]

    # IDs only appear as serialization references at the codec boundary.
    first_line = encoded["sketch"]["entities"][0]
    assert first_line["start"] == {"__model_ref__": points[0].id}
    assert first_line["end"] == {"__model_ref__": points[1].id}
    first_constraint = encoded["sketch"]["constraints"][0]
    assert first_constraint["refs"]["__tuple__"][0] == {
        "__model_ref__": lines[0].id
    }


def test_sketch_topology_rejects_string_relationships_and_foreign_object_copies():
    a = SketchPoint(x=0.0, y=0.0)
    b = SketchPoint(x=1.0, y=0.0)
    with pytest.raises(TypeError, match="SketchPoint"):
        SketchLine(start=a.id, end=b.id)

    copied = deepcopy(a)
    line = SketchLine(start=copied, end=b)
    with pytest.raises(ValueError, match="not owned"):
        SketchDefinition(points=[a, b], entities=[line])

    valid = SketchLine(start=a, end=b)
    with pytest.raises(TypeError, match="SketchPoint or sketch entity"):
        SketchConstraint(kind="Horizontal", refs=(valid.id,))


def test_string_ui_inputs_are_coerced_at_model_boundary_to_finite_enums():
    sketch, _, lines = _rectangle()
    constraint = SketchConstraint(kind="horizontal distance", refs=(lines[0],))
    feature = SketchFeature(
        name="Coerced",
        mode="Extrusion",
        operation="Add",
        sketch=sketch,
        revolve_axis="X",
    )

    assert constraint.kind is SketchConstraintKind.DISTANCE_X
    assert feature.mode is SketchFeatureMode.EXTRUSION
    assert feature.operation is SketchBooleanOperation.ADD
    assert not isinstance(constraint.refs[0], str)
    assert not isinstance(lines[0].start, str)


def test_solver_drives_rectangle_dimensions_and_reports_remaining_dof():
    sketch, points, lines = _rectangle(width=17.0, height=9.0)
    points[0].fixed = True
    sketch.constraints.extend(
        (
            SketchConstraint(kind="Horizontal", refs=(lines[0],)),
            SketchConstraint(kind="Vertical", refs=(lines[1],)),
            SketchConstraint(kind="Horizontal", refs=(lines[2],)),
            SketchConstraint(kind="Vertical", refs=(lines[3],)),
            SketchConstraint(
                kind="Distance",
                refs=(lines[0],),
                value=25.0,
            ),
            SketchConstraint(
                kind="Distance",
                refs=(lines[1],),
                value=12.0,
            ),
        )
    )

    result = solve_sketch(sketch)

    assert result.success
    assert result.degrees_of_freedom >= 0
    assert points[1].x - points[0].x == pytest.approx(25.0, abs=1.0e-5)
    assert points[2].y - points[1].y == pytest.approx(12.0, abs=1.0e-5)


def test_collinear_constraint_moves_second_line_onto_fixed_reference_line():
    sketch = SketchDefinition()
    a = SketchPoint(x=0.0, y=0.0, fixed=True)
    b = SketchPoint(x=10.0, y=0.0, fixed=True)
    c = SketchPoint(x=2.0, y=3.0)
    d = SketchPoint(x=8.0, y=4.0)
    sketch.points.extend((a, b, c, d))
    reference = SketchLine(start=a, end=b)
    moving = SketchLine(start=c, end=d)
    sketch.entities.extend((reference, moving))
    sketch.constraints.append(
        SketchConstraint(kind="Collinear", refs=(reference, moving))
    )

    result = solve_sketch(sketch)

    assert result.success
    assert c.y == pytest.approx(0.0, abs=1.0e-6)
    assert d.y == pytest.approx(0.0, abs=1.0e-6)


def test_point_on_object_constraint_projects_point_onto_fixed_line():
    sketch = SketchDefinition()
    a = SketchPoint(x=0.0, y=0.0, fixed=True)
    b = SketchPoint(x=10.0, y=0.0, fixed=True)
    point = SketchPoint(x=4.0, y=5.0)
    sketch.points.extend((a, b, point))
    line = SketchLine(start=a, end=b)
    sketch.entities.append(line)
    sketch.constraints.append(
        SketchConstraint(kind="Point on object", refs=(point, line))
    )

    result = solve_sketch(sketch)

    assert result.success
    assert point.y == pytest.approx(0.0, abs=1.0e-6)


def test_symmetry_constraint_uses_selected_line_as_symmetry_axis():
    sketch = SketchDefinition()
    axis_a = SketchPoint(x=-10.0, y=0.0, fixed=True)
    axis_b = SketchPoint(x=10.0, y=0.0, fixed=True)
    first = SketchPoint(x=3.0, y=5.0)
    second = SketchPoint(x=5.0, y=-2.0)
    sketch.points.extend((axis_a, axis_b, first, second))
    axis = SketchLine(start=axis_a, end=axis_b, construction=True)
    sketch.entities.append(axis)
    sketch.constraints.append(
        SketchConstraint(kind="Symmetry", refs=(first, second, axis))
    )

    result = solve_sketch(sketch)

    assert result.success
    assert first.x == pytest.approx(second.x, abs=1.0e-6)
    assert first.y == pytest.approx(-second.y, abs=1.0e-6)


def test_conflicting_driving_dimensions_are_rejected_without_corrupting_geometry():
    sketch, _, lines = _rectangle()
    sketch.constraints.extend(
        (
            SketchConstraint(
                kind="Distance",
                refs=(lines[0],),
                value=20.0,
            ),
            SketchConstraint(
                kind="Distance",
                refs=(lines[0],),
                value=40.0,
            ),
        )
    )
    before = deepcopy(sketch)

    result = solve_sketch(sketch)

    assert not result.success
    assert [(point.x, point.y) for point in sketch.points] == [
        (point.x, point.y) for point in before.points
    ]


def test_planar_sketch_builds_a_surface_without_a_volume():
    sketch, _, _ = _rectangle()
    feature = SketchFeature(
        name="Sheet", mode=SketchFeatureMode.PLANAR, sketch=sketch
    )
    part = Part(name="Planar", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[2]
        assert not snapshot.entities[3]
        assert snapshot.bounds is not None
        assert snapshot.bounds[5] - snapshot.bounds[2] == pytest.approx(
            0.0, abs=1.0e-5
        )
    finally:
        CACHE.invalidate(part.id)


def test_extrusion_builds_a_real_occ_volume_from_closed_sketch():
    sketch, _, _ = _rectangle()
    feature = SketchFeature(
        name="Pad",
        mode=SketchFeatureMode.EXTRUSION,
        sketch=sketch,
        depth=6.0,
    )
    part = Part(name="Extruded", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
        assert snapshot.bounds is not None
        assert snapshot.bounds[5] - snapshot.bounds[2] == pytest.approx(
            6.0, rel=1.0e-3
        )
    finally:
        CACHE.invalidate(part.id)


def test_symmetric_extrusion_is_centered_on_the_sketch_plane():
    sketch, _, _ = _rectangle()
    feature = SketchFeature(
        name="Symmetric Pad",
        mode=SketchFeatureMode.EXTRUSION,
        sketch=sketch,
        depth=8.0,
        symmetric=True,
    )
    part = Part(name="Symmetric", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.bounds is not None
        assert snapshot.bounds[2] == pytest.approx(-4.0, abs=1.0e-4)
        assert snapshot.bounds[5] == pytest.approx(4.0, abs=1.0e-4)
    finally:
        CACHE.invalidate(part.id)


def test_extrusion_supports_a_nested_closed_hole_profile():
    sketch, _, _ = _rectangle(width=30.0, height=20.0, y0=-10.0)
    center = SketchPoint(x=15.0, y=0.0)
    sketch.points.append(center)
    sketch.entities.append(SketchCircle(center=center, radius=4.0))
    feature = SketchFeature(
        name="Plate with hole",
        mode=SketchFeatureMode.EXTRUSION,
        sketch=sketch,
        depth=3.0,
    )
    part = Part(name="Holed Plate", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
        assert len(snapshot.entities[2]) > 6
    finally:
        CACHE.invalidate(part.id)


def test_add_feature_fuses_overlapping_extrusions():
    base_sketch, _, _ = _rectangle(width=20.0, height=10.0, y0=0.0)
    add_sketch, _, _ = _rectangle(
        width=10.0,
        height=10.0,
        y0=0.0,
        x0=15.0,
    )
    part = Part(
        name="Added",
        geometry=[
            SketchFeature(
                name="Base",
                mode=SketchFeatureMode.EXTRUSION,
                operation=SketchBooleanOperation.NEW,
                sketch=base_sketch,
                depth=4.0,
            ),
            SketchFeature(
                name="Add",
                mode=SketchFeatureMode.EXTRUSION,
                operation=SketchBooleanOperation.ADD,
                sketch=add_sketch,
                depth=4.0,
            ),
        ],
    )
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert len(snapshot.entities[3]) == 1
        assert snapshot.bounds is not None
        assert snapshot.bounds[0] == pytest.approx(0.0, abs=1.0e-4)
        assert snapshot.bounds[3] == pytest.approx(25.0, abs=1.0e-4)
    finally:
        CACHE.invalidate(part.id)


def test_cut_feature_removes_an_extruded_profile_from_existing_solid():
    base_sketch, _, _ = _rectangle(width=20.0, height=10.0, y0=0.0)
    cutter = _circle_sketch(10.0, 5.0, 2.0)
    part = Part(
        name="Cut",
        geometry=[
            SketchFeature(
                name="Base",
                mode=SketchFeatureMode.EXTRUSION,
                operation=SketchBooleanOperation.NEW,
                sketch=base_sketch,
                depth=6.0,
            ),
            SketchFeature(
                name="Hole",
                mode=SketchFeatureMode.EXTRUSION,
                operation=SketchBooleanOperation.CUT,
                sketch=cutter,
                depth=6.0,
            ),
        ],
    )
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert len(snapshot.entities[3]) == 1
        assert len(snapshot.entities[2]) > 6
    finally:
        CACHE.invalidate(part.id)


def test_intersect_feature_keeps_only_the_common_extruded_volume():
    base_sketch, _, _ = _rectangle(width=20.0, height=10.0, y0=0.0)
    intersect_sketch, _, _ = _rectangle(
        width=20.0,
        height=10.0,
        y0=0.0,
        x0=10.0,
    )
    part = Part(
        name="Intersected",
        geometry=[
            SketchFeature(
                name="Base",
                mode=SketchFeatureMode.EXTRUSION,
                operation=SketchBooleanOperation.NEW,
                sketch=base_sketch,
                depth=4.0,
            ),
            SketchFeature(
                name="Common",
                mode=SketchFeatureMode.EXTRUSION,
                operation=SketchBooleanOperation.INTERSECT,
                sketch=intersect_sketch,
                depth=4.0,
            ),
        ],
    )
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert len(snapshot.entities[3]) == 1
        assert snapshot.bounds is not None
        assert snapshot.bounds[0] == pytest.approx(10.0, abs=1.0e-4)
        assert snapshot.bounds[3] == pytest.approx(20.0, abs=1.0e-4)
    finally:
        CACHE.invalidate(part.id)


def test_revolve_builds_volume_about_sketch_x_axis():
    sketch, _, _ = _rectangle(width=15.0, height=4.0, y0=3.0)
    feature = SketchFeature(
        name="Revolve",
        mode=SketchFeatureMode.REVOLVE,
        sketch=sketch,
        angle_degrees=360.0,
    )
    part = Part(name="Revolved", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
    finally:
        CACHE.invalidate(part.id)


def test_revolve_rejects_a_profile_that_crosses_the_x_axis():
    sketch, _, _ = _rectangle(width=10.0, height=4.0, y0=-2.0)
    feature = SketchFeature(
        name="Invalid Revolve",
        mode=SketchFeatureMode.REVOLVE,
        sketch=sketch,
        angle_degrees=180.0,
    )
    part = Part(name="Invalid", geometry=[feature])
    try:
        with pytest.raises(GeometryError, match="cannot cross"):
            GeometryService().build_geometry(part, force=True)
    finally:
        CACHE.invalidate(part.id)
