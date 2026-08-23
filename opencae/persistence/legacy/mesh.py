"""Converts pre-polymorphic legacy mesh dictionaries into current model objects."""

from opencae.model.mesh import (
    DefaultSeed,
    EdgeSeed,
    MeshControl,
    MeshSettings,
    MeshState,
    Seed,
    create_element_definition,
)


def legacy_mesh(data):
    """Build a current MeshState from the historical mesh dictionary shape."""
    return MeshState(
        settings=MeshSettings(**data.get("settings", {})),
        seeds=[legacy_seed(item) for item in data.get("seeds", [])],
        controls=[MeshControl(**item) for item in data.get("controls", [])],
        element_definitions=[
            legacy_element(item) for item in data.get("elements", [])
        ],
        node_count=data.get("node_count", 0),
        element_count=data.get("element_count", 0),
        mesh_dimension=data.get("mesh_dimension", 0),
        minimum_quality=data.get("minimum_quality"),
        mean_quality=data.get("mean_quality"),
        status=data.get("status", "Not generated"),
    )


def legacy_seed(data):
    """Decode one historical seed record."""
    data = dict(data)
    kind = data.pop("seed_type", "Seed")
    if kind == "Default":
        return DefaultSeed(**data)
    if kind == "Edge":
        return EdgeSeed(**data)
    return Seed(seed_type=kind, **data)


def legacy_element(data):
    """Decode one historical element-definition summary."""
    data = dict(data)
    category = data.pop("category", "Solid Elements")
    topology = data.pop("topology", "Hexahedra")
    return create_element_definition(category, topology, **data)
