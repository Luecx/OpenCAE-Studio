from __future__ import annotations

import shlex
from abc import ABC, abstractmethod
from pathlib import Path

from opencae.model.analysis import Analysis
from opencae.model.project import Project


class SolverAdapter(ABC):
    """Translate one Analysis into an input deck and solver process command."""

    name: str = "Generic"
    deck_extension: str = ".inp"

    @abstractmethod
    def write_deck_text(
        self,
        project: Project,
        analysis: Analysis,
        profile=None,
    ) -> str:
        """Return one complete solver input deck, optionally using a deck profile."""
        raise NotImplementedError

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
            *shlex.split(extra_arguments, posix=False),
        ]

    def result_candidates(self, output_base: Path) -> list[Path]:
        return []
