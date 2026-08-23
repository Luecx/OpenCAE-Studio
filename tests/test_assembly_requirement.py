"""Regression for the flat-deck requirement that an assembly occurrence exists."""

import unittest

from opencae.model.core import EntityRef
from opencae.model.entities.analysis.analysis import Analysis
from opencae.model.entities.analysis.step import AnalysisStep
from opencae.model.entities.project import Project
from opencae.solvers.femaster import FEMasterAdapter


class AssemblyRequirementTest(unittest.TestCase):
    """Verify export reaches the assembly-occurrence precondition with a valid analysis."""

    def test_export_requires_active_instance(self):
        """A valid step without any model instance fails on the assembly requirement."""
        project = Project(name="EMPTY")
        step = AnalysisStep(name="STEP", step_type="Linear Static")
        analysis = Analysis(name="STATIC", analysis_type="Linear Static")
        analysis.bind_steps([step])
        project.steps.append(step)
        project.analyses.append(analysis)
        project.rebuild_index(strict=True)
        self.assertEqual(analysis.step_refs, [EntityRef.of(step, "AnalysisStep")])
        with self.assertRaisesRegex(ValueError, "active assembly instance"):
            FEMasterAdapter().write_deck_text(project, analysis)


if __name__ == "__main__":
    unittest.main()
