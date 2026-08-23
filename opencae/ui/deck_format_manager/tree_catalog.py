"""Defines the editor hierarchy from current OpenCAE record families."""

from collections import OrderedDict

from opencae.model.entities.elements.factory import element_definition_types


def _slug(value: str) -> str:
    """Create a stable catalog key fragment from one display label."""
    return "_".join(str(value).strip().lower().replace("-", " ").split())


def _element_children() -> tuple[dict, ...]:
    """Mirror the canonical OpenCAE element family/topology registry in the tree."""
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for category, topology, _definition_type in element_definition_types():
        grouped.setdefault(category, []).append(topology)
    return tuple(
        {
            "key": f"mesh.elements.{_slug(category)}",
            "label": category,
            "children": tuple(
                {
                    "key": f"mesh.elements.{_slug(category)}.{_slug(topology)}",
                    "label": topology,
                }
                for topology in topologies
            ),
        }
        for category, topologies in grouped.items()
    )


TREE_SPEC = (
    {
        "key": "general",
        "label": "General",
        "fixed": True,
        "children": (
            {"key": "general.formatting", "label": "Formatting", "fixed": True},
            {"key": "general.comments", "label": "Comments", "fixed": True},
            {"key": "general.output", "label": "Output Style", "fixed": True},
        ),
    },
    {
        "key": "mesh",
        "label": "Mesh",
        "children": (
            {"key": "mesh.nodes", "label": "Nodes"},
            {
                "key": "mesh.elements",
                "label": "Elements",
                "children": _element_children(),
            },
        ),
    },
    {"key": "node_sets", "label": "Node Sets"},
    {"key": "element_sets", "label": "Element Sets"},
    {"key": "surfaces", "label": "Surfaces"},
    {
        "key": "materials",
        "label": "Materials",
        "children": (
            {"key": "materials.header", "label": "Material Header"},
            {"key": "materials.isotropic_elastic", "label": "Isotropic Elastic"},
            {"key": "materials.density", "label": "Density"},
            {"key": "materials.plasticity", "label": "Plasticity"},
            {"key": "materials.thermal_expansion", "label": "Thermal Expansion"},
        ),
    },
    {
        "key": "sections",
        "label": "Sections",
        "children": (
            {"key": "sections.solid", "label": "Solid Section"},
            {"key": "sections.shell", "label": "Shell Section"},
            {"key": "sections.beam", "label": "Beam Section"},
            {"key": "sections.truss", "label": "Truss Section"},
        ),
    },
    {
        "key": "profiles",
        "label": "Profiles",
        "children": (
            {"key": "profiles.rectangle", "label": "Rectangle"},
            {"key": "profiles.box", "label": "Box"},
            {"key": "profiles.pipe", "label": "Pipe"},
            {"key": "profiles.i", "label": "I-Profile"},
            {"key": "profiles.general", "label": "General Profile"},
        ),
    },
    {"key": "fields", "label": "Fields"},
    {"key": "coordinate_systems", "label": "Coordinate Systems"},
    {"key": "reference_points", "label": "Reference Points"},
    {
        "key": "constraints",
        "label": "Constraints",
        "children": (
            {"key": "constraints.kinematic", "label": "Kinematic Coupling"},
            {"key": "constraints.distributing", "label": "Distributing Coupling"},
            {"key": "constraints.tie", "label": "Tie"},
            {"key": "constraints.rigid", "label": "Rigid Body"},
            {"key": "constraints.equation", "label": "Equation"},
            {"key": "constraints.mpc", "label": "MPC"},
        ),
    },
    {
        "key": "boundary_conditions",
        "label": "Boundary Conditions",
        "children": (
            {"key": "boundary_conditions.fixed", "label": "Fixed"},
            {"key": "boundary_conditions.displacement", "label": "Displacement"},
            {"key": "boundary_conditions.symmetry", "label": "Symmetry"},
        ),
    },
    {
        "key": "loads",
        "label": "Loads",
        "children": (
            {"key": "loads.concentrated", "label": "Concentrated Load"},
            {"key": "loads.distributed", "label": "Distributed Load"},
            {"key": "loads.pressure", "label": "Pressure"},
            {"key": "loads.volume", "label": "Volume Load"},
            {"key": "loads.inertia", "label": "Inertia Load"},
            {"key": "loads.temperature", "label": "Temperature"},
        ),
    },
    {
        "key": "analysis",
        "label": "Analysis",
        "children": (
            {"key": "analysis.step", "label": "Step Header"},
            {"key": "analysis.output", "label": "Output Requests"},
        ),
    },
)
