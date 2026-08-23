"""Provide representative record templates and placeholder documentation."""

from .element_type_catalog import element_template_specs


TEMPLATE_SPECS = {
    "mesh.nodes": {
        "template": (
            "*NODE\n"
            "{for node in nodes}\n"
            "{node.id}, {node.x}, {node.y}, {node.z}\n"
            "{endfor}"
        ),
        "fields": (),
        "loops": (
            {
                "collection": "nodes",
                "item": "node",
                "description": "Nodes written by this record.",
                "fields": (
                    ("id", "Solver node identifier", "101"),
                    ("x", "Global X coordinate", "0.0"),
                    ("y", "Global Y coordinate", "12.5"),
                    ("z", "Global Z coordinate", "4.0"),
                ),
                "examples": (
                    {"id": "101", "x": "0.0", "y": "12.5", "z": "4.0"},
                    {"id": "102", "x": "8.0", "y": "12.5", "z": "4.0"},
                ),
            },
        ),
    },
    "node_sets": {
        "template": "*NSET, NSET={set_name}\n{node_ids}",
        "fields": (
            ("set_name", "Node-set name", "FIXED_NODES"),
            ("node_ids", "Formatted node identifiers", "101, 102, 103"),
        ),
    },
    "element_sets": {
        "template": "*ELSET, ELSET={set_name}\n{element_ids}",
        "fields": (
            ("set_name", "Element-set name", "SOLID"),
            ("element_ids", "Formatted element identifiers", "42, 43"),
        ),
    },
    "surfaces": {
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
                    (
                        "element_id",
                        "Element identifier for one surface facet",
                        "42",
                    ),
                    ("side_id", "Local side/face identifier on that element", "S1"),
                ),
                "examples": (
                    {"element_id": "42", "side_id": "S1"},
                    {"element_id": "43", "side_id": "S2"},
                ),
            },
        ),
    },
    "materials.header": {
        "template": "*MATERIAL, NAME={material_name}",
        "fields": (("material_name", "Material name", "STEEL"),),
    },
    "materials.isotropic_elastic": {
        "template": "*ELASTIC, TYPE=ISO\n{youngs_modulus}, {poisson_ratio}",
        "fields": (
            ("youngs_modulus", "Young's modulus E", "210000"),
            ("poisson_ratio", "Poisson ratio ν", "0.3"),
            ("material_name", "Current material name", "STEEL"),
            ("temperature", "Optional temperature value", "20"),
        ),
    },
    "materials.density": {
        "template": "*DENSITY\n{density}",
        "fields": (("density", "Material mass density", "7.85e-9"),),
    },
    "materials.plasticity": {
        "template": "*PLASTIC\n{yield_stress}, {plastic_strain}",
        "fields": (
            ("yield_stress", "Yield stress", "355"),
            ("plastic_strain", "Equivalent plastic strain", "0.0"),
        ),
    },
    "materials.thermal_expansion": {
        "template": "*EXPANSION\n{thermal_expansion}",
        "fields": (
            ("thermal_expansion", "Thermal expansion coefficient", "1.2e-5"),
        ),
    },
    "sections.solid": {
        "template": "*SOLID SECTION, ELSET={element_set}, MATERIAL={material_name}",
        "fields": (
            ("element_set", "Assigned element-set name", "SOLID"),
            ("material_name", "Referenced material name", "STEEL"),
            ("section_name", "OpenCAE section name", "SECTION-1"),
        ),
    },
    "sections.shell": {
        "template": (
            "*SHELL SECTION, ELSET={element_set}, MATERIAL={material_name}\n"
            "{thickness}"
        ),
        "fields": (
            ("element_set", "Assigned element-set name", "SKIN"),
            ("material_name", "Referenced material name", "STEEL"),
            ("thickness", "Shell thickness", "2.0"),
        ),
    },
    "fields": {
        "template": "*FIELD, NAME={field_name}, TYPE={location}, COLS={components}",
        "fields": (
            ("field_name", "Field definition name", "TEMPERATURE"),
            ("location", "Field location", "NODE"),
            ("components", "Number of field components", "1"),
        ),
    },
    "coordinate_systems": {
        "template": "*ORIENTATION, NAME={name}\n{axis_1}, {axis_2}",
        "fields": (
            ("name", "Coordinate-system name", "LOCAL-1"),
            ("axis_1", "First orientation vector", "1, 0, 0"),
            ("axis_2", "Second orientation vector", "0, 1, 0"),
        ),
    },
    "reference_points": {
        "template": "*NODE, NSET={reference_name}\n{node_id}, {x}, {y}, {z}",
        "fields": (
            ("reference_name", "Reference-point name", "RP-1"),
            ("node_id", "Generated solver node identifier", "900001"),
            ("x", "Global X coordinate", "0"),
            ("y", "Global Y coordinate", "0"),
            ("z", "Global Z coordinate", "25"),
        ),
    },
    "constraints.kinematic": {
        "template": "*COUPLING, MASTER={master}, SLAVE={slave}, TYPE=KINEMATIC",
        "fields": (
            ("master", "Resolved master node/set name", "RP_1"),
            ("slave", "Resolved slave node-set name", "COUPLED"),
        ),
    },
    "boundary_conditions.fixed": {
        "template": "*BOUNDARY\n{node_set}, 1, 6, 0",
        "fields": (("node_set", "Resolved node-set name", "FIXED_NODES"),),
    },
    "loads.pressure": {
        "template": "*PLOAD, LOAD_COLLECTOR={load_name}\n{surface_name}, {pressure}",
        "fields": (
            ("load_name", "Load name", "Pressure-1"),
            ("surface_name", "Resolved surface name", "PRESSURE_FACE"),
            ("pressure", "Pressure magnitude", "12.5"),
        ),
    },
    "analysis.step": {
        "template": "*LOADCASE, NAME={step_name}, TYPE={step_type}",
        "fields": (
            ("step_name", "Analysis-step name", "Step-1"),
            ("step_type", "Formatted solver step type", "LINEARSTATIC"),
        ),
    },
}

TEMPLATE_SPECS.update(element_template_specs())
