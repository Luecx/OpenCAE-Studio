"""Define FEMaster coupling, tie, connector, RBM, contact and equation templates."""

from __future__ import annotations


_COUPLING_FIELDS = (
    ("master_set", "One-node master/reference node set", "REF"),
    ("slave_set", "Slave node set", "COUPLED_NODES"),
    ("surface_set", "Slave surface set", "LOADED_FACE"),
    ("ux", "Ux selector; positive enables the relation", 1.0),
    ("uy", "Uy selector; positive enables the relation", 1.0),
    ("uz", "Uz selector; positive enables the relation", 1.0),
    ("rx", "Rx selector; positive enables the relation", 0.0),
    ("ry", "Ry selector; positive enables the relation", 0.0),
    ("rz", "Rz selector; positive enables the relation", 0.0),
)


def _coupling_template(kind: str, slave_keyword: str, slave_field: str) -> str:
    """Build one concrete COUPLING variant without conditional template syntax."""
    return (
        f"*COUPLING, MASTER={{master_set}}, {slave_keyword}={{{slave_field}}}, TYPE={kind}\n"
        "{ux}, {uy}, {uz}, {rx}, {ry}, {rz}"
    )


def connector_template_specs() -> dict[str, dict]:
    """Return one literal CONNECTOR template for every documented connector type."""
    result = {}
    for kind in ("BEAM", "HINGE", "CYLINDRICAL", "TRANSLATOR", "JOIN", "JOINRX"):
        result[f"constraints.connector.{kind.lower()}"] = {
            "template": (
                f"*CONNECTOR, TYPE={kind}, NSET1={{node_set_1}}, "
                "NSET2={node_set_2}, COORDINATESYSTEM={coordinate_system}"
            ),
            "fields": (
                ("node_set_1", "First one-node set", "PIN_A"),
                ("node_set_2", "Second one-node set", "PIN_B"),
                ("coordinate_system", "Connector local coordinate system", "HINGE_AXES"),
            ),
            "loops": (),
            "commands": ("CONNECTOR",),
        }
    return result


TEMPLATE_SPECS = {
    "constraints.kinematic.node_set": {
        "template": _coupling_template("KINEMATIC", "SLAVE", "slave_set"),
        "fields": _COUPLING_FIELDS,
        "loops": (),
        "commands": ("COUPLING",),
    },
    "constraints.kinematic.surface": {
        "template": _coupling_template("KINEMATIC", "SFSET", "surface_set"),
        "fields": _COUPLING_FIELDS,
        "loops": (),
        "commands": ("COUPLING",),
    },
    "constraints.distributing.node_set": {
        "template": _coupling_template("STRUCTURAL", "SLAVE", "slave_set"),
        "fields": _COUPLING_FIELDS,
        "loops": (),
        "commands": ("COUPLING",),
    },
    "constraints.distributing.surface": {
        "template": _coupling_template("STRUCTURAL", "SFSET", "surface_set"),
        "fields": _COUPLING_FIELDS,
        "loops": (),
        "commands": ("COUPLING",),
    },
    "constraints.tie": {
        "template": (
            "*TIE, MASTER={master}, SLAVE={slave}, "
            "DISTANCE={distance}, ADJUST={adjust}"
        ),
        "fields": (
            ("master", "Master surface or line set", "MASTER_FACE"),
            ("slave", "Slave node or surface set", "SLAVE_NODES"),
            ("distance", "Search/projection distance", 0.5),
            ("adjust", "Initial adjustment: YES or NO", "YES"),
        ),
        "loops": (),
        "commands": ("TIE",),
    },
    "constraints.rigid": {
        "template": "*RBM, ELSET={element_set}",
        "fields": (("element_set", "Structural element set whose rigid modes are removed", "FREE_COMPONENT"),),
        "loops": (),
        "commands": ("RBM",),
    },
    "constraints.contact": {
        "template": (
            "*CONTACT, MASTER={master_surface}, SLAVE={slave_surface}, "
            "PENALTY={penalty}, CLEARANCE={clearance}, FLIP={flip}"
        ),
        "fields": (
            ("master_surface", "Master surface set", "MASTER_FACE"),
            ("slave_surface", "Slave surface set", "SLAVE_FACE"),
            ("penalty", "Initial augmented-Lagrange penalty stiffness", 1.0e8),
            ("clearance", "Contact-clearance offset", 0.0),
            ("flip", "Reverse master normal: YES or NO", "NO"),
        ),
        "loops": (),
        "commands": ("CONTACT",),
    },
    "constraints.equation": {
        "template": (
            "*EQUATION\n"
            "{term_count}\n"
            "{for term in terms}\n"
            "{term.target}, {term.dof}, {term.coefficient}\n"
            "{endfor}"
        ),
        "fields": (("term_count", "Number of target/DOF/coefficient terms", 2),),
        "loops": (
            {
                "collection": "terms",
                "item": "term",
                "description": "Linear equation terms; one triple per template row.",
                "fields": (
                    ("target", "Node ID, reference target or node-set name", "NODE_A"),
                    ("dof", "One-based structural DOF number 1-6", 1),
                    ("coefficient", "Finite equation coefficient", 1.0),
                ),
                "examples": (
                    {"target": "NODE_A", "dof": 1, "coefficient": 1.0},
                    {"target": "NODE_B", "dof": 1, "coefficient": -1.0},
                ),
            },
        ),
        "commands": ("EQUATION",),
    },
    "constraints.mpc": {
        "template": "*MPC\n{mpc_type}, {master}, {slave}",
        "fields": (
            ("mpc_type", "Abaqus MPC type", "BEAM"),
            ("master", "First MPC target", "MASTER"),
            ("slave", "Second MPC target", "SLAVE"),
        ),
        "loops": (),
        "commands": ("MPC",),
    },
}
TEMPLATE_SPECS.update(connector_template_specs())
