"""Regression coverage for Analysis-owned solver/deck-profile selection."""

from __future__ import annotations

from dataclasses import replace

from PyQt6.QtWidgets import QApplication

from opencae.deck_formats import DeckProfile
from opencae.deck_formats.selection import (
    builtin_profile_id,
    compatible_profile_names,
    normalized_profile_id,
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
        self.profile = DeckProfile("FEMaster Company", "FEMaster")
        self.deck_profiles = {self.profile.name: self.profile.to_dict()}


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
    assert normalized_profile_id(
        settings,
        adapters["CalculiX"],
        settings.profile.profile_id,
    ) == builtin_profile_id("Abaqus")


def test_custom_femaster_profile_resolves_but_builtin_is_native():
    settings = _Settings()
    adapter = available_solvers()["FEMaster"]

    custom = resolve_profile(settings, adapter, settings.profile.profile_id)
    assert custom is not None
    assert custom.name == "FEMaster Company"
    assert resolve_profile(settings, adapter, builtin_profile_id("FEMaster")) is None


def test_custom_profile_rename_does_not_change_analysis_identity():
    settings = _Settings()
    profile_id = settings.profile.profile_id
    renamed = replace(settings.profile, name="Renamed FEMaster Profile")
    settings.deck_profiles = {renamed.name: renamed.to_dict()}

    custom = resolve_profile(settings, available_solvers()["FEMaster"], profile_id)
    assert custom is not None
    assert custom.profile_id == profile_id
    assert custom.name == "Renamed FEMaster Profile"


def test_run_dialog_resets_profile_to_solver_builtin_on_solver_change():
    app = _app()
    settings = _Settings()
    adapters = available_solvers()
    analysis = Analysis(
        name="Analysis-1",
        solver="FEMaster",
        deck_profile_id=settings.profile.profile_id,
    )
    dialog = RunAnalysisDialog(analysis, adapters, settings)
    app.processEvents()

    assert dialog.deck_profile.currentText() == "FEMaster Company"
    dialog.solver.setCurrentText("Abaqus")
    app.processEvents()
    assert dialog.deck_profile.currentText() == "Abaqus"
    assert dialog.deck_profile.currentData() == builtin_profile_id("Abaqus")
    assert dialog.deck_profile.count() == 1

    dialog.solver.setCurrentText("FEMaster")
    app.processEvents()
    assert dialog.deck_profile.currentText() == "FEMaster"
    assert dialog.values() == ("FEMaster", builtin_profile_id("FEMaster"))
    dialog.close()


def test_analysis_dialog_persists_solver_and_profile_selection():
    app = _app()
    settings = _Settings()
    adapters = available_solvers()
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(
        name="Analysis-1",
        solver="FEMaster",
        deck_profile_id=settings.profile.profile_id,
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
    assert candidate.deck_profile_id == builtin_profile_id("Abaqus")
    dialog.close()


def test_analysis_deck_profile_id_roundtrips_with_project(project_factory):
    data = project_factory(include_constraints=False)
    data["analysis"].solver = "FEMaster"
    data["analysis"].deck_profile_id = "custom:stable-test-profile"

    restored = project_from_dict(project_to_dict(data["project"]))
    analysis = restored.resolve(data["analysis"].id)

    assert analysis.solver == "FEMaster"
    assert analysis.deck_profile_id == "custom:stable-test-profile"
