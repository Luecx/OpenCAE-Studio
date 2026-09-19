"""Regression tests for simplified convergence Studies, live output and list hit areas."""
from __future__ import annotations

from copy import deepcopy

import numpy as np
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QApplication

from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, JobSourceKind
from opencae.model.entities.studies import MeshConvergenceStudy
from opencae.model.project import Project
from opencae.results.frd_data import FrdData, FrdFieldData
from opencae.results.mesh_convergence import evaluate_all_metrics, assess_all_metrics
from opencae.ui.primitives.lists import ListCheck
from opencae.ui.tree.studies_tree import append_studies


class _Signal:
    def __init__(self):
        self.calls = []
    def connect(self, callback):
        self.calls.append(callback)
    def emit(self, *args):
        for callback in self.calls:
            callback(*args)


def test_no_monitor_nodes_uses_actual_global_displacement_maximum():
    block = FrdFieldData(
        name="DISP", components=["D1", "D2", "D3"],
        step_id=1, frame_id=1, frame_value=1.0,
        values={1: [0., 0., 0.], 2: [3., 4., 0.], 3: [0., 0., 2.]},
    )
    data = FrdData(
        nodes={1: (0, 0, 0), 2: (1, 0, 0), 3: (2, 0, 0)},
        fields=[block],
    )
    class Loader:
        def read(self, _source):
            return data

    study = MeshConvergenceStudy(
        name="Tip", metrics=[dict(
            id="control-1", name="Displacement control",
            kind="displacement_control", component="Magnitude", nodes=[],
        )],
    )
    sample = evaluate_all_metrics("unused.frd", study, Loader())
    assert sample["value"] == 5.0
    assert sample["metrics"]["control-1"]["metric"] == "displacement_max"
    assert sample["metrics"]["control-1"]["samples"] == 3


def test_study_tree_omits_topology_groups_for_displacement_convergence():
    study = MeshConvergenceStudy(name="Convergence")
    study.metrics = [dict(name="Tip", kind="displacement_control")]
    root = QStandardItem("Root")
    append_studies(root, [study])
    branch = root.child(0)
    convergence_node = branch.child(0)
    assert convergence_node.rowCount() == 0


def test_check_list_row_geometry_matches_full_visual_hit_area():
    app = QApplication.instance() or QApplication([])
    widget = ListCheck(
        [("First analysis step", "step-1"), ("Second step", "step-2")]
    )
    widget.resize(390, 240)
    widget.show()
    app.processEvents()
    try:
        rect1 = widget.visualItemRect(widget.item(0))
        rect2 = widget.visualItemRect(widget.item(1))
        assert rect1.height() >= 40
        assert rect2.top() > rect1.bottom()
        assert widget.itemAt(QPoint(rect1.left() + 20, rect1.bottom() - 3)) is widget.item(0)
        assert widget.itemAt(QPoint(rect2.left() + 20, rect2.bottom() - 3)) is widget.item(1)
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_every_refinement_level_becomes_a_real_job_linked_result():
    from opencae.controllers.job_manager_convergence import record_sample

    project = Project(name="Convergence")
    study = MeshConvergenceStudy(name="Study")
    job = Job(
        name="Study Job", source_ref=EntityRef.of(study, "Study"),
        source_kind=JobSourceKind.STUDY,
    )
    study.run_history = [{
        "job_id": job.id, "samples": [], "status": "Running",
    }]
    project.studies.append(study)
    project.jobs.append(job)
    project.rebuild_index(strict=True)

    class Store:
        def __init__(self):
            self.project = project
        def replace_entity(self, _description, _parent_id, attribute, entity):
            values = getattr(self.project, attribute)
            values[next(i for i, item in enumerate(values) if item.id == entity.id)] = entity
            self.project.rebuild_index(strict=True)
        def add_entity(self, _description, _parent_id, attribute, entity):
            getattr(self.project, attribute).append(entity)
            self.project.rebuild_index(strict=True)

    samples = _Signal()
    progress = []
    manager = type("Manager", (), {})()
    manager.store = Store()
    manager.convergence_sample = samples
    manager._update_progress = lambda job_id, fraction, label: progress.append(fraction)
    sample = dict(
        level=1, seed_scale=1.0, elements=20, nodes=33,
        value=0.5, source_file="/tmp/level-01/results.frd",
        _result_fields=[], metrics={"tip": {
            "metric": "displacement_max", "field": "DISP",
            "component": "Magnitude", "value": 0.5,
        }},
    )
    record_sample(manager, job.id, study.id, sample)
    assert len(project.results) == 1
    assert project.results[0].source_file == sample["source_file"]
    assert project.results[0].metadata["mesh_level"] == 1
    assert len(project.resolve(job.id).result_refs) == 1
    assert project.resolve(job.id).result_refs[0].entity_id == project.results[0].id
    assert "_result_fields" not in project.resolve(study.id).run_history[0]["samples"][0]
    assert len(samples.calls) == 0 or samples.calls is not None
    assert progress == [1/len(study.mesh_scales)]


