"""Runtime smoke coverage for the parametric Sketcher Qt surface."""

from PyQt6.QtWidgets import QApplication, QWidget

import opencae.ui.sketcher.dialog as dialog_module
from opencae.model.entities.geometry import SketchFeature
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.sketcher import SketchFeatureDialog

_QT_APPLICATION = None


class _PreviewStub(QWidget):
    """Avoid creating a VTK render window for this pure Qt editor smoke test."""

    def refresh_feature(self, _feature):
        return True

    def refresh_theme(self):
        return None


def _application():
    global _QT_APPLICATION
    _QT_APPLICATION = QApplication.instance() or QApplication([])
    return _QT_APPLICATION


def test_sketch_dialog_constructs_with_complete_toolbar_and_mode_switch(monkeypatch):
    _application()
    monkeypatch.setattr(dialog_module, "SketchFeaturePreview", _PreviewStub)

    dialog = SketchFeatureDialog(
        SketchFeature(name="Runtime Sketch", mode="Extrusion", depth=5.0)
    )
    try:
        assert dialog.canvas.tool == "Select"
        assert dialog.mode_combo.currentText() == "Extrusion"
        assert not dialog.canvas.show_revolve_axis

        for tool in (
            "Select",
            "Point",
            "Line",
            "Polyline",
            "Rectangle",
            "Circle",
            "Center Arc",
            "3-Point Arc",
            "Ellipse",
            "Spline",
            "Slot",
        ):
            action = dialog._tool_actions[tool]
            assert not action.icon().isNull(), tool

        constraint_kinds = {
            str(action.property("constraintKind"))
            for action in dialog.toolbar.actions()
            if action.property("constraintKind")
        }
        assert {
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
        } <= constraint_kinds

        dialog.mode_combo.setCurrentText("Revolve")
        assert dialog.canvas.show_revolve_axis
        assert dialog.depth_spin.isHidden()
        assert not dialog.angle_spin.isHidden()
    finally:
        dialog.close()


def test_all_semantic_sketch_icons_render_through_shared_factory():
    _application()
    kinds = (
        IconKind.SKETCH_SELECT,
        IconKind.SKETCH_POINT,
        IconKind.SKETCH_LINE,
        IconKind.SKETCH_POLYLINE,
        IconKind.SKETCH_RECTANGLE,
        IconKind.SKETCH_CIRCLE,
        IconKind.SKETCH_ARC,
        IconKind.SKETCH_ELLIPSE,
        IconKind.SKETCH_SPLINE,
        IconKind.SKETCH_SLOT,
        IconKind.SKETCH_CONSTRUCTION,
        IconKind.SKETCH_CONSTRAINT,
        IconKind.SKETCH_DIMENSION,
    )
    assert all(not make_icon(kind, 24).isNull() for kind in kinds)
