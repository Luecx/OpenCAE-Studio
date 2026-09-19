"""Physical-coordinate and measure-weighted refinement metrics.

Evaluate primitive tensor/vector components before deriving Mises/magnitude.
Nodal maxima are diagnostics, never proof of mesh convergence.
"""
from __future__ import annotations
from math import isfinite
import numpy as np
from opencae.results.derived_fields import component_values
from opencae.results.frd_loader import FrdLoader

METRICS = {
    "probe": "Fixed-position probe",
    "weighted_rms": "Measure-weighted RMS",
    "weighted_p95": "Measure-weighted 95th percentile",
    "nodal_max": "Nodal maximum (diagnostic only)",
}

def _primitive_scalar(components, rows, component):
    result = component_values(components, np.asarray(rows, dtype=float), component)
    if len(result) != len(rows):
        raise ValueError(f"Unavailable field component: {component}")
    return np.asarray(result, dtype=float)

def _block(loader, source, study):
    blocks = [b for b in loader.read(source).fields
              if b.name == study.field_name and int(b.step_id) == study.step_id]
    if not blocks:
        raise ValueError(f"No {study.field_name} data in Step {study.step_id}")
    return max(blocks, key=lambda b: (b.frame_id, b.block_index))

def evaluate_result(source, study, loader=None):
    """Measure a complete FRD result at a common physical coordinate/region."""
    import pyvista as pv
    loader = loader or FrdLoader()
    data = loader.read(source)
    block = _block(loader, source, study)
    grid = loader.pyvista_grid(source, block.step_id, block.frame_id)
    names = [f"{block.name}:{c}" for c in block.components]
    if any(name not in grid.point_data for name in names):
        raise ValueError(f"Primitive components missing for {block.name}")
    excluded = np.asarray(study.exclude_center, dtype=float)
    radius = float(study.exclude_radius)
    if study.metric == "probe":
        coordinate = np.asarray(study.probe_position, dtype=float)
        if radius > 0 and np.linalg.norm(coordinate - excluded) < radius:
            raise ValueError("Probe lies in the excluded singularity zone")
        points = pv.PolyData(coordinate.reshape(1, 3)).sample(grid)
        mask = np.asarray(points.point_data.get("vtkValidPointMask", [0]))
        if not mask[0]:
            raise ValueError("Probe point does not lie inside the FE mesh")
        rows = np.column_stack([points.point_data[name] for name in names])
        scalar = _primitive_scalar(block.components, rows, study.component)
        value, sample_count = float(scalar[0]), 1
    elif study.metric == "nodal_max":
        node_ids = data.node_order()
        rows = np.full((len(node_ids), len(block.components)), np.nan)
        for i, tag in enumerate(node_ids):
            value_row = block.values.get(tag)
            if value_row is not None:
                rows[i, :min(len(value_row), len(block.components))] = value_row[:len(block.components)]
        scalar = _primitive_scalar(block.components, rows, study.component)
        if radius > 0:
            coordinates = np.asarray([data.nodes[tag] for tag in node_ids])
            scalar[np.linalg.norm(coordinates - excluded, axis=1) < radius] = np.nan
        finite = scalar[np.isfinite(scalar)]
        if not len(finite):
            raise ValueError("No finite nodal samples remain")
        value, sample_count = float(np.max(finite)), len(finite)
    elif study.metric in {"weighted_rms", "weighted_p95"}:
        if not grid.n_cells:
            raise ValueError("Result grid contains no FE elements")
        centers = grid.cell_centers().points
        sizes = grid.compute_cell_sizes(length=True, area=True, volume=True)
        weights = np.maximum.reduce([
            np.asarray(sizes.cell_data[key], dtype=float)
            for key in ("Length", "Area", "Volume")
        ])
        if radius > 0:
            weights[np.linalg.norm(centers - excluded, axis=1) < radius] = 0.0
        points = pv.PolyData(centers).sample(grid)
        mask = np.asarray(points.point_data.get(
            "vtkValidPointMask", np.zeros(len(centers))), dtype=bool
        )
        rows = np.column_stack([points.point_data[name] for name in names])
        scalar = _primitive_scalar(block.components, rows, study.component)
        valid = mask & np.isfinite(scalar) & np.isfinite(weights) & (weights > 0)
        if not np.any(valid):
            raise ValueError("No finite cells outside the exclusion zone")
        values, measures = scalar[valid], weights[valid]
        if study.metric == "weighted_rms":
            value = float(np.sqrt(np.average(values * values, weights=measures)))
        else:
            order = np.argsort(values)
            cumulative = np.cumsum(measures[order])
            index = min(int(np.searchsorted(cumulative, cumulative[-1] * .95)),
                        len(order)-1)
            value = float(values[order[index]])
        sample_count = int(np.sum(valid))
    else:
        raise ValueError(f"Unknown refinement metric: {study.metric}")
    if not isfinite(value):
        raise ValueError("Refinement metric is non-finite")
    return dict(
        source_file=str(source), elements=len(data.elements), nodes=len(data.nodes),
        frame_id=int(block.frame_id), frame_value=float(block.frame_value),
        samples=sample_count, value=value, metric=study.metric,
        field=study.field_name, component=study.component,
    )

def assess_convergence(samples, tolerance, metric):
    """Conservatively qualify terminal relative changes, not exact FE error."""
    if not samples:
        return "No completed mesh refinements"
    if metric == "nodal_max":
        return "Diagnostic only: peak values may diverge near singularities"
    if len(samples) < 3:
        return "At least three completed refinement levels are required"
    counts = [int(s["elements"]) for s in samples]
    if any(b <= a for a, b in zip(counts, counts[1:])):
        return "Not assessed: element counts must increase strictly"
    values = [float(s["value"]) for s in samples]
    differences = [abs(b-a)/max(abs(a), abs(b), 1e-30)
                   for a,b in zip(values, values[1:])]
    if differences[-1] <= tolerance and differences[-2] <= tolerance:
        return "Terminal metric changes are within tolerance (not an FE error bound)"
    return "Not converged: terminal relative changes exceed tolerance"
