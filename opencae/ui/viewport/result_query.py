from __future__ import annotations
import numpy as np
from .result_query_model import QueryResult


def node_values(grid, point, field=None):
    index = int(grid.find_closest_point(point)); node_id = int(grid.point_data.get("node_id", np.arange(grid.n_points))[index])
    rows = [("Node", node_id), ("Coordinates", _vector(grid.points[index]))]
    rows.extend(_node_field_rows(grid, index, field)); return index, QueryResult(summary=rows)


def element_values(grid, point, field=None):
    cell_id = int(grid.find_closest_cell(point)); cell = grid.get_cell(cell_id); point_ids = np.asarray(cell.point_ids, dtype=int)
    element_ids = grid.cell_data.get("element_id", np.arange(grid.n_cells)); component = _component(field)
    summary = [("Element", int(element_ids[cell_id])), ("Cell type", str(cell.type)), ("Component", component)]
    values = _component_values(grid, field, component); nodes = _node_ids(grid, point_ids)
    matrix = [[node, _value(values[index])] for node, index in zip(nodes, point_ids)] if values is not None else []
    if not matrix: summary.append(("Field values", "No nodal values are available for this component"))
    return cell_id, QueryResult(summary=summary, columns=["Node", component], matrix=matrix)


def _node_field_rows(grid, index, field):
    rows = []
    for label, values in _field_arrays(grid, field): rows.append((label, _value(np.asarray(values)[index])))
    return rows or _all_point_rows(grid, index)


def _field_arrays(grid, field):
    if field is None: return []
    block = field.metadata.get("block", field.name)
    names = [*field.metadata.get("components", ()), *field.metadata.get("derived", ()), "Magnitude"]
    rows = []
    for name in dict.fromkeys(str(item) for item in names):
        key = f"{block}:{name}"
        if key in grid.point_data: rows.append((name, grid.point_data[key]))
    return rows


def _component_values(grid, field, component):
    if field is None: return None
    key = f"{field.metadata.get('block', field.name)}:{component}"
    return np.asarray(grid.point_data[key]) if key in grid.point_data else None


def _component(field): return str(field.metadata.get("component", "Magnitude")) if field else "Value"
def _all_point_rows(grid,index): return [(name,_value(np.asarray(values)[index])) for name,values in grid.point_data.items() if name!="node_id"]
def _node_ids(grid,indices):
    values=np.asarray(grid.point_data.get("node_id",indices)); return [int(values[int(index)]) for index in indices]
def _value(value):
    data=np.asarray(value); return f"{float(data):.7g}" if data.ndim==0 else _vector(data)
def _vector(values): return "("+", ".join(f"{float(value):.7g}" for value in np.asarray(values).ravel())+")"
