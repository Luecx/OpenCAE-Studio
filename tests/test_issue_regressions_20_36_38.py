"""Regression coverage for issues #20, #36, #38 and related UI/runtime fixes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_solver_selector_allows_extensionless_unix_executables():
    source = _source("opencae/ui/dialogs/solver_row.py")
    assert '"Executable files (*.exe);;All files (*)"' in source
    assert 'All files (*.*)' not in source


def test_standard_dialogs_and_reported_editors_have_real_minimum_geometry():
    layouts = _source("opencae/ui/templates/layouts.py")
    materials = _source("opencae/ui/dialogs/material_browser.py")
    loads = _source("opencae/ui/dialogs/load_common.py")
    steps = _source("opencae/ui/dialogs/step.py")

    assert "QLayout.SizeConstraint.SetMinimumSize" in layouts
    assert "self.setMinimumSize(720, 420)" in materials
    assert "self.table.setMinimumHeight(250)" in materials
    assert "self.setMinimumSize(760, 620)" in loads
    assert 'nonlinear = step.step_type == "Nonlinear Static"' in steps
    assert "self.setMinimumSize(760, 780 if nonlinear else 520)" in steps
    assert "tabs.setMinimumHeight(290)" in steps


def test_analysis_start_opens_live_monitor_with_job_scoped_stop():
    workflow = _source("opencae/controllers/job_manager_analysis.py")
    manager = _source("opencae/controllers/job_manager.py")
    monitor = _source("opencae/ui/monitors/analysis_job_monitor.py")

    assert workflow.index("manager.open_selected_monitor()") < workflow.index("runner.start()")
    assert "def stop_job(self, job_id)" in manager
    assert "stop_callback=lambda current=job.id: self.stop_job(current)" in manager
    assert "self.stop_button = QPushButton(\"Stop\")" in monitor
    assert "callback()" in monitor


def test_job_runtime_guard_ignores_detached_nonpersistent_backreferences():
    manager = _source("opencae/controllers/job_manager.py")

    assert 'field_info.metadata.get("serialize", True) is False' in manager
    assert "Job runtime update attempted to change non-runtime field" in manager


def test_cad_face_highlight_cannot_expose_render_tessellation_as_mesh():
    geometry = _source("opencae/ui/viewport/pyvista_geometry.py")

    assert "prop.SetEdgeVisibility(False)" in geometry
    assert 'getattr(prop, "SetEdgeOpacity", None)' in geometry
    assert "set_edge_opacity(0.0)" in geometry


def test_new_models_imports_and_results_request_initial_framing():
    project = _source("opencae/controllers/project_controller.py")
    lifecycle = _source("opencae/controllers/part/lifecycle.py")
    results = _source("opencae/ui/viewport/solution_scene.py")

    assert "self._fit_loaded_content()" in project
    assert "viewport.request_refresh(fit=True)" in project
    assert lifecycle.count("self._fit_loaded_content()") >= 2
    assert "viewport.request_refresh(fit=True)" in lifecycle
    assert "fit_on_load = identity != previous_identity or scene.result_actor is None" in results
    assert "if fit_on_load or camera is None:" in results
    assert "scene.owner.plotter.reset_camera()" in results
