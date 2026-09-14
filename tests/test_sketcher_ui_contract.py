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
    editor_canvas = (ROOT / "opencae/ui/sketcher/editor_canvas.py").read_text(encoding="utf-8")
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    extended = (ROOT / "opencae/ui/sketcher/constraint_dialog.py").read_text(
        encoding="utf-8"
    )
    assert '_theme("axis_x"' in editor_canvas
    assert '_theme("axis_y"' in editor_canvas
    assert "Qt.PenStyle.DashDotLine" in editor_canvas
    assert "REVOLVE AXIS  X" in editor_canvas
    assert "font.setPixelSize(10)" in editor_canvas
    assert "painter.resetTransform()" in editor_canvas
    assert "ScrollBarAlwaysOff" in editor_canvas
    for tool in (
        "Line",
        "Rectangle",
        "Circle",
        "Center Arc",
        "Ellipse",
        "Spline",
        "Slot",
    ):
        assert f'"{tool}"' in canvas or f'"{tool}"' in dialog
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


def test_sketcher_reuses_main_ribbon_metrics_and_collapses_to_three_semantic_groups():
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    ribbon = (ROOT / "opencae/ui/ribbon/ribbon_page.py").read_text(encoding="utf-8")
    group = (ROOT / "opencae/ui/ribbon/ribbon_group.py").read_text(encoding="utf-8")

    assert "ResponsiveRibbonPage" in dialog
    assert "RIBBON_PAGE_HEIGHT" in dialog
    assert 'RibbonGroupSpec(\n                "PRIMITIVES"' in dialog
    assert 'RibbonGroupSpec(\n                "CONSTRAINTS"' in dialog
    assert 'RibbonGroupSpec(\n                "CONSTRUCTION/GRID"' in dialog
    assert "if len(target) >= 2:" in dialog
    assert "return frozenset(spec.title for spec in self._specs)" in dialog
    assert "RIBBON_BUTTON_WIDTH" in ribbon
    assert "RIBBON_BUTTON_HEIGHT" in (ROOT / "opencae/ui/templates/primitives.py").read_text(encoding="utf-8")
    assert "PALETTE['ribbon_separator']" in group
    assert "QToolBar" not in dialog


def test_sketch_workspace_mode_switch_uses_the_canonical_viewport_toolbar():
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    main_toolbar = (ROOT / "opencae/ui/viewport/selection_toolbar.py").read_text(
        encoding="utf-8"
    )
    assert 'bar.setObjectName("ViewportToolbar")' in dialog
    assert "ViewportToolButton(" in dialog
    assert 'ViewportToolButton("Sketch"' in dialog
    assert '"3D Preview", checkable=True' in dialog
    assert 'ViewportToolButton("Fit"' in dialog
    assert 'self.setObjectName("ViewportToolbar")' in main_toolbar


def test_dimension_and_grid_are_normal_ribbon_buttons_and_construction_edits_selection():
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    editor_canvas = (ROOT / "opencae/ui/sketcher/editor_canvas.py").read_text(
        encoding="utf-8"
    )
    assert '"constraint.dimension", "Dimension", IconKind.SKETCH_DIMENSION' in dialog
    assert 'QAction(self._icon(IconKind.SKETCH_GRID), "Grid", self)' in dialog
    assert 'QAction(\n            self._icon(IconKind.SKETCH_CONSTRUCTION), "Construction", self' in dialog
    assert "self.canvas.selection_changed.connect(self._sync_construction_from_selection)" in dialog
    assert "for entity in changed:" in editor_canvas
    assert "entity.construction = enabled" in editor_canvas
    assert "self._push_history()" in editor_canvas


