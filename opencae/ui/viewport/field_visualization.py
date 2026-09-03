"""Build scalar field actors for tabular, formula, and file-backed fields."""

from __future__ import annotations

import math
import numpy as np
from opencae.ui.core.theme import PALETTE
from .scalar_bar import scalar_bar_args
from .safe_operations import remove_actor


def add_field(plotter, grid, snapshot, field):
    if grid is None: return None
    target = grid.copy(deep=True); location = field.location
    sample_points = target.cell_centers().points if location == "Element" else target.points
    identifiers = np.arange(1, len(sample_points) + 1)
    if location != "Element" and snapshot is not None: identifiers = snapshot.node_tags
    values = _field_values(field, sample_points, identifiers)
    if location == "Element": target.cell_data[field.name] = values
    else: target.point_data[field.name] = values
    for name in ("field-visualization", "generated-mesh", "generated-mesh-lines"):
        remove_actor(plotter, name)
    actor = plotter.add_mesh(target, scalars=field.name, cmap="turbo", n_colors=18, show_edges=True,
        edge_color=PALETTE["result_edge"], line_width=1.0, lighting=True, ambient=0.25,
        diffuse=0.72, scalar_bar_args=scalar_bar_args(field.name, plotter), name="field-visualization", render=False)
    plotter.render(); return actor


def _field_values(field, points, identifiers):
    count = len(points); components = max(1, int(field.components))
    if field.source_type == "Tabular":
        table = {str(row[0]): row[1:] for row in field.table if row}
        data = [_row_values(table.get(str(int(tag)), ()), components) for tag in identifiers]
    elif field.source_type == "Formula":
        data = [_formula_values(field.expression, point, components) for point in points]
    else:
        data = _file_values(field.file_path, identifiers, points, components, field.interpolation)
    array = np.asarray(data, dtype=float).reshape(count, components)
    return array[:, 0] if components == 1 else np.linalg.norm(array, axis=1)


def _row_values(values, components):
    result = []
    for index in range(components):
        try: result.append(float(values[index]))
        except (IndexError, TypeError, ValueError): result.append(0.0)
    return result


def _formula_values(expression, point, components):
    env = {"x": float(point[0]), "y": float(point[1]), "z": float(point[2]),
           "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "abs": abs,
           "pi": math.pi, "np": np}
    expressions = [value.strip() for value in expression.replace(";", ",").split(",") if value.strip()] or ["0.0"]
    result = []
    for index in range(components):
        try: result.append(float(eval(expressions[min(index, len(expressions) - 1)], {"__builtins__": {}}, env)))
        except (ArithmeticError, NameError, SyntaxError, TypeError, ValueError): result.append(0.0)
    return result


def _file_values(path, identifiers, points, components, interpolation):
    try:
        rows = np.genfromtxt(path, delimiter=",", dtype=float, ndmin=2)
        if rows.shape[1] >= components + 3:
            sources = rows[:, :3]; values = rows[:, 3:3 + components]
            return [_interpolate(sources, values, point, interpolation) for point in points]
        table = {str(int(row[0])): row[1:] for row in rows if len(row)}
        return [_row_values(table.get(str(int(tag)), ()), components) for tag in identifiers]
    except (OSError, TypeError, ValueError):
        return np.zeros((len(identifiers), components), dtype=float)


def _interpolate(sources, values, point, method):
    distances = np.linalg.norm(sources - np.asarray(point, dtype=float), axis=1)
    nearest = int(np.argmin(distances))
    if method == "Nearest" or distances[nearest] < 1.0e-12:
        return values[nearest]
    power = 3.0 if method == "Cubic" else 1.0
    weights = 1.0 / np.maximum(distances, 1.0e-12) ** power
    return np.sum(values * weights[:, None], axis=0) / np.sum(weights)
