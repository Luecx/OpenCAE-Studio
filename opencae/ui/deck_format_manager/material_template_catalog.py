"""Define material-property templates used by the deck-format editor."""

from __future__ import annotations


TEMPLATE_SPECS = {
    "materials.header": {
        "template": "*MATERIAL, NAME={material_name}",
        "fields": (("material_name", "Material name", "STEEL"),),
        "loops": (),
        "commands": ("MATERIAL",),
    },
    "materials.elastic.isotropic": {
        "template": "*ELASTIC, TYPE=ISOTROPIC\n{youngs_modulus}, {poisson_ratio}",
        "fields": (
            ("youngs_modulus", "Young's modulus E", 210000.0),
            ("poisson_ratio", "Poisson ratio nu", 0.3),
            ("material_name", "Current material name", "STEEL"),
        ),
        "loops": (),
        "commands": ("ELASTIC",),
    },
    "materials.elastic.generalised_isotropic": {
        "template": (
            "*ELASTIC, TYPE=GENISO\n"
            "{youngs_modulus}, {poisson_ratio}, {shear_modulus}"
        ),
        "fields": (
            ("youngs_modulus", "Young's modulus E", 210000.0),
            ("poisson_ratio", "Poisson ratio nu", 0.3),
            ("shear_modulus", "Independent shear modulus G", 80000.0),
        ),
        "loops": (),
        "commands": ("ELASTIC",),
    },
    "materials.elastic.engineering_constants": {
        "template": (
            "*ELASTIC, TYPE=ENGINEERINGCONSTANTS\n"
            "{e1}, {e2}, {e3}, {nu12}, {nu13}, {nu23}, "
            "{g12}, {g13}, {g23}"
        ),
        "fields": (
            ("e1", "Young's modulus E1", 135000.0),
            ("e2", "Young's modulus E2", 10000.0),
            ("e3", "Young's modulus E3", 10000.0),
            ("nu12", "Poisson ratio nu12", 0.3),
            ("nu13", "Poisson ratio nu13", 0.3),
            ("nu23", "Poisson ratio nu23", 0.4),
            ("g12", "Shear modulus G12", 5000.0),
            ("g13", "Shear modulus G13", 5000.0),
            ("g23", "Shear modulus G23", 3500.0),
        ),
        "loops": (),
        "commands": ("ELASTIC",),
    },
    "materials.elastic.orthotropic_stiffness": {
        "template": (
            "*ELASTIC, TYPE=ORTHOTROPIC\n"
            "{d1111}, {d1122}, {d2222}, {d1133}, {d2233}, {d3333}, "
            "{d1212}, {d1313}, {d2323}"
        ),
        "fields": (
            ("d1111", "Orthotropic stiffness D1111", 150000.0),
            ("d1122", "Orthotropic stiffness D1122", 5000.0),
            ("d2222", "Orthotropic stiffness D2222", 12000.0),
            ("d1133", "Orthotropic stiffness D1133", 5000.0),
            ("d2233", "Orthotropic stiffness D2233", 4500.0),
            ("d3333", "Orthotropic stiffness D3333", 12000.0),
            ("d1212", "Orthotropic shear stiffness D1212", 5000.0),
            ("d1313", "Orthotropic shear stiffness D1313", 5000.0),
            ("d2323", "Orthotropic shear stiffness D2323", 3500.0),
        ),
        "loops": (),
        "commands": ("ELASTIC",),
    },
    "materials.hyperelastic.neo_hooke": {
        "template": "*HYPERELASTIC, NEOHOOKE\n{c10}, {d1}",
        "fields": (
            ("c10", "Neo-Hooke deviatoric coefficient C10", 0.348),
            ("d1", "Neo-Hooke compressibility coefficient D1", 5.0e-6),
        ),
        "loops": (),
        "commands": ("HYPERELASTIC",),
    },
    "materials.density": {
        "template": "*DENSITY\n{density}",
        "fields": (("density", "Material mass density", 7.85e-9),),
        "loops": (),
        "commands": ("DENSITY",),
    },
    "materials.thermal_expansion": {
        "template": "*THERMALEXPANSION\n{thermal_expansion}",
        "fields": (
            ("thermal_expansion", "Constant isotropic expansion coefficient", 1.2e-5),
        ),
        "loops": (),
        "commands": ("THERMALEXPANSION",),
    },
    "materials.plasticity": {
        "template": (
            "*PLASTIC\n"
            "{for point in points}\n"
            "{point.yield_stress}, {point.plastic_strain}\n"
            "{endfor}"
        ),
        "fields": (),
        "loops": (
            {
                "collection": "points",
                "item": "point",
                "description": "Abaqus plastic hardening points.",
                "fields": (
                    ("yield_stress", "Yield stress", 355.0),
                    ("plastic_strain", "Equivalent plastic strain", 0.0),
                ),
                "examples": (
                    {"yield_stress": 355.0, "plastic_strain": 0.0},
                    {"yield_stress": 410.0, "plastic_strain": 0.02},
                ),
            },
        ),
        "commands": ("PLASTIC",),
    },
}
