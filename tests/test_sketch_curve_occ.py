"""Real OpenCASCADE coverage for the curve families exposed by the Sketcher."""

from opencae.geometry import GeometryService
from opencae.geometry.cache import CACHE
from opencae.model.entities.geometry import (
    SketchArc,
    SketchDefinition,
    SketchEllipse,
    SketchFeature,
    SketchLine,
    SketchPoint,
    SketchSpline,
)
from opencae.model.entities.parts import Part


def _assert_extrudes_to_volume(sketch: SketchDefinition, name: str) -> None:
    part = Part(
        name=name,
        geometry=[
            SketchFeature(
                name=f"{name} feature",
                mode="Extrusion",
                sketch=sketch,
                depth=3.0,
            )
        ],
    )
    try:
        snapshot = GeometryService().build_geometry(part, force=True)
        assert snapshot.entities[3]
        assert snapshot.surfaces
    finally:
        CACHE.invalidate(part.id)


def test_ellipse_profile_extrudes_to_occ_volume():
    sketch = SketchDefinition()
    center = SketchPoint(x=0.0, y=0.0)
    major = SketchPoint(x=6.0, y=0.0)
    sketch.points.extend((center, major))
    sketch.entities.append(
        SketchEllipse(center=center.id, major=major.id, minor_radius=3.0)
    )

    _assert_extrudes_to_volume(sketch, "Ellipse")


def test_arc_and_line_profile_extrudes_to_occ_volume():
    sketch = SketchDefinition()
    center = SketchPoint(x=0.0, y=0.0, construction=True)
    start = SketchPoint(x=-5.0, y=0.0)
    end = SketchPoint(x=5.0, y=0.0)
    sketch.points.extend((center, start, end))
    sketch.entities.extend(
        (
            SketchArc(
                center=center.id,
                start=start.id,
                end=end.id,
                clockwise=False,
            ),
            SketchLine(start=end.id, end=start.id),
        )
    )

    _assert_extrudes_to_volume(sketch, "Arc profile")


def test_open_spline_closed_by_line_extrudes_to_occ_volume():
    sketch = SketchDefinition()
    first = SketchPoint(x=-5.0, y=0.0)
    middle = SketchPoint(x=0.0, y=5.0)
    last = SketchPoint(x=5.0, y=0.0)
    sketch.points.extend((first, middle, last))
    sketch.entities.extend(
        (
            SketchSpline(points=(first.id, middle.id, last.id)),
            SketchLine(start=last.id, end=first.id),
        )
    )

    _assert_extrudes_to_volume(sketch, "Spline profile")


def test_slot_curve_mix_extrudes_to_occ_volume():
    sketch = SketchDefinition()
    center_a = SketchPoint(x=0.0, y=0.0, construction=True)
    center_b = SketchPoint(x=10.0, y=0.0, construction=True)
    top_a = SketchPoint(x=0.0, y=2.0)
    top_b = SketchPoint(x=10.0, y=2.0)
    bottom_b = SketchPoint(x=10.0, y=-2.0)
    bottom_a = SketchPoint(x=0.0, y=-2.0)
    sketch.points.extend(
        (center_a, center_b, top_a, top_b, bottom_b, bottom_a)
    )
    sketch.entities.extend(
        (
            SketchLine(start=top_a.id, end=top_b.id),
            SketchArc(
                center=center_b.id,
                start=top_b.id,
                end=bottom_b.id,
                clockwise=True,
            ),
            SketchLine(start=bottom_b.id, end=bottom_a.id),
            SketchArc(
                center=center_a.id,
                start=bottom_a.id,
                end=top_a.id,
                clockwise=True,
            ),
        )
    )

    _assert_extrudes_to_volume(sketch, "Slot")
