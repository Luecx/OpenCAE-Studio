import unittest

import numpy as np

from opencae.ui.viewport.vtk_cell_data import cell_array


class _Array:
    def __init__(self, values): self.values = values
    def GetNumberOfTuples(self): return len(self.values)
    def GetValue(self, index): return self.values[index]


class _Data:
    def __init__(self, values): self.values = values
    def GetArray(self, name): return _Array(self.values) if name == "element_id" else None


class _Grid:
    def __init__(self, values): self.values = values
    def GetCellData(self): return _Data(self.values)


class _BrokenGrid:
    def GetCellData(self): raise RecursionError


class VtkCellDataTest(unittest.TestCase):
    def test_fallback_reads_values(self):
        self.assertTrue(np.array_equal(cell_array(_Grid([4, 8]), "element_id"), [4, 8]))

    def test_invalid_grid_is_safe(self):
        self.assertEqual(len(cell_array(_BrokenGrid(), "element_id")), 0)
        self.assertEqual(len(cell_array(None, "element_id")), 0)


if __name__ == "__main__": unittest.main()
