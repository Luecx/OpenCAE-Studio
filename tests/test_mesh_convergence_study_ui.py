"""Regression coverage for CAD Cell picking and multi-metric Study creation."""
from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import pytest

from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.project import Project
from opencae.model.selection import SelectableKind
from opencae.results import mesh_convergence as convergence
from opencae.ui.viewport.pyvista_picker import PyVistaPicker


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in self.callbacks:
            callback()


def test_new_convergence_qaction_bool_creates_instead_of_replacing(monkeypatch):
    from opencae.controllers import optimization_controller as module

    project = Project(name="Study ID regression")
    calls = []

    class _Store:
        def __init__(self):
            self.project = project

        def add_entity(self, description, parent_id, attr, entity):
            calls.append(("add", attr))
            project.studies.append(entity)
            project.rebuild_index(strict=True)

        def replace_entity(self, *args):
            raise AssertionError("New Study must never call replace_entity")

        def select(self, entity):
            calls.append(("selected", entity.id))

    class _Dialog:
        def __init__(self, project, current, parent):
            assert current is None
            self.accepted = _Signal()
            self.finished = _Signal()
            self.entity = MeshConvergenceStudy(name="New Study")

        def study(self):
            return self.entity

    created = []
    monkeypatch.setattr(module, "MeshConvergenceDialog", _Dialog)
    monkeypatch.setattr(module, "show_modeless_dialog", created.append)
    ctrl = SimpleNamespace(store=_Store(), parent=None, _dialogs=[], active_study_id="")
    module.OptimizationController.new_mesh_convergence(ctrl, False)
    assert len(created) == 1
    created[0].accepted.emit()
    assert [call[0] for call in calls] == ["add", "selected"]
    assert project.studies[0].name == "New Study"


def test_cell_mode_direct_click_targets_face_not_occluding_edge():
    face = object()
    edge = object()
    owner = SimpleNamespace(
        stage="PART", display_mode="geometry", selection_mode="cell",
        context_pick=SimpleNamespace(active=True),
        scene=SimpleNamespace(face_actors={face: "CAD-face", edge: "CAD-edge"}),
    )
    picker = PyVistaPicker.__new__(PyVistaPicker)
    picker.owner = owner
    picked = []
    picker._depth_pick = lambda _cursor: (edge, .2)
    picker._face_pick = lambda _cursor: face
    picker.picked_actor = picked.append
    assert picker.handles_direct_click()
    assert picker.pick_display_position((140, 70))
    assert picked == [face]


def test_displacement_control_tracks_original_coordinates_not_refined_node_ids(monkeypatch):
    calls = []

    def evaluate(_source, request, _loader):
        calls.append((request.field_name, request.probe_position, request.component))
        return {
            "elements": 25, "nodes": 30, "metric": request.metric,
            "field": request.field_name, "component": request.component,
            "value": request.probe_position[0],
        }

    monkeypatch.setattr(convergence, "evaluate_result", evaluate)
    study = MeshConvergenceStudy(
        name="Displacement convergence",
        metrics=[
            {"id": "control-a", "name": "Tip displacement",
             "kind": "displacement_control", "component": "Magnitude",
             "nodes": [
                 {"node_id": 110, "instance_id": "", "position": [4, 0, 0]},
                 {"node_id": 204, "instance_id": "", "position": [5, 0, 0]},
             ]},
        ],
    )
    sample = convergence.evaluate_all_metrics("unread.frd", study, object())
    assert len(sample["metrics"]) == 2
    assert sample["metrics"]["control-a::node:110"]["value"] == 4
    assert sample["metrics"]["control-a::node:204"]["value"] == 5
    assert calls == [
        ("DISP", (4., 0., 0.), "Magnitude"),
        ("DISP", (5., 0., 0.), "Magnitude"),
    ]


def test_multi_metric_assessment_keeps_each_control_independent():
    counts = [80, 170, 390]
    values = [
        (2.0, 10.0),
        (2.005, 12.0),
        (2.009, 15.0),
    ]
    samples = [
        {"metrics": {
            "tip": {"value": first, "elements": count, "metric": "probe"},
            "root": {"value": second, "elements": count, "metric": "nodal_max"},
        }}
        for count, (first, second) in zip(counts, values)
    ]
    results = convergence.assess_all_metrics(samples, .01)
    assert "within tolerance" in results["tip"]
    assert "Diagnostic only" in results["root"]


