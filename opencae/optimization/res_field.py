"""Defines one parsed field from a FEMaster native result file."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ResField:
    """Field metadata and dense or indexed numeric values from a `.res` file."""

    name: str
    domain: str
    values: np.ndarray
    indices: np.ndarray | None = None
