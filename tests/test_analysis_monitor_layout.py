"""Regression coverage for roomy dialogs and the structured Analysis monitor."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_standard_editor_dialogs_use_a_roomier_shared_width():
    templates = _source("opencae/ui/templates/dialogs.py")
    forms = _source("opencae/ui/core/form_dialog.py")
    named = _source("opencae/ui/core/named_entity_dialog.py")
    cad = _source("opencae/ui/dialogs/import_geometry.py")
    run = _source("opencae/ui/dialogs/run_analysis.py")
    entity = _source("opencae/ui/dialogs/entity_editor.py")
    reorder = _source("opencae/ui/dialogs/step_reorder.py")
    visibility = _source("opencae/ui/dialogs/visibility.py")

    assert "DEFAULT_DIALOG_WIDTH = 640" in templates
    assert "width: int = DEFAULT_DIALOG_WIDTH" in forms
    assert "width=DEFAULT_DIALOG_WIDTH" in named
    assert "width=720" in cad
    assert "self.setMinimumWidth(680)" in run
    assert "self.resize(700" not in run
    assert "self.setMinimumWidth(640)" in entity
    assert "self.setMinimumSize(640, 440)" in reorder
    assert "self.setMinimumSize(640, 520)" in visibility


def test_analysis_monitor_places_monospace_output_left_and_runtime_details_right():
    monitor = _source("opencae/ui/monitors/analysis_job_monitor.py")
    output_view = _source("opencae/ui/core/widgets/monospace_output_view.py")
    manager = _source("opencae/controllers/job_manager.py")

    assert "QSplitter(Qt.Orientation.Horizontal" in monitor
    assert 'SectionHeading("Solver Output")' in monitor
    assert "self.output = MonospaceOutputView" in monitor
    assert 'SectionHeading("Runtime Details")' in monitor
    assert '("step", "Step")' in monitor
    assert '("procedure", "Procedure")' in monitor
    assert '("frame", "Frame")' in monitor
    assert '("iteration", "Iteration")' in monitor
    assert '("time_frequency", "Time / Frequency")' in monitor
    assert 'SectionHeading("Step / Post Checks")' in monitor
    assert "self.post_checks.setColumnCount(3)" in monitor
    assert "def set_runtime_state(" in monitor
    assert "def set_runtime_details(" in monitor
    assert "def set_post_checks(" in monitor
    assert "QFontDatabase.SystemFont.FixedFont" in output_view
    assert "analysis_runtime_changed = pyqtSignal(str, object, object)" in manager
    assert 'Path(directory) / "analysis_runtime.json"' in manager
    assert "_persist_analysis_runtime_snapshot" in manager
    assert "_load_analysis_runtime_snapshot" in manager


def test_femaster_monitor_probe_covers_every_native_loadcase_family():
    deck = _source("tests/fixtures/femaster/all_loadcases_monitor_probe.inp")
    expected = (
        "LINEARSTATIC",
        "NONLINEARSTATIC",
        "LINEARBUCKLING",
        "LINEARSTATICTOPO",
        "EIGENFREQ",
        "LINEARTRANSIENT",
        "LINEARHARMONIC",
    )

    assert deck.count("*LOADCASE, TYPE=") == len(expected)
    for loadcase_type in expected:
        assert f"*LOADCASE, TYPE={loadcase_type}" in deck

    assert "*NONLINEAR, CONTROL=LOAD" in deck
    assert "*NUMEIGENVALUES" in deck
    assert "*TOPODENSITY, FIELD=DENSITY_FIELD" in deck
    assert "*TIME\n0.0, 0.01, 0.002" in deck
    assert "*FREQUENCIES, SCALE=LINEAR" in deck
