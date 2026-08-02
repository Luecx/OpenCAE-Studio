from __future__ import annotations

import shlex
from pathlib import Path

from opencae.model.core import SolverName
from opencae.model.validation import validate_project
from opencae.solvers.femaster_dsl import require_valid
from .base import SolverAdapter


class FEMasterAdapter(SolverAdapter):
    name = "FEMaster"

    def write_deck_text(self, project, analysis):
        errors = validate_project(project)
        if errors:
            raise ValueError("Invalid project:\n- " + "\n- ".join(errors))
        text = project.render_deck(SolverName.FEMASTER, analysis)
        require_valid(text)
        return text

    def build_command(self, executable: str, deck_path: Path, output_base: Path, extra_arguments: str = "") -> list[str]:
        return [executable, str(deck_path), "--output", str(output_base), *shlex.split(extra_arguments, posix=False)]

    def result_candidates(self, output_base: Path) -> list[Path]:
        return [output_base.with_suffix(".frd"), output_base.with_suffix(".res")]
