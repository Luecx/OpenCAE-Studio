"""Mesh-edge paths and FRD XY-series, without dependence on the displayed/deformed mesh.

Paths use solver node IDs and the undeformed mesh. A waypoint pair is joined by
Dijkstra's shortest Euclidean edge path; element interiors are never shortcuts.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import dist, isfinite
from pathlib import Path

import numpy as np

from opencae.results.derived_fields import component_values
from opencae.results.frd_loader import FrdLoader


@dataclass(frozen=True)
class MeshPath:
    name: str
    waypoints: tuple[int, ...]
    node_ids: tuple[int, ...]
    distances: tuple[float, ...]
    default_x_axis: str = "distance"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "waypoints": list(self.waypoints),
            "node_ids": list(self.node_ids),
            "distances": list(self.distances),
            "default_x_axis": self.default_x_axis,
        }

    @classmethod
    def from_dict(cls, value):
        return cls(
            name=str(value["name"]),
            waypoints=tuple(int(x) for x in value["waypoints"]),
            node_ids=tuple(int(x) for x in value["node_ids"]),
            distances=tuple(float(x) for x in value["distances"]),
            default_x_axis=str(value.get("default_x_axis", "distance")),
        )


def _pairs(cell):
    """Extract actual topological edges, including quadratic midside segments."""
    count = cell.GetNumberOfEdges()
    if count:
        edges = (cell.GetEdge(i) for i in range(count))
    else:
        # vtkLine and vtkQuadraticEdge are themselves edges.
        edges = (cell,)
    for edge in edges:
        ids = edge.GetPointIds()
        values = [int(ids.GetId(i)) for i in range(ids.GetNumberOfIds())]
        if len(values) == 2:
            yield values[0], values[1]
        elif len(values) == 3:
            # VTK quadratic edges have endpoints first, midside node last.
            yield values[0], values[2]
            yield values[2], values[1]
        elif len(values) > 3:
            # Lagrange edge: ordered endpoints followed by successive interior nodes.
            sequence = [values[0], *values[2:], values[1]]
            yield from zip(sequence, sequence[1:])


def mesh_graph(data, loader=None):
    """Return (coordinates, node adjacency) from the original FRD FE topology.

    The beam surface expansion is excluded; otherwise its visualization edges
    could incorrectly connect distinct FE nodes.
    """
    from opencae.ui.viewport.result_visualization import _vtk_ordered_frd_grid

    loader = loader or FrdLoader()
    grid = _vtk_ordered_frd_grid(loader.pyvista_grid(data))
    tags = np.asarray(grid.point_data["node_id"], dtype=np.int64)
    coordinates = {
        int(tag): tuple(float(x) for x in grid.points[index])
        for index, tag in enumerate(tags) if int(tag) > 0
    }
    adjacency = {node: {} for node in coordinates}
    for cell_index in range(grid.n_cells):
        if "_opencae_physical_beam" in grid.cell_data:
            # Physical beam display polygons do not define original FE edges.
            if int(grid.cell_data["_opencae_physical_beam"][cell_index]):
                continue
        cell = grid.GetCell(cell_index)
        for a, b in _pairs(cell):
            first, second = int(tags[a]), int(tags[b])
            if first == second or first not in adjacency or second not in adjacency:
                continue
            length = dist(coordinates[first], coordinates[second])
            adjacency[first][second] = length
            adjacency[second][first] = length
    return coordinates, adjacency


def shortest_edge_path(adjacency, start, end):
    """Dijkstra with stable tie ordering and explicit disconnected-node errors."""
    start, end = int(start), int(end)
    if start not in adjacency or end not in adjacency:
        raise ValueError(f"Unknown path node: {start if start not in adjacency else end}")
    if start == end:
        return (start,)
    queue = [(0.0, start)]
    best = {start: 0.0}
    previous = {}
    settled = set()
    while queue:
        cost, node = heappop(queue)
        if node in settled:
            continue
        settled.add(node)
        if node == end:
            sequence = [end]
            while sequence[-1] != start:
                sequence.append(previous[sequence[-1]])
            return tuple(reversed(sequence))
        for neighbour, length in sorted(adjacency[node].items()):
            new_cost = cost + float(length)
            if new_cost < best.get(neighbour, float("inf")) - 1e-12:
                best[neighbour] = new_cost
                previous[neighbour] = node
                heappush(queue, (new_cost, neighbour))
    raise ValueError(f"No connected mesh-edge route between nodes {start} and {end}")


def create_mesh_path(name, waypoints, coordinates, adjacency, default_x_axis='distance'):
    if default_x_axis not in {"distance", "node_id"}:
        raise ValueError("Path X must be distance or node ID")
    anchors = tuple(int(x) for x in waypoints)
    if not name.strip() or len(anchors) < 2:
        raise ValueError("A path needs a name and at least two waypoint node IDs")
    ordered = []
    for a, b in zip(anchors, anchors[1:]):
        segment = shortest_edge_path(adjacency, a, b)
        ordered.extend(segment if not ordered else segment[1:])
    if len(ordered) < 2:
        raise ValueError("Path must contain at least two distinct nodes")
    distances = [0.0]
    for a, b in zip(ordered, ordered[1:]):
        distances.append(distances[-1] + dist(coordinates[a], coordinates[b]))
    return MeshPath(name.strip(), anchors, tuple(ordered), tuple(distances), default_x_axis)


def stored_paths(result):
    return tuple(MeshPath.from_dict(item) for item in result.metadata.get("mesh_paths", ()))


def _block(loader, source, step_id, frame_id, field_name):
    data = loader.read(source)
    candidates = [
        value for value in data.fields
        if value.name == field_name
        and int(value.step_id) == int(step_id)
        and int(value.frame_id) == int(frame_id)
    ]
    if not candidates:
        raise ValueError(f"Field {field_name} is unavailable in frame {frame_id}")
    return candidates[-1]


def _scalar(block, node_id, component):
    row = block.values.get(int(node_id))
    if row is None:
        return float("nan")
    values = np.asarray([row], dtype=float)
    scalar = component_values(block.components, values, str(component))
    if scalar.size != 1:
        raise ValueError(f"Component {component} is unavailable for {block.name}")
    return float(scalar[0])


def path_field_series(loader, source, path, field_name, component, step_id, frame_id,
                      x_axis="distance"):
    block = _block(loader, source, step_id, frame_id, field_name)
    if x_axis not in {"distance", "node_id"}:
        raise ValueError("Path X axis must be distance or node_id")
    x = path.distances if x_axis == "distance" else path.node_ids
    y = tuple(_scalar(block, node, component) for node in path.node_ids)
    return tuple(float(value) for value in x), y


def time_field_series(loader, source, node_id, field_name, component, step_id):
    data = loader.read(source)
    frames = sorted(
        (block for block in data.fields
         if block.name == field_name and int(block.step_id) == int(step_id)),
        key=lambda block: (block.frame_id, block.block_index),
    )
    if not frames:
        raise ValueError(f"No frames for {field_name} in Step {step_id}")
    seen = set()
    x, y = [], []
    for block in frames:
        if block.frame_id in seen:
            continue
        seen.add(block.frame_id)
        x.append(float(block.frame_value))
        y.append(_scalar(block, node_id, component))
    return tuple(x), tuple(y)


def finite_series(x, y):
    """Only remove missing samples in a paired fashion; never invent results."""
    points = [(float(a), float(b)) for a, b in zip(x, y)
              if isfinite(float(a)) and isfinite(float(b))]
    return tuple(a for a, _ in points), tuple(b for _, b in points)
