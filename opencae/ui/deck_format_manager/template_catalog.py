"""Provide representative FEMaster record templates and input documentation."""

from .element_type_catalog import element_template_specs
from .profile_record_catalog import profile_template_specs


_ORIENTATION_FIELDS = (
    ("name", "Coordinate-system name", "LOCAL-1"),
    ("origin_x", "Origin X coordinate", 0.0),
    ("origin_y", "Origin Y coordinate", 0.0),
    ("origin_z", "Origin Z coordinate", 0.0),
    ("axis_1_x", "First axis X component", 1.0),
    ("axis_1_y", "First axis Y component", 0.0),
    ("axis_1_z", "First axis Z component", 0.0),
    ("axis_2_x", "Second axis X component", 0.0),
    ("axis_2_y", "Second axis Y component", 1.0),
    ("axis_2_z", "Second axis Z component", 0.0),
)


def _orientation_spec(kind: str) -> dict:
    """Return one FEMaster ORIENTATION record with a literal coordinate-system type."""
    return {
        "template": (
            f"*ORIENTATION, NAME={{name}}, TYPE={kind}\n"
            "{origin_x}, {origin_y}, {origin_z}, "
            "{axis_1_x}, {axis_1_y}, {axis_1_z}, "
            "{axis_2_x}, {axis_2_y}, {axis_2_z}"
        ),
        "fields": _ORIENTATION_FIELDS,
        "loops": (),
    }


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
                    ("element_id", "Element identifier for one surface facet", 42),
                    ("side_id", "Local side/face identifier on that element", "S1"),
                ),
                "examples": (
                    {"element_id": 42, "side_id": "S1"},
                    {"element_id": 43, "side_id": "S2"},
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
            ("youngs_modulus", "Young's modulus E", 210000.0),
            ("poisson_ratio", "Poisson ratio ν", 0.3),
            ("material_name", "Current material name", "STEEL"),
            ("temperature", "Optional temperature value", 20.0),
        ),
    },
    "materials.density": {
        "template": "*DENSITY\n{density}",
        "fields": (("density", "Material mass density", 7.85e-9),),
    },
    "materials.plasticity": {
        "template": "*PLASTIC\n{yield_stress}, {plastic_strain}",
        "fields": (
            ("yield_stress", "Yield stress", 355.0),
            ("plastic_strain", "Equivalent plastic strain", 0.0),
        ),
    },
    "materials.thermal_expansion": {
        "template": "*EXPANSION\n{thermal_expansion}",
        "fields": (("thermal_expansion", "Thermal expansion coefficient", 1.2e-5),),
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
            ("thickness", "Shell thickness", 2.0),
        ),
    },
    "fields": {
        "template": (
            "*FIELD, NAME={field_name}, TYPE={location}, COLS={components}, FILL={fill_value}\n"
            "{for row in rows}\n"
            "{row.entity_id}, {row.values}\n"
            "{endfor}"
        ),
        "fields": (
            ("field_name", "Field definition name", "TEMPERATURE"),
            ("location", "Field location: NODE, ELEMENT or ELEMENT_NODAL", "NODE"),
            ("components", "Number of values after each entity id", 2),
            ("fill_value", "Value FEMaster uses for missing components", "NAN"),
        ),
        "loops": (
            {
                "collection": "rows",
                "item": "row",
                "description": "Tabular field values written for solver entities.",
                "fields": (
                    ("entity_id", "Node or element identifier", 101),
                    ("values", "One or more field component values", "2.5, 3.5"),
                ),
                "examples": (
                    {"entity_id": 101, "values": "2.5, 3.5"},
                    {"entity_id": 102, "values": "4.5, 5.5"},
                ),
            },
        ),
    },
    "coordinate_systems.rectangular": _orientation_spec("RECTANGULAR"),
    "coordinate_systems.cylindrical": _orientation_spec("CYLINDRICAL"),
    "reference_points": {
        "template": "*NODE, NSET={reference_name}\n{node_id}, {x}, {y}, {z}",
        "fields": (
            ("reference_name", "Reference-point name", "RP-1"),
            ("node_id", "Generated solver node identifier", 900001),
            ("x", "Global X coordinate", 0.0),
            ("y", "Global Y coordinate", 0.0),
            ("z", "Global Z coordinate", 25.0),
        ),
    },
    "constraints.kinematic": {
        "template": "*COUPLING, MASTER={master}, SLAVE={slave}, TYPE=KINEMATIC",
        "fields": (
            ("master", "Resolved master node/set name", "RP_1"),
            ("slave", "Resolved slave node-set name", "COUPLED"),
        ),
    },
    "constraints.equation": {
        "template": (
            "*EQUATION, NAME={equation_name}\n"
            "{for term in terms}\n"
            "{term.target}, {term.dof}, {term.coefficient}\n"
            "{endfor}"
        ),
        "fields": (("equation_name", "Equation constraint name", "Equation-1"),),
        "loops": (
            {
                "collection": "terms",
                "item": "term",
                "description": "Individual linear equation terms.",
                "fields": (
                    ("target", "Resolved node/reference target", "NODE_A"),
                    ("dof", "Degree of freedom number", 1),
                    ("coefficient", "Linear equation coefficient", 1.0),
                ),
                "examples": (
                    {"target": "NODE_A", "dof": 1, "coefficient": 1.0},
                    {"target": "NODE_B", "dof": 1, "coefficient": -1.0},
                ),
            },
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
            ("pressure", "Pressure magnitude", 12.5),
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
TEMPLATE_SPECS.update(profile_template_specs())
