from opencae.model.mesh import DefaultSeed, EdgeSeed, MeshControl, MeshSettings, MeshState, Seed
from opencae.model.mesh import create_element_definition


def legacy_mesh(data):
    return MeshState(
        settings=MeshSettings(**data.get("settings", {})),
        seeds=[legacy_seed(item) for item in data.get("seeds", [])],
        controls=[MeshControl(**item) for item in data.get("controls", [])],
        elements=[legacy_element(item) for item in data.get("elements", [])],
        node_count=data.get("node_count", 0),
        element_count=data.get("element_count", 0),
        mesh_dimension=data.get("mesh_dimension", 0),
        minimum_quality=data.get("minimum_quality"),
        mean_quality=data.get("mean_quality"),
        status=data.get("status", "Not generated"),
    )


def legacy_seed(data):
    data = dict(data)
    kind = data.pop("seed_type", "Seed")
    if kind == "Default":
        return DefaultSeed(**data)
    if kind == "Edge":
        return EdgeSeed(**data)
    return Seed(seed_type=kind, **data)


def legacy_element(data):
    data = dict(data)
    category = data.pop("category", "Solid Elements")
    topology = data.pop("topology", "Hexahedra")
    return create_element_definition(category, topology, **data)
