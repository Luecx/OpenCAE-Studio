"""Define the hierarchical record ordering shown by the deck-format manager."""

from __future__ import annotations

from .element_type_catalog import element_tree_nodes
from .profile_record_catalog import profile_tree_nodes


_FEMASTER_ONLY = ("FEMaster",)
_ABAQUS_ONLY = ("Abaqus",)


def _leaf(key: str, label: str, supported_formats=()) -> dict:
    """Create one navigation leaf with optional underlying-format capability."""
    node = {"key": key, "label": label}
    if supported_formats:
        node["supported_formats"] = tuple(supported_formats)
    return node


TREE_SPEC = (
    {
        "key": "general",
        "label": "General",
        "fixed": True,
        "children": (
            {"key": "general.formatting", "label": "Formatting", "fixed": True},
            {"key": "general.comments", "label": "Comments", "fixed": True},
            {"key": "general.output", "label": "Output Style", "fixed": True},
            _leaf("general.heading", "Heading", _FEMASTER_ONLY),
            _leaf("general.model", "Model Marker", _FEMASTER_ONLY),
        ),
    },
    {
        "key": "mesh",
        "label": "Mesh",
        "children": (
            _leaf("mesh.nodes", "Nodes"),
            {
                "key": "mesh.elements",
                "label": "Elements",
                "children": element_tree_nodes(),
            },
        ),
    },
    _leaf("node_sets", "Node Sets"),
    _leaf("element_sets", "Element Sets"),
    {
        "key": "surfaces",
        "label": "Surfaces",
        "children": (
            _leaf("surfaces.definition", "Surface Definition", _FEMASTER_ONLY),
            _leaf("surfaces.set", "Surface Set (SFSET)", _FEMASTER_ONLY),
        ),
    },
    {
        "key": "materials",
        "label": "Materials",
        "children": (
            _leaf("materials.header", "Material Header"),
            {
                "key": "materials.elastic",
                "label": "Elasticity",
                "children": (
                    _leaf("materials.elastic.isotropic", "Isotropic Elastic"),
                    _leaf(
                        "materials.elastic.generalised_isotropic",
                        "Generalised Isotropic",
                        _FEMASTER_ONLY,
                    ),
                    _leaf("materials.elastic.engineering_constants", "Engineering Constants"),
                    _leaf("materials.elastic.orthotropic_stiffness", "Orthotropic Stiffness"),
                ),
            },
            _leaf("materials.hyperelastic.neo_hooke", "Neo-Hooke Hyperelastic"),
            _leaf("materials.density", "Density"),
            _leaf("materials.thermal_expansion", "Thermal Expansion", _FEMASTER_ONLY),
            _leaf("materials.plasticity", "Plasticity", _ABAQUS_ONLY),
        ),
    },
    {
        "key": "sections",
        "label": "Sections",
        "children": (
            _leaf("sections.solid", "Solid Section"),
            {
                "key": "sections.shell",
                "label": "Shell Section",
                "children": (
                    _leaf("sections.shell.integrated", "Integrated Shell", _FEMASTER_ONLY),
                    _leaf("sections.shell.abd", "ABD Shell", _FEMASTER_ONLY),
                ),
            },
            _leaf("sections.beam", "Beam Section", _FEMASTER_ONLY),
            _leaf("sections.truss", "Truss Section", _FEMASTER_ONLY),
        ),
    },
    {
        "key": "profiles",
        "label": "Profiles",
        "children": profile_tree_nodes(),
    },
    {
        "key": "fields",
        "label": "Fields",
        "children": (
            _leaf("fields.node", "Node Field", _FEMASTER_ONLY),
            _leaf("fields.element", "Element Field", _FEMASTER_ONLY),
            _leaf("fields.element_nodal", "Element-Nodal Field", _FEMASTER_ONLY),
            _leaf("fields.element_ip", "Integration-Point Field", _FEMASTER_ONLY),
            _leaf("fields.element_mp", "Material-Point Field", _FEMASTER_ONLY),
            _leaf("fields.normal", "Shell Normal Field", _FEMASTER_ONLY),
        ),
    },
    {
        "key": "coordinate_systems",
        "label": "Coordinate Systems",
        "children": (
            _leaf("coordinate_systems.rectangular", "Rectangular"),
            _leaf("coordinate_systems.cylindrical", "Cylindrical", _FEMASTER_ONLY),
        ),
    },
    _leaf("reference_points", "Reference Points"),
    _leaf("point_masses", "Point Masses", _FEMASTER_ONLY),
    {
        "key": "constraints",
        "label": "Constraints",
        "children": (
            {
                "key": "constraints.kinematic",
                "label": "Kinematic Coupling",
                "children": (
                    _leaf("constraints.kinematic.node_set", "Node-Set Slave", _FEMASTER_ONLY),
                    _leaf("constraints.kinematic.surface", "Surface Slave", _FEMASTER_ONLY),
                ),
            },
            {
                "key": "constraints.distributing",
                "label": "Distributing Coupling",
                "children": (
                    _leaf("constraints.distributing.node_set", "Node-Set Slave", _FEMASTER_ONLY),
                    _leaf("constraints.distributing.surface", "Surface Slave", _FEMASTER_ONLY),
                ),
            },
            _leaf("constraints.tie", "Tie", _FEMASTER_ONLY),
            {
                "key": "constraints.connector",
                "label": "Connector",
                "children": tuple(
                    _leaf(f"constraints.connector.{key}", label, _FEMASTER_ONLY)
                    for key, label in (
                        ("beam", "Beam"),
                        ("hinge", "Hinge"),
                        ("cylindrical", "Cylindrical"),
                        ("translator", "Translator"),
                        ("join", "Join"),
                        ("joinrx", "Join RX"),
                    )
                ),
            },
            _leaf("constraints.rigid", "Rigid Body / RBM", _FEMASTER_ONLY),
            _leaf("constraints.contact", "Contact", _FEMASTER_ONLY),
            _leaf("constraints.equation", "Equation"),
            _leaf("constraints.mpc", "MPC", _ABAQUS_ONLY),
        ),
    },
    {
        "key": "boundary_conditions",
        "label": "Supports / Boundary Conditions",
        "children": (
            _leaf("boundary_conditions.fixed", "Fixed", _FEMASTER_ONLY),
            _leaf("boundary_conditions.displacement", "Displacement", _FEMASTER_ONLY),
            _leaf("boundary_conditions.symmetry", "Symmetry", _FEMASTER_ONLY),
        ),
    },
    {
        "key": "loads",
        "label": "Loads",
        "children": (
            _leaf("loads.amplitude", "Amplitude", _FEMASTER_ONLY),
            _leaf("loads.concentrated", "Concentrated Load / CLOAD", _FEMASTER_ONLY),
            _leaf("loads.distributed", "Distributed Traction / DLOAD", _FEMASTER_ONLY),
            _leaf("loads.pressure", "Pressure / PLOAD", _FEMASTER_ONLY),
            _leaf("loads.volume", "Volume Load / VLOAD", _FEMASTER_ONLY),
            _leaf("loads.inertia", "Inertia Load", _FEMASTER_ONLY),
            _leaf("loads.temperature", "Thermal Load / TLOAD", _FEMASTER_ONLY),
        ),
    },
    {
        "key": "analysis",
        "label": "Analysis / Loadcases",
        "children": (
            {
                "key": "analysis.loadcases",
                "label": "Loadcase Type",
                "children": tuple(
                    _leaf(f"analysis.loadcases.{key}", label, _FEMASTER_ONLY)
                    for key, label in (
                        ("linear_static", "Linear Static"),
                        ("nonlinear_static", "Nonlinear Static"),
                        ("linear_buckling", "Linear Buckling"),
                        ("topology_static", "Topology Static"),
                        ("eigenfrequency", "Eigenfrequency"),
                        ("linear_transient", "Linear Transient"),
                        ("linear_harmonic", "Linear Harmonic"),
                    )
                ),
            },
            {
                "key": "analysis.selections",
                "label": "Collectors",
                "children": (
                    _leaf("analysis.selections.supports", "Support Collectors", _FEMASTER_ONLY),
                    _leaf("analysis.selections.loads", "Load Collectors", _FEMASTER_ONLY),
                ),
            },
            {
                "key": "analysis.controls",
                "label": "Numerical Controls",
                "children": tuple(
                    _leaf(f"analysis.controls.{key}", label, _FEMASTER_ONLY)
                    for key, label in (
                        ("solver", "Solver"),
                        ("constraint_method", "Constraint Method"),
                        ("nonlinear", "Nonlinear Controls"),
                        ("time", "Time"),
                        ("newmark", "Newmark"),
                        ("damping", "Damping"),
                        ("frequencies", "Frequencies"),
                        ("num_eigenvalues", "Number of Eigenvalues"),
                        ("sigma", "Buckling Sigma"),
                        ("write_every", "Write Every"),
                        ("initial_velocity", "Initial Velocity"),
                        ("inertia_relief", "Inertia Relief"),
                        ("rebalance_loads", "Rebalance Loads"),
                    )
                ),
            },
            {
                "key": "analysis.topology",
                "label": "Topology Controls",
                "children": (
                    _leaf("analysis.topology.density", "Topology Density", _FEMASTER_ONLY),
                    _leaf("analysis.topology.orientation", "Topology Orientation", _FEMASTER_ONLY),
                    _leaf("analysis.topology.exponent", "Topology Exponent", _FEMASTER_ONLY),
                ),
            },
            {
                "key": "analysis.diagnostics",
                "label": "Diagnostics / Output",
                "children": (
                    _leaf("analysis.diagnostics.overview", "Overview", _FEMASTER_ONLY),
                    _leaf("analysis.diagnostics.stiffness", "Request Stiffness", _FEMASTER_ONLY),
                    _leaf(
                        "analysis.diagnostics.geometric_stiffness",
                        "Request Geometric Stiffness",
                        _FEMASTER_ONLY,
                    ),
                    _leaf(
                        "analysis.diagnostics.constraint_summary",
                        "Constraint Summary",
                        _FEMASTER_ONLY,
                    ),
                ),
            },
            _leaf("analysis.end", "End Loadcase", _FEMASTER_ONLY),
        ),
    },
)
