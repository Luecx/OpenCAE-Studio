"""Regress surface-load association with concrete mesh element facets."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pyvista as pv

from opencae.model.core import EntityRef
from opencae.model.entities.loads import (
    DistributedLoad,
    PressureLoad,
    load_region_projection,
)
from opencae.model.entities.regions import Region
from opencae.model.selection import (
    MeshElementOperand,
    MeshFacetOperand,
    NamedRegionOperand,
    RegionDefinition,
    RegionProjection,
    RegionScope,
    RegionSelectionItem,
)
from opencae.ui.viewport.boundary_geometry import region_samples
from opencae.ui.viewport.boundary_overlay import _load_vector


def _definition(*operands):
    return RegionDefinition(tuple(RegionSelectionItem(item) for item in operands))


def _tet_grid(part):
    points = np.asarray(part.mesh.nodes.coordinates, dtype=float)
    cells = np.asarray((4, 0, 1, 2, 3), dtype=np.int64)
    grid = pv.UnstructuredGrid(
        cells,
        np.asarray((pv.CellType.TETRA,), dtype=np.uint8),
        points,
    )
    grid.cell_data["element_id"] = np.asarray((1,), dtype=np.int64)
    return grid


def _scene(instance, grid):
    return SimpleNamespace(
        mesh_grid=None,
        mesh_grids={instance.id: grid},
        part_id=None,
        assembly_instances={instance.id: instance},
        instance_for=lambda instance_id: instance if instance_id == instance.id else None,
        snapshot_for=lambda _instance_id: None,
    )


def test_named_mesh_facet_surface_places_pressure_and_traction_on_the_face(project_factory):
    data = project_factory(two_instances=False, include_constraints=False)
    project, part, instance = data["project"], data["part"], data["instance_1"]
    surface = Region(
        name="FACET_SURFACE",
        scope=RegionScope.PART,
        preferred_projection=RegionProjection.FACETS,
        definition=_definition(
            MeshFacetOperand(
                EntityRef.of(part, "Part"),
                1,
                "S1",
                mesh_revision=part.mesh.revision,
            )
        ),
    )
    part.regions.append(surface)
    project.rebuild_index(strict=True)
    target = _definition(
        NamedRegionOperand(
            EntityRef.of(surface, "Region"),
            EntityRef.of(instance, "Instance"),
        )
    )
    pressure = PressureLoad(name="P", target=target, pressure=4.0)
    traction = DistributedLoad(name="T", target=target, components=[1.0, 2.0, 3.0])
    scene = _scene(instance, _tet_grid(part))

    pressure_samples = region_samples(
        project,
        pressure.target,
        scene,
        projection=load_region_projection(pressure),
    )
    traction_samples = region_samples(
        project,
        traction.target,
        scene,
        projection=load_region_projection(traction),
    )

    assert len(pressure_samples) == len(traction_samples) == 1
    center, normal = pressure_samples[0]
    assert np.allclose(center, (1.0 / 3.0, 1.0 / 3.0, 0.0))
    assert normal is not None
    assert np.isclose(np.linalg.norm(normal), 1.0)
    assert np.linalg.norm(_load_vector(pressure, normal)) == 4.0
    assert np.allclose(traction_samples[0][0], center)
    assert np.allclose(_load_vector(traction, traction_samples[0][1]), (1.0, 2.0, 3.0))


def test_element_based_surface_expands_to_exterior_facets_for_surface_loads(project_factory):
    data = project_factory(two_instances=False, include_constraints=False)
    project, part, instance = data["project"], data["part"], data["instance_1"]
    surface = Region(
        name="ELEMENT_SURFACE",
        scope=RegionScope.PART,
        preferred_projection=RegionProjection.FACETS,
        definition=_definition(
            MeshElementOperand(
                EntityRef.of(part, "Part"),
                1,
                mesh_revision=part.mesh.revision,
            )
        ),
    )
    part.regions.append(surface)
    project.rebuild_index(strict=True)
    pressure = PressureLoad(
        name="P",
        target=_definition(
            NamedRegionOperand(
                EntityRef.of(surface, "Region"),
                EntityRef.of(instance, "Instance"),
            )
        ),
        pressure=2.0,
    )
    samples = region_samples(
        project,
        pressure.target,
        _scene(instance, _tet_grid(part)),
        projection=RegionProjection.FACETS,
    )

    assert len(samples) == 4
    assert all(normal is not None for _center, normal in samples)
    assert all(np.isclose(np.linalg.norm(normal), 1.0) for _center, normal in samples)
    element_center = np.asarray((0.25, 0.25, 0.25))
    assert all(not np.allclose(center, element_center) for center, _normal in samples)
