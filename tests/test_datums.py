from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from opencae.model.datums import create_datum
from opencae.model.entities.parts.part import Part
from opencae.model.entities.project import Project
from opencae.persistence.project_io import load_project, save_project


def point(name, value): return {"name": name, "kind": "datum_point", "point": value}


def test_datum_construction_methods():
    midpoint = create_datum("Point", "MID", "Between Two Points", {
        "point_1": point("A", (0, 0, 0)), "point_2": point("B", (10, 0, 0)), "ratio": .25,
    })
    assert np.allclose(midpoint.position, (2.5, 0, 0))
    tangent = create_datum("Vector", "T", "Along Edge", {
        "edge": {"name": "E", "kind": "edge", "points": [(0, 0, 0), (0, 4, 0)]}, "position": .5,
    })
    assert np.allclose(tangent.origin, (0, 2, 0)); assert np.allclose(tangent.direction, (0, 1, 0))
    plane = create_datum("Plane", "P", "Three Points", {
        "point_1": point("A", (0, 0, 0)), "point_2": point("B", (1, 0, 0)), "point_3": point("C", (0, 1, 0)),
    })
    assert np.allclose(plane.normal, (0, 0, 1))


def test_datums_survive_project_roundtrip():
    project = Project(name="DATUMS"); part = Part(name="P")
    part.datums.append(create_datum("Point", "D", "Coordinates", {
        "coordinate_x": 1.0, "coordinate_y": 2.0, "coordinate_z": 3.0,
        "coordinate_system": {"origin": (0, 0, 0), "axis_1": (1, 0, 0), "axis_2": (0, 1, 0)},
    })); project.parts.append(part)
    with TemporaryDirectory() as directory:
        path = Path(directory) / "datums.ocae"; save_project(project, path); loaded = load_project(path)
    assert loaded.parts[0].datums[0].datum_type == "Point"
    assert loaded.parts[0].datums[0].position == (1.0, 2.0, 3.0)
