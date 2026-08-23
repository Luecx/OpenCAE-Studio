"""Static UI catalog used by the first deck-format editor prototype.

The real format/profile domain model is intentionally not introduced here yet.
This module only supplies representative current OpenCAE record groups, default
templates, and placeholder metadata so the editor can be evaluated in the app.
"""

from __future__ import annotations

from collections import defaultdict


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
            {"key": "mesh.elements", "label": "Elements"},
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
    {"key": "coordinate_systems", "label": "Coordinate Systems"},
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


TEMPLATE_SPECS = {
    "mesh.nodes": {
        "template": "*NODE\n{node_id}, {x}, {y}, {z}",
        "fields": (
            ("node_id", "Solver node identifier", "101"),
            ("x", "Global X coordinate", "0.0"),
            ("y", "Global Y coordinate", "12.5"),
            ("z", "Global Z coordinate", "4.0"),
        ),
    },
    "mesh.elements": {
        "template": "*ELEMENT, TYPE={element_type}\n{element_id}, {connectivity}",
        "fields": (
            ("element_type", "Formatted element type", "C3D4"),
            ("element_id", "Solver element identifier", "42"),
            ("connectivity", "Comma-separated node connectivity", "101, 102, 103, 104"),
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
        "template": "*SURFACE, NAME={surface_name}\n{surface_entries}",
        "fields": (
            ("surface_name", "Surface name", "PRESSURE_FACE"),
            ("surface_entries", "Formatted surface facets", "SOLID, S1"),
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
        "fields": (("thermal_expansion", "Thermal expansion coefficient", "1.2e-5"),),
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
        "template": "*SHELL SECTION, ELSET={element_set}, MATERIAL={material_name}\n{thickness}",
        "fields": (
            ("element_set", "Assigned element-set name", "SKIN"),
            ("material_name", "Referenced material name", "STEEL"),
            ("thickness", "Shell thickness", "2.0"),
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


GLOBAL_PAGES = {
    "general.formatting": "Formatting",
    "general.comments": "Comments",
    "general.output": "Output Style",
}


def template_spec(key: str, label: str) -> dict:
    """Return a representative template specification for one tree leaf."""
    if key in TEMPLATE_SPECS:
        return TEMPLATE_SPECS[key]
    field_name = label.lower().replace(" ", "_").replace("-", "_") + "_name"
    return {
        "template": f"*{label.upper().replace(' ', '')}, NAME={{{field_name}}}",
        "fields": ((field_name, f"{label} name", label.upper().replace(" ", "_")),),
    }


def render_preview(template: str, fields: tuple[tuple[str, str, str], ...]) -> str:
    """Render a live prototype preview from the field example values."""
    values = defaultdict(lambda: "…")
    values.update({name: example for name, _description, example in fields})
    try:
        return template.format_map(values)
    except (ValueError, KeyError):
        return template
