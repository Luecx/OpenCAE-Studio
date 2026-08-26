from __future__ import annotations

from opencae.model.core import SolverName

from .base import SolverAdapter


class GenericAdapter(SolverAdapter):
    name = "Generic"

    def write_deck_text(self, project, analysis, profile=None):
        """Render the generic diagnostic deck."""
        return project.render_deck(SolverName.GENERIC, analysis)