def test_modeless_dialog_uses_canonical_picker_and_saves_original_positions():
    """Picker can collect several ordinary clicks and persist original coordinates."""
    from PyQt6.QtWidgets import QApplication, QWidget
    from opencae.model.entities.analysis import Analysis
    from opencae.model.entities.parts import Part
    from opencae.model.selection import SelectionOperation, ViewportHit
    from opencae.ui.dialogs.mesh_convergence import MeshConvergenceDialog

    app = QApplication.instance() or QApplication([])
    project = Project(name="CAD")
    analysis = Analysis(name="Static", solver="FEMaster")
    project.analyses.append(analysis)
    part = Part(name="Mesh")
    part.mesh.node_count = 2
    project.parts.append(part)
    project.rebuild_index(strict=True)
    parent = QWidget()

    class Viewport:
        def __init__(self):
            self.callback = None
            self.finished = None
            self.mode = ""

        def set_display_mode(self, mode):
            self.mode = mode
        def show_region_preview(self, channel, definition, **style):
            self.preview = definition
        def clear_region_preview(self, channel):
            self.preview = None

        def begin_selection_session(self, policy, callback, finished=None):
            assert policy.accepted_kinds == frozenset({SelectableKind.MESH_NODE})
            self.callback, self.finished = callback, finished

        def cancel_context_pick(self):
            if self.finished:
                callback, self.finished = self.finished, None
                callback()

    parent.viewport = Viewport()
    dialog = MeshConvergenceDialog(project, parent=parent)
    try:
        assert dialog.metric.currentData() == "displacement_control"
        dialog.nodes.pick_button.setChecked(True)
        assert parent.viewport.mode == "mesh"
        for node, point in ((11, (1., 2., 3.)), (12, (4., 5., 6.))):
            parent.viewport.callback(ViewportHit(
                kind=SelectableKind.MESH_NODE, mesh_id=node,
                world_position=point, selection_operation=SelectionOperation.REPLACE,
                label=f"Node-{node}",
            ))
        dialog.nodes.finish_pick()
        saved = dialog.values()
        assert saved.analysis_ref.entity_id == analysis.id
        assert saved.metrics[0]["field_name"] == "DISP"
        assert saved.metrics[0]["component"] == "Magnitude"
        assert [item["node_id"] for item in saved.metrics[0]["nodes"]] == [11, 12]
        assert [item["position"] for item in saved.metrics[0]["nodes"]] == [
            [1., 2., 3.], [4., 5., 6.],
        ]
        assert parent.viewport.preview is not None
    finally:
        dialog.close()
        parent.close()
        app.processEvents()


def test_mesh_node_click_reaches_canonical_point_state_without_pyvista_callback(monkeypatch):
    from vtkmodules import vtkRenderingCore

    class Actor:
        def GetVisibility(self):
            return True
        def GetPickable(self):
            return True

    actors = [Actor()]
    class Picker:
        def SetTolerance(self, value):
            assert 0 < value <= .03
        def PickFromListOn(self):
            pass
        def AddPickList(self, actor):
            assert actor in actors
        def Pick(self, x, y, z, renderer):
            assert (x, y, z) == (150., 88., 0.)
            return True
        def GetPickPosition(self):
            return (5., 1., 0.)

    monkeypatch.setattr(vtkRenderingCore, "vtkPointPicker", Picker)
    owner = SimpleNamespace(
        stage="STUDIES", display_mode="mesh", selection_mode="point",
        context_pick=SimpleNamespace(
            active=True, accepts=lambda kind: kind is SelectableKind.MESH_NODE
        ),
        scene=SimpleNamespace(
            mesh_actor=actors[0], mesh_actors=[],
            authored_node_actor=None, authored_node_actors=[],
        ),
        plotter=SimpleNamespace(renderer=object()),
    )
    picker = PyVistaPicker.__new__(PyVistaPicker)
    picker.owner = owner
    picked = []
    picker.points = SimpleNamespace(picked=picked.append)
    assert picker.handles_direct_click()
    assert picker.pick_display_position((150., 88.))
    assert picked == [(5., 1., 0.)]
