"""Regression coverage for nonlinear Step UI and solver lowering."""

from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QApplication

from opencae.model.core import DeckWriter
from opencae.model.entities.analysis import AnalysisStep
from opencae.solvers.femaster_dsl.emitters.loadcase import write_step
from opencae.ui.deck_format_manager.template_catalog import TEMPLATE_SPECS
from opencae.ui.deck_format_manager.tree_catalog import TREE_SPEC
from opencae.ui.dialogs.step import StepDialog


class _Context:
    def __init__(self, solver="Abaqus"):
        self.analysis = SimpleNamespace(solver=solver)

    @staticmethod
    def solver_name(_entity, name):
        return name

    @staticmethod
    def resolve(_ref):
        return None

    @staticmethod
    def current_name(ref):
        return ref.entity_id


class _SemanticWriter:
    def __init__(self):
        self.commands = []

    def command(self, name, data, *, flags=(), keywords=None, record_key=""):
        self.commands.append(
            (name, tuple(data), tuple(flags), dict(keywords or {}), record_key)
        )


def _tree_node(key, nodes=TREE_SPEC):
    for node in nodes:
        if node.get("key") == key:
            return node
        found = _tree_node(key, tuple(node.get("children", ())))
        if found is not None:
            return found
    return None


def test_nonlinear_step_dialog_exposes_load_and_path_control_pages():
    app = QApplication.instance() or QApplication([])
    step = AnalysisStep(
        name="NL",
        step_type="Nonlinear Static",
        time_period=2.5,
        settings={
            "control": "PATH",
            "max_increments": 350,
            "initial_arc_length": 0.02,
            "minimum_arc_length": 1.0e-6,
            "maximum_arc_length": 0.08,
            "arc_length_psi": 0.75,
        },
    )
    dialog = StepDialog(step, [], [])
    try:
        assert dialog.nonlinear_control.currentData() == "PATH"
        assert dialog.control_stack.currentIndex() == 1
        assert dialog.max_increments.value() == 350
        values = dialog.values()
        assert values["settings"]["control"] == "PATH"
        assert values["settings"]["initial_arc_length"] == pytest.approx(0.02)
        assert values["settings"]["arc_length_psi"] == pytest.approx(0.75)

        dialog.nonlinear_control.setCurrentIndex(
            dialog.nonlinear_control.findData("LOAD")
        )
        dialog.time_period.setValue(4.0)
        dialog.initial_increment.setValue(0.2)
        values = dialog.values()
        assert dialog.control_stack.currentIndex() == 0
        assert values["time_period"] == pytest.approx(4.0)
        assert values["settings"]["control"] == "LOAD"
        assert values["settings"]["initial_increment"] == pytest.approx(0.2)
    finally:
        dialog.deleteLater()
        app.processEvents()


def test_abaqus_nonlinear_load_control_emits_increment_settings_directly_after_step():
    step = AnalysisStep(
        name="NL Load",
        step_type="Nonlinear Static",
        time_period=2.0,
        settings={
            "control": "LOAD",
            "max_increments": 240,
            "initial_increment": 0.05,
            "minimum_increment": 1.0e-7,
            "maximum_increment": 0.2,
            "adaptive": True,
        },
    )
    writer = DeckWriter()
    step.write_abaqus(writer, _Context("Abaqus"))
    lines = writer.text().splitlines()
    assert lines[0] == "*STEP, NAME=NL Load, NLGEOM=YES, INC=240"
    assert lines[1] == "*STATIC"
    assert lines[2] == "0.05, 2, 1e-07, 0.2"
    assert lines[-1] == "*END STEP"


def test_abaqus_path_control_emits_riks_arc_length_settings():
    step = AnalysisStep(
        name="Snap Through",
        step_type="Nonlinear Static",
        settings={
            "control": "PATH",
            "max_increments": 500,
            "initial_arc_length": 0.01,
            "total_arc_length": 1.5,
            "minimum_arc_length": 1.0e-8,
            "maximum_arc_length": 0.04,
        },
    )
    writer = DeckWriter()
    step.write_abaqus(writer, _Context("Abaqus"))
    text = writer.text()
    assert "*STATIC, RIKS" in text
    assert "0.01, 1.5, 1e-08, 0.04" in text


