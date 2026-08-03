import unittest

from opencae.solvers.femaster_dsl.catalog import ALL_COMMANDS


class FEMasterCatalogTest(unittest.TestCase):
    def test_documented_command_catalog(self):
        expected = {
            "MODEL", "NODE", "ELEMENT", "SURFACE", "NSET", "ELSET", "SFSET",
            "MATERIAL", "ELASTIC", "HYPERELASTIC", "DENSITY",
            "THERMALEXPANSION", "SOLIDSECTION", "SHELLSECTION",
            "BEAMSECTION", "TRUSSSECTION", "PROFILE", "POINTMASS", "FIELD",
            "ORIENTATION", "SUPPORT", "CLOAD", "DLOAD", "PLOAD", "VLOAD",
            "TLOAD", "INERTIALOAD", "AMPLITUDE", "COUPLING", "TIE",
            "CONNECTOR", "RBM", "LOADCASE", "END", "SUPPORTS", "LOADS",
            "SOLVER", "CONSTRAINTMETHOD", "NONLINEAR", "INERTIARELIEF",
            "REBALANCELOADS", "REQUESTSTIFFNESS", "REQUESTSTGEOM",
            "NUMEIGENVALUES", "SIGMA", "TOPODENSITY", "TOPOORIENT",
            "TOPOEXPONENT", "TIME", "NEWMARK", "DAMPING", "WRITEEVERY",
            "INITIALVELOCITY", "CONSTRAINTSUMMARY", "OVERVIEW",
        }
        self.assertEqual(expected, set(ALL_COMMANDS))


if __name__ == "__main__":
    unittest.main()
