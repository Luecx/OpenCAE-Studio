from __future__ import annotations

import shlex
from pathlib import Path

from opencae.deck_formats import DeckProfile, ProfileCommandWriter
from opencae.model.core import ExportContext, SolverName
from opencae.model.validation import validate_project
from opencae.solvers.femaster_dsl import require_valid
from .base import SolverAdapter


class FEMasterAdapter(SolverAdapter):
    """Render and execute FEMaster input decks."""

    name = "FEMaster"

    def write_deck_text(self, project, analysis, profile=None):
        """Render a validated deck through the built-in or selected custom profile."""
        errors = validate_project(project, analysis=analysis)
        if errors:
            raise ValueError("Invalid project:\n- " + "\n- ".join(errors))

        deck_profile = _profile(profile)
        if deck_profile is None:
            text = project.render_deck(SolverName.FEMASTER, analysis)
        else:
            from opencae.solvers.femaster_dsl.emitters import write_project

            writer = ProfileCommandWriter(deck_profile)
            context = ExportContext(project, analysis)
            writer.comment("OpenCAE Studio generated FEMaster deck")
            write_project(project, writer, context)
            text = writer.text()

        require_valid(text)
        return text

    def build_command(
        self,
        executable: str,
        deck_path: Path,
        output_base: Path,
        extra_arguments: str = "",
    ) -> list[str]:
        return [
            executable,
            str(deck_path),
            "--output",
            str(output_base),
            *shlex.split(extra_arguments, posix=False),
        ]

    def result_candidates(self, output_base: Path) -> list[Path]:
        return [
            output_base.with_suffix(".frd"),
            output_base.with_suffix(".res"),
        ]


def _profile(value) -> DeckProfile | None:
    """Normalize a persisted profile snapshot for adapter callers."""
    if value is None:
        return None
    if isinstance(value, DeckProfile):
        profile = value
    elif isinstance(value, dict):
        profile = DeckProfile.from_dict(value)
    else:
        raise TypeError("Deck profile must be DeckProfile, mapping, or None")
    if profile is None:
        raise ValueError("Invalid deck profile")
    if profile.format_name != "FEMaster":
        raise ValueError(
            f"Deck profile {profile.name!r} targets {profile.format_name}, not FEMaster"
        )
    return profile
