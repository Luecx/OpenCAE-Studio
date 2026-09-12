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


def test_sketcher_has_themed_grid_revolve_axis_and_constraint_toolbar():
    canvas = (ROOT / "opencae/ui/sketcher/canvas.py").read_text(encoding="utf-8")
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    assert 'PALETTE.get("axis_x"' in canvas
    assert "Qt.PenStyle.DashDotLine" in canvas
    assert "REVOLVE AXIS  X" in canvas
    for tool in ("Line", "Rectangle", "Circle", "Center Arc", "Ellipse", "Spline", "Slot"):
        assert f'"{tool}"' in canvas
    for constraint in (
        "Coincident", "Horizontal", "Vertical", "Parallel", "Perpendicular",
        "Tangent", "Equal", "Concentric", "Midpoint", "Fixed",
    ):
        assert f'"{constraint}"' in dialog
    for dimension in ("DistanceX", "DistanceY", "Angle", "Radius", "Diameter"):
        assert f'"{dimension}"' in dialog


def test_schema_25_is_reserved_for_registered_sketch_types():
    codec = (ROOT / "opencae/persistence/project_codec.py").read_text(encoding="utf-8")
    migrations = (ROOT / "opencae/persistence/migrations/__init__.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION = 25" in codec
    assert "migrate_v24_to_v25" in migrations