def test_calculix_rejects_path_control_instead_of_writing_invalid_riks_syntax():
    step = AnalysisStep(
        name="Unsupported Path",
        step_type="Nonlinear Static",
        settings={"control": "PATH"},
    )
    with pytest.raises(ValueError, match="CalculiX.*Riks"):
        step.write_abaqus(DeckWriter(), _Context("CalculiX"))


def test_femaster_nonlinear_emitter_uses_portable_keyword_surface():
    step = AnalysisStep(
        name="NL",
        step_type="Nonlinear Static",
        settings={
            "control": "PATH",
            "max_increments": 300,
            "initial_arc_length": 0.02,
            "minimum_arc_length": 1.0e-6,
            "maximum_arc_length": 0.08,
            "arc_length_psi": 0.7,
            "growth_factor": 1.8,
            "cutback_factor": 0.4,
            "fast_iterations": 5,
            "slow_iterations": 11,
            "maximum_cutbacks": 16,
            "regularize_zero_rows": True,
            "regularization_alpha": 2.0e-4,
        },
    )
    writer = _SemanticWriter()
    write_step(step, writer, _Context("FEMaster"))
    nonlinear = next(item for item in writer.commands if item[0] == "NONLINEAR")
    keywords = nonlinear[3]
    assert keywords["CONTROL"] == "ARC_LENGTH"
    assert keywords["INITIAL_INCREMENT"] == pytest.approx(0.02)
    assert keywords["MINIMUM_INCREMENT"] == pytest.approx(1.0e-6)
    assert keywords["MAXIMUM_INCREMENT"] == pytest.approx(0.08)
    assert keywords["MAX_INCREMENTS"] == 300
    assert keywords["ARC_LENGTH_PSI"] == pytest.approx(0.7)
    assert keywords["REGULARIZE_ZERO_ROWS"] is True
    assert {
        "GROWTH_FACTOR",
        "CUTBACK_FACTOR",
        "FAST_ITERATIONS",
        "SLOW_ITERATIONS",
        "MAXIMUM_CUTBACKS",
        "REGULARIZATION_ALPHA",
    }.isdisjoint(keywords)


def test_deck_format_record_exposes_complete_nonlinear_semantic_controls():
    spec = TEMPLATE_SPECS["analysis.controls.nonlinear"]
    fields = {name for name, _description, _example in spec["fields"]}
    assert {
        "control",
        "max_increments",
        "initial_increment",
        "minimum_increment",
        "maximum_increment",
        "arc_length_psi",
        "adaptive",
        "growth_factor",
        "cutback_factor",
        "fast_iterations",
        "slow_iterations",
        "maximum_cutbacks",
        "max_iterations",
        "tolerance",
        "regularize_zero_rows",
        "regularization_alpha",
    } <= fields
    template = spec["template"]
    assert all(
        keyword not in template
        for keyword in (
            "GROWTH_FACTOR",
            "CUTBACK_FACTOR",
            "FAST_ITERATIONS",
            "SLOW_ITERATIONS",
            "MAXIMUM_CUTBACKS",
            "REGULARIZATION_ALPHA",
        )
    )


def test_deck_format_nonlinear_controls_are_nested_under_nonlinear_static():
    nonlinear = _tree_node("analysis.nonlinear_static")
    assert nonlinear is not None
    child_keys = [child["key"] for child in nonlinear["children"]]
    assert child_keys == [
        "analysis.loadcases.nonlinear_static",
        "analysis.controls.nonlinear",
    ]

    numerical = _tree_node("analysis.controls")
    assert numerical is not None
    assert "analysis.controls.nonlinear" not in {
        child["key"] for child in numerical["children"]
    }
