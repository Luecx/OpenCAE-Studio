from __future__ import annotations

import shlex
from pathlib import Path

from opencae.model.core import SolverName
from .base import SolverAdapter


class AbaqusAdapter(SolverAdapter):
    name = "Abaqus"

    def write_deck_text(self, project, analysis, profile=None):
        """Render the native Abaqus deck; custom Abaqus profiles are not wired yet."""
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
            f"job={output_base.name}",
            f"input={deck_path.name}",
            "interactive",
            *shlex.split(extra_arguments, posix=False),
        ]
