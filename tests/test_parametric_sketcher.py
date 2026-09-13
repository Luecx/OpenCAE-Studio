from copy import deepcopy

import pytest

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.geometry.errors import GeometryError
from opencae.model.core import decode_model, encode_model
from opencae.model.entities.geometry import (
    SketchCircle,
    SketchConstraint,
    SketchDefinition,
    SketchFeature,
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
        SketchLine(start=points[0].id, end=points[1].id),
        SketchLine(start=points[1].id, end=points[2].id),
        SketchLine(start=points[2].id, end=points[3].id),
        SketchLine(start=points[3].id, end=points[0].id),
    ]
    sketch.entities.extend(lines)
    return sketch, points, lines


def _circle_sketch(x: float, y: float, radius: float):
    sketch = SketchDefinition(grid_spacing=5.0)
    center = SketchPoint(x=x, y=y)
    sketch.points.append(center)
    sketch.entities.append(SketchCircle(center=center.id, radius=radius))
    return sketch


def test_sketch_model_round_trips_registered_entities_and_constraints():
    sketch, points, lines = _rectangle()
    sketch.entities.append(
        SketchCircle(center=points[0].id, radius=3.0, construction=True)
    )
    sketch.constraints.extend(
        (
            SketchConstraint(
                kind="Horizontal",
                refs=(f"entity:{lines[0].id}",),
            ),
            SketchConstraint(
                kind="Distance",
                refs=(f"entity:{lines[0].id}",),
                value=20.0,
            ),
        )
    )
    feature = SketchFeature(
        name="Base",
        mode="Extrusion",
        sketch=sketch,
        depth=8.0,
        symmetric=True,
    )

    decoded = decode_model(encode_model(feature))

    assert isinstance(decoded, SketchFeature)
    assert isinstance(decoded.sketch.entities[0], SketchLine)
    assert isinstance(decoded.sketch.entities[-1], SketchCircle)
    assert decoded.sketch.constraints[1].value == pytest.approx(20.0)
    assert decoded.symmetric is True


def test_solver_drives_rectangle_dimensions_and_reports_remaining_dof():
    sketch, points, lines = _rectangle(width=17.0, height=9.0)
    points[0].fixed = True
    sketch.constraints.extend(
        (
            SketchConstraint(
                kind="Horizontal", refs=(f"entity:{lines[0].id}",)
            ),
            SketchConstraint(
                kind="Vertical", refs=(f"entity:{lines[1].id}",)
            ),
            SketchConstraint(
                kind="Horizontal", refs=(f"entity:{lines[2].id}",)
            ),
            SketchConstraint(
                kind="Vertical", refs=(f"entity:{lines[3].id}",)
            ),
            SketchConstraint(
                kind="Distance",
                refs=(f"entity:{lines[0].id}",),
                value=25.0,
            ),
            SketchConstraint(
                kind="Distance",
                refs=(f"entity:{lines[1].id}",),
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
    reference = SketchLine(start=a.id, end=b.id)
    moving = SketchLine(start=c.id, end=d.id)
    sketch.entities.extend((reference, moving))
    sketch.constraints.append(
        SketchConstraint(
            kind="Collinear",
            refs=(f"entity:{reference.id}", f"entity:{moving.id}"),
        )
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
    line = SketchLine(start=a.id, end=b.id)
    sketch.entities.append(line)
    sketch.constraints.append(
        SketchConstraint(
            kind="Point on object",
            refs=(f"point:{point.id}", f"entity:{line.id}"),
        )
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
    axis = SketchLine(start=axis_a.id, end=axis_b.id, construction=True)
    sketch.entities.append(axis)
    sketch.constraints.append(
        SketchConstraint(
            kind="Symmetry",
            refs=(
                f"point:{first.id}",
                f"point:{second.id}",
                f"entity:{axis.id}",
            ),
        )
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
                refs=(f"entity:{lines[0].id}",),
                value=20.0,
            ),
            SketchConstraint(
                kind="Distance",
                refs=(f"entity:{lines[0].id}",),
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
    feature = SketchFeature(name="Sheet", mode="Planar", sketch=sketch)
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
        mode="Extrusion",
        sketch=sketch,
        depth=6.0,
    )
    part = Part(name="Extruded", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
        assert snapshot.bounds is not None
        # GeometrySnapshot bounds are xmin/ymin/zmin/xmax/ymax/zmax.
        assert snapshot.bounds[5] - snapshot.bounds[2] == pytest.approx(
            6.0, rel=1.0e-3
        )
    finally:
        CACHE.invalidate(part.id)


def test_symmetric_extrusion_is_centered_on_the_sketch_plane():
    sketch, _, _ = _rectangle()
    feature = SketchFeature(
        name="Symmetric Pad",
        mode="Extrusion",
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
    sketch.entities.append(SketchCircle(center=center.id, radius=4.0))
    feature = SketchFeature(
        name="Plate with hole",
        mode="Extrusion",
        sketch=sketch,
        depth=3.0,
    )
    part = Part(name="Holed Plate", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
        # A through-hole gives the solid more than the six faces of a box.
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
                mode="Extrusion",
                operation="New",
                sketch=base_sketch,
                depth=4.0,
            ),
            SketchFeature(
                name="Add",
                mode="Extrusion",
                operation="Add",
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
                mode="Extrusion",
                operation="New",
                sketch=base_sketch,
                depth=6.0,
            ),
            SketchFeature(
                name="Hole",
                mode="Extrusion",
                operation="Cut",
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
                mode="Extrusion",
                operation="New",
                sketch=base_sketch,
                depth=4.0,
            ),
            SketchFeature(
                name="Common",
                mode="Extrusion",
                operation="Intersect",
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
    # Rectangle deliberately stays above y=0; revolving it about X creates a tube.
    sketch, _, _ = _rectangle(width=15.0, height=4.0, y0=3.0)
    feature = SketchFeature(
        name="Revolve",
        mode="Revolve",
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
        mode="Revolve",
        sketch=sketch,
        angle_degrees=180.0,
    )
    part = Part(name="Invalid", geometry=[feature])
    try:
        with pytest.raises(GeometryError, match="cannot cross"):
            GeometryService().build_geometry(part, force=True)
    finally:
        CACHE.invalidate(part.id)
