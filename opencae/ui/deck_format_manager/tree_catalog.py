"""Define the FEMaster editor hierarchy from current OpenCAE record families."""

from .element_type_catalog import element_tree_nodes
from .profile_record_catalog import profile_tree_nodes


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
                "children": element_tree_nodes(),
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
        "children": profile_tree_nodes(),
    },
    {"key": "fields", "label": "Fields"},
    {
        "key": "coordinate_systems",
        "label": "Coordinate Systems",
        "children": (
            {
                "key": "coordinate_systems.rectangular",
                "label": "Rectangular",
            },
            {
                "key": "coordinate_systems.cylindrical",
                "label": "Cylindrical",
            },
        ),
    },
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
