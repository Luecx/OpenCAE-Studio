from __future__ import annotations

import shlex
from pathlib import Path

from opencae.model.core import SolverName
from .base import SolverAdapter


class CalculiXAdapter(SolverAdapter):
    name = "CalculiX"
    accepted_deck_formats = ("Abaqus",)
    custom_profile_formats = ()

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

    def postprocess_results(self, project, output_base: Path) -> None:
        """Expose CalculiX's input-stem FRD under OpenCAE's stable result name.

        ccx -i analysis writes analysis.frd, whereas the generic Analysis runner
        publishes results.frd. Do not require the user to rename the output.
        """
        from shutil import copy2

        del project
        published = output_base.with_suffix(".frd")
        source = output_base.with_name("analysis").with_suffix(".frd")
        if source.is_file() and source.resolve() != published.resolve():
            copy2(source, published)

