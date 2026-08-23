"""Define flat-model, mesh, region, reference-point and point-mass templates."""

from __future__ import annotations


TEMPLATE_SPECS = {
    "general.heading": {
        "template": "*HEADING\n{heading}",
        "fields": (("heading", "Descriptive deck heading", "OpenCAE model"),),
        "loops": (),
        "commands": ("HEADING",),
    },
    "general.model": {
        "template": "*MODEL, NAME={model_name}",
        "fields": (("model_name", "Optional native FEMaster model name", "MODEL-1"),),
        "loops": (),
        "commands": ("MODEL",),
    },
    "mesh.nodes": {
        "template": (
            "*NODE\n"
            "{for node in nodes}\n"
            "{node.id}, {node.x}, {node.y}, {node.z}\n"
            "{endfor}"
        ),
        "fields": (("node_set", "Optional NSET added on the NODE keyword", "NALL"),),
        "loops": (
            {
                "collection": "nodes",
                "item": "node",
                "description": "Nodes emitted into this NODE block.",
                "fields": (
                    ("id", "Solver node identifier", 101),
                    ("x", "Global X coordinate", 0.0),
                    ("y", "Global Y coordinate", 12.5),
                    ("z", "Global Z coordinate", 4.0),
                ),
                "examples": (
                    {"id": 101, "x": 0.0, "y": 12.5, "z": 4.0},
                    {"id": 102, "x": 8.0, "y": 12.5, "z": 4.0},
                ),
            },
        ),
        "commands": ("NODE",),
    },
    "node_sets": {
        "template": (
            "*NSET, NSET={set_name}\n"
            "{for member in members}\n"
            "{member.node_id}\n"
            "{endfor}"
        ),
        "fields": (
            ("set_name", "Node-set name", "FIXED_NODES"),
            ("generate_start", "GENERATE start identifier", 0),
            ("generate_end", "GENERATE inclusive end identifier", 99),
            ("generate_increment", "GENERATE increment", 1),
        ),
        "loops": (
            {
                "collection": "members",
                "item": "member",
                "description": "Explicit node-set members.",
                "fields": (("node_id", "Node identifier", 101),),
                "examples": ({"node_id": 101}, {"node_id": 102}, {"node_id": 103}),
            },
        ),
        "commands": ("NSET",),
    },
    "element_sets": {
        "template": (
            "*ELSET, ELSET={set_name}\n"
            "{for member in members}\n"
            "{member.element_id}\n"
            "{endfor}"
        ),
        "fields": (
            ("set_name", "Element-set name", "SOLID"),
            ("generate_start", "GENERATE start identifier", 0),
            ("generate_end", "GENERATE inclusive end identifier", 99),
            ("generate_increment", "GENERATE increment", 1),
        ),
        "loops": (
            {
                "collection": "members",
                "item": "member",
                "description": "Explicit element-set members.",
                "fields": (("element_id", "Element identifier", 42),),
                "examples": ({"element_id": 42}, {"element_id": 43}),
            },
        ),
        "commands": ("ELSET",),
    },
    "surfaces.definition": {
        "template": (
            "*SURFACE, NAME={surface_name}\n"
            "{for facet in facets}\n"
            "{facet.element_id}, {facet.side_id}\n"
            "{endfor}"
        ),
        "fields": (("surface_name", "Surface name", "PRESSURE_FACE"),),
        "loops": (
            {
                "collection": "facets",
                "item": "facet",
                "description": "Element-side entries belonging to the surface.",
                "fields": (
                    ("element_id", "Element or element-set identifier", 42),
                    ("side_id", "Local side/face label such as S1", "S1"),
                ),
                "examples": (
                    {"element_id": 42, "side_id": "S1"},
                    {"element_id": 43, "side_id": "S2"},
                ),
            },
        ),
        "commands": ("SURFACE",),
    },
    "surfaces.set": {
        "template": (
            "*SFSET, SFSET={set_name}\n"
            "{for member in members}\n"
            "{member.surface_id}\n"
            "{endfor}"
        ),
        "fields": (
            ("set_name", "Surface-set name", "CONTACT_FACE"),
            ("generate_start", "GENERATE start surface ID", 0),
            ("generate_end", "GENERATE inclusive end surface ID", 10),
            ("generate_increment", "GENERATE increment", 1),
        ),
        "loops": (
            {
                "collection": "members",
                "item": "member",
                "description": "Existing native surface entities grouped by SFSET.",
                "fields": (("surface_id", "Explicit surface identifier", 0),),
                "examples": ({"surface_id": 0}, {"surface_id": 1}),
            },
        ),
        "commands": ("SFSET",),
    },
    "reference_points": {
        "template": "*NODE, NSET={reference_name}\n{node_id}, {x}, {y}, {z}",
        "fields": (
            ("reference_name", "Reference-point node-set name", "RP-1"),
            ("node_id", "Generated solver node identifier", 900001),
            ("x", "Global X coordinate", 0.0),
            ("y", "Global Y coordinate", 0.0),
            ("z", "Global Z coordinate", 25.0),
        ),
        "loops": (),
        "commands": ("NODE",),
    },
    "point_masses": {
        "template": (
            "*POINTMASS, NSET={node_set}\n"
            "{mass}, {ix}, {iy}, {iz}, "
            "{kx}, {ky}, {kz}, {krx}, {kry}, {krz}"
        ),
        "fields": (
            ("node_set", "Target node set", "PAYLOAD"),
            ("mass", "Translational point mass per target node", 0.025),
            ("ix", "Rotary inertia Ix", 0.0012),
            ("iy", "Rotary inertia Iy", 0.0012),
            ("iz", "Rotary inertia Iz", 0.002),
            ("kx", "Translational spring stiffness Kx", 1000.0),
            ("ky", "Translational spring stiffness Ky", 1000.0),
            ("kz", "Translational spring stiffness Kz", 0.0),
            ("krx", "Rotational spring stiffness Krx", 0.0),
            ("kry", "Rotational spring stiffness Kry", 0.0),
            ("krz", "Rotational spring stiffness Krz", 0.0),
        ),
        "loops": (),
        "commands": ("POINTMASS",),
    },
}
