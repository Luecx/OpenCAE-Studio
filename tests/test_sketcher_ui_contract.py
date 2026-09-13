"""Source-level regressions for the authored sketch workflow."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_new_part_offers_sketch_extrude_and_revolve_entry_modes():
    source = (ROOT / "opencae/ui/dialogs/new_part.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "opencae/controllers/part/lifecycle.py").read_text(encoding="utf-8")
    assert '"Planar sketch", "Extrusion", "Revolve"' in source
    assert "SketchFeatureDialog(" in lifecycle
    assert '"Planar sketch": "Planar"' in lifecycle


def test_sketch_feature_is_exposed_in_part_workflows_and_feature_editor():
    ids = (ROOT / "opencae/ui/actions/ids.py").read_text(encoding="utf-8")
    actions = (ROOT / "opencae/ui/actions/catalog/part_actions.py").read_text(encoding="utf-8")
    ribbon = (ROOT / "opencae/ui/ribbon/part_page.py").read_text(encoding="utf-8")
    controller = (ROOT / "opencae/controllers/part/controller.py").read_text(encoding="utf-8")
    assert 'SKETCH_FEATURE = "part.sketch"' in ids
    assert "A.SKETCH_FEATURE" in actions
    assert "A.SKETCH_FEATURE" in ribbon
    assert "isinstance(feature, SketchFeature)" in controller
    assert "edit_sketch(feature)" in controller


def test_sketcher_has_themed_grid_revolve_axis_and_complete_constraint_toolbar():
    canvas = (ROOT / "opencae/ui/sketcher/canvas.py").read_text(encoding="utf-8")
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    extended = (ROOT / "opencae/ui/sketcher/constraint_dialog.py").read_text(
        encoding="utf-8"
    )
    assert '_theme("axis_x"' in canvas
    assert '_theme("axis_y"' in canvas
    assert "Qt.PenStyle.DashDotLine" in canvas
    assert "REVOLVE AXIS  X" in canvas
    for tool in (
        "Line",
        "Rectangle",
        "Circle",
        "Center Arc",
        "Ellipse",
        "Spline",
        "Slot",
    ):
        assert f'"{tool}"' in canvas
    constraint_source = dialog + extended
    for constraint in (
        "Coincident",
        "Horizontal",
        "Vertical",
        "Parallel",
        "Perpendicular",
        "Tangent",
        "Equal",
        "Concentric",
        "Midpoint",
        "Collinear",
        "Point on object",
        "Symmetry",
        "Fixed",
    ):
        assert f'"{constraint}"' in constraint_source
    for dimension in ("DistanceX", "DistanceY", "Angle", "Radius", "Diameter"):
        assert f'"{dimension}"' in dialog


def test_sketch_toolbar_uses_central_semantic_vector_icons():
    kinds = (ROOT / "opencae/ui/core/icons/kinds.py").read_text(encoding="utf-8")
    factory = (ROOT / "opencae/ui/core/icons/factory.py").read_text(encoding="utf-8")
    renderer = (ROOT / "opencae/ui/core/icons/sketch_renderer.py").read_text(
        encoding="utf-8"
    )
    dialog = (ROOT / "opencae/ui/sketcher/constraint_dialog.py").read_text(
        encoding="utf-8"
    )
    for kind in (
        "SKETCH_SELECT",
        "SKETCH_POINT",
        "SKETCH_LINE",
        "SKETCH_POLYLINE",
        "SKETCH_RECTANGLE",
        "SKETCH_CIRCLE",
        "SKETCH_ARC",
        "SKETCH_ELLIPSE",
        "SKETCH_SPLINE",
        "SKETCH_SLOT",
        "SKETCH_CONSTRUCTION",
        "SKETCH_CONSTRAINT",
        "SKETCH_DIMENSION",
    ):
        assert kind in kinds
        assert kind in renderer or kind in dialog
    assert "make_sketch_icon" in factory
    assert '"Rectangle": IconKind.SKETCH_RECTANGLE' in dialog
    assert '"Spline": IconKind.SKETCH_SPLINE' in dialog


def test_sketch_interaction_preserves_pick_order_and_last_valid_drag_state():
    canvas = (ROOT / "opencae/ui/sketcher/canvas.py").read_text(encoding="utf-8")
    assert "class _OrderedSelection" in canvas
    assert "self._selected_points = _OrderedSelection()" in canvas
    assert "self._selected_entities = _OrderedSelection()" in canvas
    assert "self._drag_last_valid = deepcopy(self.sketch)" in canvas
    assert "self.sketch = deepcopy(self._drag_last_valid)" in canvas
    assert "Constraint prevents moving the point" in canvas


def test_sketch_curve_creation_rejects_invalid_ellipse_and_arc_render_is_null_safe():
    canvas = (ROOT / "opencae/ui/sketcher/canvas.py").read_text(encoding="utf-8")
    assert "minor radius cannot exceed the major radius" in canvas
    assert "if center is None or start is None or end is None:" in canvas
    assert "None in {center, start, end}" not in canvas


def test_schema_25_is_reserved_for_registered_sketch_types():
    codec = (ROOT / "opencae/persistence/project_codec.py").read_text(encoding="utf-8")
    migrations = (ROOT / "opencae/persistence/migrations/__init__.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION = 25" in codec
    assert "migrate_v24_to_v25" in migrations
