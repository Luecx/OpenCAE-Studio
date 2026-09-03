from __future__ import annotations

import numpy as np

from .result_query_model import QueryResult


_VTK_CELL_LABELS = {
    3: "Line (2-node)",
    5: "Triangle (3-node)",
    9: "Quadrilateral (4-node)",
    10: "Tetrahedron (4-node)",
    12: "Hexahedron (8-node)",
    13: "Wedge (6-node)",
    14: "Pyramid (5-node)",
    21: "Quadratic line (3-node)",
    22: "Quadratic triangle (6-node)",
    23: "Quadratic quadrilateral (8-node)",
    24: "Quadratic tetrahedron (10-node)",
    25: "Quadratic hexahedron (20-node)",
    26: "Quadratic wedge (15-node)",
    27: "Quadratic pyramid (13-node)",
}
_STRING_CELL_LABELS = {
    "line": "Line",
    "triangle": "Triangle",
    "quad": "Quadrilateral",
    "quadrilateral": "Quadrilateral",
    "tetra": "Tetrahedron",
    "tetrahedron": "Tetrahedron",
    "hexahedron": "Hexahedron",
    "hex": "Hexahedron",
    "wedge": "Wedge",
    "pyramid": "Pyramid",
}


def node_values(grid, point, field=None):
    index = int(grid.find_closest_point(point))
    node_id = int(
        grid.point_data.get("node_id", np.arange(grid.n_points))[index]
    )
    summary = [("Node", node_id), ("Coordinates", _vector(grid.points[index]))]
    values = _node_field_rows(grid, index, field)
    matrix = [[name, value] for name, value in values]
    return index, QueryResult(
        summary=summary,
        summary_columns=2,
        columns=["Component", "Value"],
        matrix=matrix,
    )


def element_values(grid, point, field=None):
    cell_id = int(grid.find_closest_cell(point))
    cell = grid.get_cell(cell_id)
    point_ids = np.asarray(cell.point_ids, dtype=int)
    element_ids = grid.cell_data.get("element_id", np.arange(grid.n_cells))
    component = _component(field)
    summary = [
        ("Element", int(element_ids[cell_id])),
        ("Cell type", _cell_type_label(cell)),
        ("Component", component),
    ]
    values = _component_values(grid, field, component)
    nodes = _node_ids(grid, point_ids)
    matrix = (
        [[node, _value(values[index])] for node, index in zip(nodes, point_ids)]
        if values is not None
        else []
    )
    if not matrix:
        summary.append(
            ("Field values", "No nodal values are available for this component")
        )
    return cell_id, QueryResult(
        summary=summary,
        summary_columns=2,
        columns=["Node", component],
        matrix=matrix,
    )


def _cell_type_label(cell):
    """Return a readable finite-element topology instead of a raw VTK type id."""
    raw_type = getattr(cell, "type", "")
    try:
        cell_type = int(raw_type)
    except (TypeError, ValueError):
        key = str(raw_type).strip().casefold().replace("vtk_", "")
        base = _STRING_CELL_LABELS.get(key, str(raw_type).strip().replace("_", " ").title())
        count = len(getattr(cell, "point_ids", ()))
        return f"{base} ({count}-node)" if count else base or "VTK cell"

    label = _VTK_CELL_LABELS.get(cell_type)
    if label:
        return label
    count = int(getattr(cell, "n_points", len(getattr(cell, "point_ids", ()))))
    name = type(cell).__name__.replace("Cell", "").strip() or "VTK cell"
    return f"{name} ({count}-node)" if count else name


def _node_field_rows(grid, index, field):
    rows = []
    for label, values in _field_arrays(grid, field):
        rows.append((label, _value(np.asarray(values)[index])))
    return rows or _all_point_rows(grid, index)


def _field_arrays(grid, field):
    if field is None:
        return []
    block = field.metadata.get("block", field.name)
    names = [
        *field.metadata.get("components", ()),
        *field.metadata.get("derived", ()),
        "Magnitude",
    ]
    rows = []
    for name in dict.fromkeys(str(item) for item in names):
        key = f"{block}:{name}"
        if key in grid.point_data:
            rows.append((name, grid.point_data[key]))
    return rows


def _component_values(grid, field, component):
    if field is None:
        return None
    key = f"{field.metadata.get('block', field.name)}:{component}"
    return np.asarray(grid.point_data[key]) if key in grid.point_data else None


def _component(field):
    return str(field.metadata.get("component", "Magnitude")) if field else "Value"


def _all_point_rows(grid, index):
    return [
        (name, _value(np.asarray(values)[index]))
        for name, values in grid.point_data.items()
        if name != "node_id"
    ]


def _node_ids(grid, indices):
    values = np.asarray(grid.point_data.get("node_id", indices))
    return [int(values[int(index)]) for index in indices]


def _value(value):
    data = np.asarray(value)
    return f"{float(data):.7g}" if data.ndim == 0 else _vector(data)


def _vector(values):
    return "(" + ", ".join(
        f"{float(value):.7g}" for value in np.asarray(values).ravel()
    ) + ")"
