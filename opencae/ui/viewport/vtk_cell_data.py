from __future__ import annotations

import numpy as np


def cell_array(grid, name: str) -> np.ndarray:
    """Read VTK cell data without constructing PyVista DataSetAttributes.

    Direct VTK access avoids a PyVista recursion failure that can occur when a
    grid is replaced while a modeless preview callback is still pending.
    """
    if grid is None:
        return np.asarray([], dtype=np.int64)
    try:
        data = grid.GetCellData()
        array = data.GetArray(name) if data is not None else None
    except (AttributeError, RuntimeError, RecursionError):
        return np.asarray([], dtype=np.int64)
    if array is None:
        return np.asarray([], dtype=np.int64)
    try:
        from vtkmodules.util.numpy_support import vtk_to_numpy
        return np.asarray(vtk_to_numpy(array))
    except (ImportError, AttributeError, TypeError, RuntimeError, RecursionError):
        try:
            return np.asarray([array.GetValue(index) for index in range(array.GetNumberOfTuples())])
        except (AttributeError, RuntimeError, RecursionError):
            return np.asarray([], dtype=np.int64)
