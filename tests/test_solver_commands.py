import unittest
from pathlib import Path

from opencae.solvers.abaqus import AbaqusAdapter
from opencae.solvers.calculix import CalculiXAdapter
from opencae.solvers.femaster import FEMasterAdapter


class SolverCommandTest(unittest.TestCase):
    def test_commands(self):
        deck = Path("C:/job/Job-1.inp"); output = Path("C:/job/Job-1")
        self.assertEqual(["femaster.exe", str(deck), "--output", str(output)], FEMasterAdapter().build_command("femaster.exe", deck, output))
        self.assertEqual(["ccx.exe", "-i", "Job-1"], CalculiXAdapter().build_command("ccx.exe", deck, output))
        self.assertIn("job=Job-1", AbaqusAdapter().build_command("abaqus.bat", deck, output))


if __name__ == "__main__": unittest.main()
