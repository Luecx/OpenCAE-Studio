"""Single metric convergence and picker-driven stored Path lifecycle."""
from __future__ import annotations

from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication, QWidget

from opencae.jobs.mesh_convergence_runner import MeshConvergenceRunner
from opencae.model.entities.jobs import ResultSet
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.results.mesh_path import stored_paths
from opencae.ui.dialogs import result_paths_and_plots as paths


def test_one_displacement_metric_and_geometric_scales_in_study_editor():
    from opencae.model.entities.analysis import Analysis
    from opencae.model.project import Project
    from opencae.ui.dialogs.mesh_convergence import MeshConvergenceDialog

    app = QApplication.instance() or QApplication([])
    project = Project(name="Refinement")
    project.analyses.append(Analysis(name="Static"))
    project.rebuild_index(strict=True)
    dialog = MeshConvergenceDialog(project, parent=None)
    try:
        assert dialog.metric.count() == 1
        assert dialog.metric.currentData() == "displacement_control"
        dialog.factor.setValue(0.7)
        dialog.iterations.setValue(5)
        study = dialog.values()
        assert study.mesh_scaling_factor == 0.7
        assert study.max_iterations == 5
        assert study.mesh_scales == [
            0.7 ** i for i in range(5)
        ]
        assert len(study.metrics) == 1
        assert study.metrics[0]["nodes"] == []
        assert study.metrics[0]["component"] == "Magnitude"
        assert study.metrics[0]["name"] == "Displacement"
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_runner_stops_when_three_consecutive_mesh_levels_converge():
    app = QApplication.instance() or QApplication([])
    study = MeshConvergenceStudy(
        name="Study", mesh_scaling_factor=.7, max_iterations=8,
        relative_tolerance=.02,
    )
    study.metrics = [dict(
        id="displacement", kind="displacement_control",
        name="Displacement", component="Magnitude", nodes=[],
    )]
    runner = MeshConvergenceRunner(
        SimpleNamespace(), study, "analysis", object(), "", "", "/tmp",
    )
    advanced = []
    finished = []
    runner._advance = lambda: advanced.append(runner._level)
    runner._finish = lambda status, message: finished.append((status, message))
    for index, (elements, value) in enumerate(
        ((100, 1.0), (200, 1.005), (400, 1.007)), start=1
    ):
        runner._measured(dict(
            elements=elements, nodes=elements, value=value,
            field="DISP", component="Magnitude", metric="displacement_max",
            source_file="unused.frd",
            metrics={"displacement": dict(
                elements=elements, value=value,
                field="DISP", component="Magnitude", metric="displacement_max",
            )},
        ))
    assert advanced == [1, 2]
    assert runner._level == 3
    assert finished == [("Completed", "All displacement metrics are within tolerance")]


def test_path_editor_picker_updates_highlight_and_persists_shortest_mesh_route(monkeypatch):
    app = QApplication.instance() or QApplication([])
    graph = (
        {1:(0.,0.,0.), 2:(1.,0.,0.), 3:(2.,0.,0.)},
        {1:{2:1.}, 2:{1:1.,3:1.}, 3:{2:1.}},
    )
    monkeypatch.setattr(paths, "mesh_graph", lambda _source, _loader: graph)

    class Viewport:
        def __init__(self):
            self.callback = None
            self.preview = ()
            self.cleared = 0
        def begin_result_path_pick(self, callback):
            self.callback = callback
            return lambda: setattr(self, "callback", None)
        def show_result_path_preview(self, _coordinates, nodes):
            self.preview = tuple(nodes)
        def clear_result_path_preview(self):
            self.cleared += 1
            self.preview = ()

    source = ResultSet(name="Analysis", source_file="unused.frd")
    viewport = Viewport()
    parent = QWidget()
    editor = paths.PathEditorDialog(source, None, None, parent, viewport=viewport)
    try:
        editor.pick.setChecked(True)
        viewport.callback(1)
        assert viewport.preview == (1,)
        viewport.callback(3)
        assert viewport.preview == (1, 2, 3)
        editor.default_x.setCurrentIndex(editor.default_x.findData("node_id"))
        editor._save()
        stored = stored_paths(source)
        assert len(stored) == 1
        assert stored[0].node_ids == (1, 2, 3)
        assert stored[0].default_x_axis == "node_id"
        assert viewport.preview == ()
        assert viewport.callback is None
    finally:
        editor.close()
        parent.close()
        app.processEvents()
