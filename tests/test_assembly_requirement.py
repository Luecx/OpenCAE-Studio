import unittest

from opencae.model.entities.analysis.analysis import Analysis
from opencae.model.entities.project import Project
from opencae.solvers.femaster import FEMasterAdapter


class AssemblyRequirementTest(unittest.TestCase):
    def test_export_requires_active_instance(self):
        project = Project(name='EMPTY')
        analysis = Analysis(name='STATIC', analysis_type='Linear Static')
        project.analyses.append(analysis)
        with self.assertRaisesRegex(ValueError, 'active assembly instance'):
            FEMasterAdapter().write_deck_text(project, analysis)


if __name__ == '__main__':
    unittest.main()
