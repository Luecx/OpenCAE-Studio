"""Reads and enriches persisted topology density iteration states."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def load_density_state(path: str | Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Return physical density and optional solver element volumes from one state."""
    with np.load(Path(path), allow_pickle=False) as values:
        density = np.asarray(values["physical"], dtype=float).copy()
        volumes = (
            np.asarray(values["volumes"], dtype=float).copy()
            if "volumes" in values.files
            else None
        )
    if volumes is not None and volumes.shape != density.shape:
        volumes = None
    return density, volumes


def store_density_volumes(path: str | Path, volumes) -> None:
    """Atomically add solver element volumes to an existing density state."""
    target = Path(path)
    with np.load(target, allow_pickle=False) as values:
        state = {name: np.asarray(values[name]).copy() for name in values.files}
    volume_values = np.asarray(volumes, dtype=float).ravel()
    density_values = np.asarray(state["physical"], dtype=float).ravel()
    if volume_values.shape != density_values.shape:
        raise ValueError("Topology volumes do not match the density state")
    state["volumes"] = volume_values
    temporary = target.with_name(f"{target.stem}.updating.npz")
    try:
        np.savez_compressed(temporary, **state)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
