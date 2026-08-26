from __future__ import annotations

import shlex
from pathlib import Path

from opencae.model.core import SolverName
from .base import SolverAdapter


class CalculiXAdapter(SolverAdapter):
    name = "CalculiX"

    def write_deck_text(self, project, analysis, profile=None):
        """Render the native Abaqus-compatible CalculiX deck."""
        return project.render_deck(SolverName.ABAQUS, analysis)

    def build_command(
        self,
        executable: str,
        deck_path: Path,
        output_base: Path,
        extra_arguments: str = "",
    ) -> list[str]:
        return [
            executable,
            "-i",
            deck_path.stem,
            *shlex.split(extra_arguments, posix=False),
        ]

    def result_candidates(self, output_base: Path) -> list[Path]:
        return [output_base.with_suffix(".frd")]