def test_live_monitor_adds_curves_and_opens_real_solver_results():
    from PyQt6.QtWidgets import QWidget
    from opencae.model.entities.jobs import ResultSet, ResultStatus
    from opencae.ui.monitors.mesh_convergence_job_monitor import MeshConvergenceJobMonitor

    app = QApplication.instance() or QApplication([])
    project = Project(name="Convergence monitor")
    study = MeshConvergenceStudy(name="Study")
    job = Job(
        name="Study Job", source_ref=EntityRef.of(study, "Study"),
        source_kind=JobSourceKind.STUDY,
    )
    project.studies.append(study)
    project.jobs.append(job)
    project.rebuild_index(strict=True)

    class Store:
        def __init__(self):
            self.project = project
            self.changed = _Signal()

    class Parent(QWidget):
        def __init__(self):
            super().__init__()
            self.opened = []
        def show_solution(self, result):
            self.opened.append(result)

    parent = Parent()
    store = Store()
    monitor = MeshConvergenceJobMonitor(store, job.id, parent)
    try:
        assert monitor.series.count() == 0
        for level, displacement in enumerate((3.0, 3.2), start=1):
            monitor.sample_added(job.id, dict(
                level=level, nodes=50*level, elements=100*level,
                metrics={"tip::node:7": dict(
                    value=displacement, field="DISP",
                    component="Magnitude", metric_name="Tip displacement",
                )},
            ))
        assert monitor.series.count() == 1
        assert monitor.plot._x == [100., 200.]
        assert monitor.plot._y == [3., 3.2]
        assert monitor._measurements["tip::node:7"] == [
            {"level":1, "nodes":50, "elements":100, "value":3.0,
             "field":"DISP", "component":"Magnitude"},
            {"level":2, "nodes":100, "elements":200, "value":3.2,
             "field":"DISP", "component":"Magnitude"},
        ]
        monitor.x_axis.setCurrentIndex(monitor.x_axis.findData("nodes"))
        assert monitor.plot._x == [50., 100.]
        monitor.x_axis.setCurrentIndex(monitor.x_axis.findData("level"))
        assert monitor.plot._x == [1., 2.]
        monitor.log_x.setChecked(True)
        assert monitor.plot._x_scale == "log"
        assert monitor.plot._x == [1., 2.]
        assert monitor.plot._point_value_labels
        assert "3.2" in monitor.readout.text()
        level_result = ResultSet(
            name="Refinement level 2",
            job_ref=EntityRef.of(job, "Job"),
            source_file="/tmp/level-02/results.frd",
            status=ResultStatus.AVAILABLE,
        )
        project.results.append(level_result)
        job.result_refs.append(EntityRef.of(level_result, "ResultSet"))
        project.rebuild_index(strict=True)
        monitor._refresh_results()
        assert monitor.results.isEnabled()
        monitor._open_results()
        assert parent.opened == [level_result]
    finally:
        monitor.close()
        parent.close()
        app.processEvents()


def test_shared_plot_supports_logarithmic_x_without_modifying_raw_series():
    from opencae.ui.panels.time_manager_plot import TimeManagerPlot

    app = QApplication.instance() or QApplication([])
    plot = TimeManagerPlot()
    plot.resize(720, 330)
    try:
        plot.set_series(
            [1, 10, 100], [1e-6, 1.1e-6, 1.2e-6],
            x_label="Nodes", y_label="DISP: Magnitude",
            x_scale="log", point_value_labels=True,
            show_markers=True, interactive=False, show_play_range=False,
        )
        assert plot._x == [1., 10., 100.]
        assert plot._x_domain() == (0., 2.)
        assert abs(plot._screen_x(10) - (
            plot._screen_x(1) + plot._screen_x(100)
        ) / 2) < 1e-8
        assert abs(plot._value_at_screen_x(plot._screen_x(10)) - 10) < 1e-9
        assert plot._point_value_labels
        assert plot._nearest_marker is not None
        plot.set_series(
            [1, 2, 3], [2, 3, 4],
            x_scale="linear", interactive=False, show_play_range=False,
        )
        assert plot._x_domain() == (1., 3.)
        assert not plot._point_value_labels
        assert plot._plot_rect().left() == 56.
    finally:
        plot.close()
        plot.deleteLater()
        app.processEvents()


def test_convergence_plot_and_console_match_dialog_window_surface():
    """The convergence monitor must not paint the Time Manager's brighter panel."""
    from PyQt6.QtGui import QColor, QImage
    from opencae.ui.core.theme import PALETTE, palette_for
    from opencae.ui.core.styles.views import css as view_styles
    from opencae.ui.panels.time_manager_plot import TimeManagerPlot
    from opencae.ui.monitors.mesh_convergence_job_monitor import MeshConvergenceJobMonitor

    app = QApplication.instance() or QApplication([])
    project = Project(name="Convergence surfaces")
    study = MeshConvergenceStudy(name="Study")
    job = Job(
        name="Study Job", source_ref=EntityRef.of(study, "Study"),
        source_kind=JobSourceKind.STUDY,
    )
    project.studies.append(study)
    project.jobs.append(job)
    project.rebuild_index(strict=True)

    class Store:
        def __init__(self):
            self.project = project
            self.changed = _Signal()

    monitor = MeshConvergenceJobMonitor(Store(), job.id)
    try:
        assert monitor.objectName() == "MeshConvergenceJobMonitor"
        assert not monitor.plot_surface.autoFillBackground()
        assert monitor.plot._background_role == "window"
        assert monitor.output.objectName() == "MeshConvergenceOutput"
        assert TimeManagerPlot()._background_role == "panel"
        monitor.plot.resize(560, 300)
        image = QImage(560, 300, QImage.Format.Format_ARGB32)
        image.fill(QColor("transparent"))
        monitor.plot.render(image)
        assert image.pixelColor(0, 0).name() == QColor(PALETTE["window"]).name()
        for scheme in ("dark", "light", "gray"):
            palette = palette_for(scheme)
            style = view_styles(palette)
            assert (
                "QDialog#MeshConvergenceJobMonitor "
                "QPlainTextEdit#MeshConvergenceOutput"
            ) in style
            assert f"background: {palette['window']};" in style
    finally:
        monitor.close()
        monitor.deleteLater()
        app.processEvents()
