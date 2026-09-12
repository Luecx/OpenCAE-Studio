from copy import deepcopy

import pytest

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
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


def _rectangle(width=20.0, height=10.0, y0=2.0):
    sketch = SketchDefinition(grid_spacing=5.0)
    points = [
        SketchPoint(x=0.0, y=y0),
        SketchPoint(x=width, y=y0),
        SketchPoint(x=width, y=y0 + height),
        SketchPoint(x=0.0, y=y0 + height),
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


def test_sketch_model_round_trips_registered_entities_and_constraints():
    sketch, points, lines = _rectangle()
    sketch.entities.append(SketchCircle(center=points[0].id, radius=3.0, construction=True))
    sketch.constraints.extend(
        (
            SketchConstraint(kind="Horizontal", refs=(f"entity:{lines[0].id}",)),
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
            SketchConstraint(kind="Horizontal", refs=(f"entity:{lines[0].id}",)),
            SketchConstraint(kind="Vertical", refs=(f"entity:{lines[1].id}",)),
            SketchConstraint(kind="Horizontal", refs=(f"entity:{lines[2].id}",)),
            SketchConstraint(kind="Vertical", refs=(f"entity:{lines[3].id}",)),
            SketchConstraint(kind="Distance", refs=(f"entity:{lines[0].id}",), value=25.0),
            SketchConstraint(kind="Distance", refs=(f"entity:{lines[1].id}",), value=12.0),
        )
    )

    result = solve_sketch(sketch)

    assert result.success
    assert result.degrees_of_freedom >= 0
    assert points[1].x - points[0].x == pytest.approx(25.0, abs=1.0e-5)
    assert points[2].y - points[1].y == pytest.approx(12.0, abs=1.0e-5)


def test_conflicting_driving_dimensions_are_rejected_without_corrupting_geometry():
    sketch, _, lines = _rectangle()
    sketch.constraints.extend(
        (
            SketchConstraint(kind="Distance", refs=(f"entity:{lines[0].id}",), value=20.0),
            SketchConstraint(kind="Distance", refs=(f"entity:{lines[0].id}",), value=40.0),
        )
    )
    before = deepcopy(sketch)

    result = solve_sketch(sketch)

    assert not result.success
    assert [(point.x, point.y) for point in sketch.points] == [
        (point.x, point.y) for point in before.points
    ]


def test_extrusion_builds_a_real_occ_volume_from_closed_sketch():
    sketch, _, _ = _rectangle()
    feature = SketchFeature(name="Pad", mode="Extrusion", sketch=sketch, depth=6.0)
    part = Part(name="Extruded", geometry=[feature])
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
        assert snapshot.bounds is not None
        assert snapshot.bounds[5] - snapshot.bounds[4] == pytest.approx(6.0, rel=1.0e-3)
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