def test_sketch_toolbar_uses_distinct_central_semantic_vector_icons():
    kinds = (ROOT / "opencae/ui/core/icons/kinds.py").read_text(encoding="utf-8")
    factory = (ROOT / "opencae/ui/core/icons/factory.py").read_text(encoding="utf-8")
    renderer = (ROOT / "opencae/ui/core/icons/sketch_renderer.py").read_text(
        encoding="utf-8"
    )
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    required = (
        "SKETCH_SELECT",
        "SKETCH_POINT",
        "SKETCH_LINE",
        "SKETCH_POLYLINE",
        "SKETCH_RECTANGLE",
        "SKETCH_CIRCLE",
        "SKETCH_ARC_CENTER",
        "SKETCH_ARC_3POINT",
        "SKETCH_ELLIPSE",
        "SKETCH_SPLINE",
        "SKETCH_SLOT",
        "SKETCH_PRIMITIVES_MORE",
        "SKETCH_CONSTRUCTION",
        "SKETCH_GRID",
        "SKETCH_SNAP",
        "SKETCH_CONSTRAINT_COINCIDENT",
        "SKETCH_CONSTRAINT_HORIZONTAL",
        "SKETCH_CONSTRAINT_VERTICAL",
        "SKETCH_CONSTRAINT_PARALLEL",
        "SKETCH_CONSTRAINT_PERPENDICULAR",
        "SKETCH_CONSTRAINT_TANGENT",
        "SKETCH_CONSTRAINT_EQUAL",
        "SKETCH_CONSTRAINT_FIXED",
        "SKETCH_CONSTRAINT_MORE",
        "SKETCH_DIMENSION",
        "SKETCH_DIMENSION_DISTANCE",
        "SKETCH_DIMENSION_HORIZONTAL",
        "SKETCH_DIMENSION_VERTICAL",
        "SKETCH_DIMENSION_ANGLE",
        "SKETCH_DIMENSION_RADIUS",
        "SKETCH_DIMENSION_DIAMETER",
    )
    for kind in required:
        assert kind in kinds
        assert kind in renderer
        assert kind in dialog or kind.startswith("SKETCH_DIMENSION_")
    assert "make_sketch_icon" in factory
    assert "IconKind.PART" not in dialog


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


def test_persistent_sketch_graph_uses_objects_and_finite_domains_not_string_refs():
    model = (ROOT / "opencae/model/entities/geometry/sketch.py").read_text(
        encoding="utf-8"
    )
    solver = (ROOT / "opencae/sketch/solver.py").read_text(encoding="utf-8")
    codec = (ROOT / "opencae/model/core/model_codec.py").read_text(encoding="utf-8")

    assert "start: SketchPoint" in model
    assert "end: SketchPoint" in model
    assert "center: SketchPoint" in model
    assert "points: tuple[SketchPoint, ...]" in model
    assert "refs: tuple[SketchReference, ...]" in model
    assert "class SketchConstraintKind" in model
    assert "class SketchFeatureMode" in model
    assert "class SketchBooleanOperation" in model
    assert "__model_identity__ = True" in model
    assert "__model_ref__" in codec
    assert "_parse_entity_ref" not in solver
    assert 'startswith("point:")' not in solver
    assert 'startswith("entity:")' not in solver
    assert "start: str" not in model
    assert "refs: tuple[str" not in model


def test_sketcher_styling_is_part_of_central_theme_pipeline():
    modules = (ROOT / "opencae/ui/core/styles/__init__.py").read_text(
        encoding="utf-8"
    )
    sketch_style = (ROOT / "opencae/ui/core/styles/sketcher.py").read_text(
        encoding="utf-8"
    )
    dialog = (ROOT / "opencae/ui/sketcher/dialog.py").read_text(encoding="utf-8")
    assert "sketcher," in modules
    assert "QDialog#SketchFeatureDialog" in sketch_style
    assert "def css(p):" in sketch_style
    assert "{p['window']}" in sketch_style
    assert "_apply_local_style" not in dialog
    assert "setStyleSheet(" not in dialog


def test_schema_25_is_reserved_for_registered_sketch_types():
    codec = (ROOT / "opencae/persistence/project_codec.py").read_text(encoding="utf-8")
    migrations = (ROOT / "opencae/persistence/migrations/__init__.py").read_text(encoding="utf-8")
    assert "CURRENT_SCHEMA_VERSION = 25" in codec
    assert "migrate_v24_to_v25" in migrations
