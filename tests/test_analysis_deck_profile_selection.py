"""Regression coverage for Analysis-owned solver/deck-profile selection."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from opencae.deck_formats import DeckProfile
from opencae.deck_formats.selection import (
    compatible_profile_names,
    normalized_profile_name,
    resolve_profile,
)
from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.persistence.project_codec import project_from_dict, project_to_dict
from opencae.solvers.registry import available_solvers
from opencae.ui.dialogs.analysis_dialog import AnalysisDialog
from opencae.ui.dialogs.run_analysis import RunAnalysisDialog


class _Settings:
    """Small settings stand-in exposing persisted deck profiles."""

    def __init__(self):
        profile = DeckProfile("FEMaster Company", "FEMaster")
        self.deck_profiles = {profile.name: profile.to_dict()}


def _app():
    return QApplication.instance() or QApplication([])


def test_solver_capabilities_filter_profile_choices_and_defaults():
    settings = _Settings()
    adapters = available_solvers()

    assert compatible_profile_names(settings, adapters["FEMaster"]) == (
        "FEMaster",
        "FEMaster Company",
    )
    assert compatible_profile_names(settings, adapters["Abaqus"]) == ("Abaqus",)
    assert compatible_profile_names(settings, adapters["CalculiX"]) == ("Abaqus",)
    assert normalized_profile_name(settings, adapters["CalculiX"], "FEMaster") == "Abaqus"


def test_custom_femaster_profile_resolves_but_builtin_is_native():
    settings = _Settings()
    adapter = available_solvers()["FEMaster"]

    custom = resolve_profile(settings, adapter, "FEMaster Company")
    assert custom is not None
    assert custom.name == "FEMaster Company"
    assert resolve_profile(settings, adapter, "FEMaster") is None


def test_run_dialog_resets_profile_to_solver_builtin_on_solver_change():
    app = _app()
    settings = _Settings()
    adapters = available_solvers()
    analysis = Analysis(
        name="Analysis-1",
        solver="FEMaster",
        deck_profile="FEMaster Company",
    )
    dialog = RunAnalysisDialog(analysis, adapters, settings)
    app.processEvents()

    assert dialog.deck_profile.currentText() == "FEMaster Company"
    dialog.solver.setCurrentText("Abaqus")
    app.processEvents()
    assert dialog.deck_profile.currentText() == "Abaqus"
    assert dialog.deck_profile.count() == 1

    dialog.solver.setCurrentText("FEMaster")
    app.processEvents()
    assert dialog.deck_profile.currentText() == "FEMaster"
    assert dialog.values() == ("FEMaster", "FEMaster")
    dialog.close()


def test_analysis_dialog_persists_solver_and_profile_selection():
    app = _app()
    settings = _Settings()
    adapters = available_solvers()
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(
        name="Analysis-1",
        solver="FEMaster",
        deck_profile="FEMaster Company",
        step_refs=[EntityRef.of(step, "AnalysisStep")],
    )
    dialog = AnalysisDialog(
        analysis,
        [step],
        adapters,
        settings,
        existing_names=(),
    )
    app.processEvents()

    assert dialog.deck_profile.currentText() == "FEMaster Company"
    dialog.solver.setCurrentText("CalculiX")
    app.processEvents()
    assert dialog.deck_profile.currentText() == "Abaqus"
    candidate = dialog.result()
    assert candidate.solver == "CalculiX"
    assert candidate.deck_profile == "Abaqus"
    dialog.close()


def test_analysis_deck_profile_roundtrips_with_project(project_factory):
    data = project_factory(include_constraints=False)
    data["analysis"].solver = "FEMaster"
    data["analysis"].deck_profile = "FEMaster Company"

    restored = project_from_dict(project_to_dict(data["project"]))
    analysis = restored.resolve(data["analysis"].id)

    assert analysis.solver == "FEMaster"
    assert analysis.deck_profile == "FEMaster Company"
