"""Define native FEMaster amplitude, support and load record templates."""

from __future__ import annotations


_SUPPORT_FIELDS = (
    ("support_collector", "Destination support collector", "BC"),
    ("target", "Node ID or node-set target", "FIXED"),
    ("ux", "Prescribed Ux; NAN means free", 0.0),
    ("uy", "Prescribed Uy; NAN means free", 0.0),
    ("uz", "Prescribed Uz; NAN means free", 0.0),
    ("rx", "Prescribed Rx; NAN means free", "NAN"),
    ("ry", "Prescribed Ry; NAN means free", "NAN"),
    ("rz", "Prescribed Rz; NAN means free", "NAN"),
    ("orientation", "Optional local coordinate-system name", "LOCAL-1"),
)


def _support_template(values: tuple[str, ...]) -> str:
    """Build one SUPPORT row with six generalized components."""
    return (
        "*SUPPORT, SUPPORT_COLLECTOR={support_collector}\n"
        "{target}, " + ", ".join(values)
    )


TEMPLATE_SPECS = {
    "loads.amplitude": {
        "template": (
            "*AMPLITUDE, NAME={amplitude_name}, TYPE={interpolation}\n"
            "{for sample in samples}\n"
            "{sample.abscissa}, {sample.value}\n"
            "{endfor}"
        ),
        "fields": (
            ("amplitude_name", "Amplitude name", "RAMP"),
            ("interpolation", "LINEAR, STEP or NEAREST", "LINEAR"),
        ),
        "loops": (
            {
                "collection": "samples",
                "item": "sample",
                "description": "Amplitude abscissa/value samples.",
                "fields": (
                    ("abscissa", "Time or analysis-variable sample", 0.0),
                    ("value", "Scalar amplitude value", 0.0),
                ),
                "examples": (
                    {"abscissa": 0.0, "value": 0.0},
                    {"abscissa": 0.1, "value": 1.0},
                    {"abscissa": 1.0, "value": 1.0},
                ),
            },
        ),
        "commands": ("AMPLITUDE",),
    },
    "boundary_conditions.fixed": {
        "template": _support_template(("0.", "0.", "0.", "0.", "0.", "0.")),
        "fields": _SUPPORT_FIELDS,
        "loops": (),
        "commands": ("SUPPORT",),
    },
    "boundary_conditions.displacement": {
        "template": _support_template(
            ("{ux}", "{uy}", "{uz}", "{rx}", "{ry}", "{rz}")
        ),
        "fields": _SUPPORT_FIELDS,
        "loops": (),
        "commands": ("SUPPORT",),
    },
    "boundary_conditions.symmetry": {
        "template": _support_template(
            ("{ux}", "{uy}", "{uz}", "{rx}", "{ry}", "{rz}")
        ),
        "fields": _SUPPORT_FIELDS,
        "loops": (),
        "commands": ("SUPPORT",),
    },
    "loads.concentrated": {
        "template": (
            "*CLOAD, LOAD_COLLECTOR={load_collector}\n"
            "{target}, {fx}, {fy}, {fz}, {mx}, {my}, {mz}"
        ),
        "fields": (
            ("load_collector", "Destination load collector", "TIP_LOAD"),
            ("target", "Node ID or node-set target", "TIP"),
            ("fx", "Force X component", 1000.0),
            ("fy", "Force Y component", -250.0),
            ("fz", "Force Z component", 0.0),
            ("mx", "Moment X component", 0.0),
            ("my", "Moment Y component", 0.0),
            ("mz", "Moment Z component", 0.0),
            ("orientation", "Optional local load basis", "LOCAL-1"),
            ("amplitude", "Optional amplitude name", "RAMP"),
        ),
        "loops": (),
        "commands": ("CLOAD",),
    },
    "loads.distributed": {
        "template": (
            "*DLOAD, LOAD_COLLECTOR={load_collector}\n"
            "{surface}, {tx}, {ty}, {tz}"
        ),
        "fields": (
            ("load_collector", "Destination load collector", "TRACTION"),
            ("surface", "Surface or surface-set target", "SIDE"),
            ("tx", "Traction X component", 0.0),
            ("ty", "Traction Y component", 2.5),
            ("tz", "Traction Z component", 0.0),
            ("orientation", "Optional local traction basis", "LOCAL-1"),
            ("amplitude", "Optional amplitude name", "RAMP"),
        ),
        "loops": (),
        "commands": ("DLOAD",),
    },
    "loads.pressure": {
        "template": (
            "*PLOAD, LOAD_COLLECTOR={load_collector}\n"
            "{surface}, {pressure}"
        ),
        "fields": (
            ("load_collector", "Destination load collector", "PRESSURE"),
            ("surface", "Surface or surface-set target", "INNER_FACE"),
            ("pressure", "Scalar pressure magnitude", 2.0),
            ("amplitude", "Optional amplitude name", "RAMP"),
        ),
        "loops": (),
        "commands": ("PLOAD",),
    },
    "loads.volume": {
        "template": (
            "*VLOAD, LOAD_COLLECTOR={load_collector}\n"
            "{element_target}, {x}, {y}, {z}"
        ),
        "fields": (
            ("load_collector", "Destination load collector", "GRAVITY"),
            ("element_target", "Element ID or element-set target", "EALL"),
            ("x", "Volumetric acceleration/body-force X component", 0.0),
            ("y", "Volumetric acceleration/body-force Y component", 0.0),
            ("z", "Volumetric acceleration/body-force Z component", -9810.0),
            ("orientation", "Optional local vector basis", "LOCAL-1"),
            ("amplitude", "Optional amplitude name", "RAMP"),
        ),
        "loops": (),
        "commands": ("VLOAD",),
    },
    "loads.temperature": {
        "template": (
            "*TLOAD, LOAD_COLLECTOR={load_collector}, "
            "TEMPERATUREFIELD={temperature_field}, "
            "REFERENCETEMPERATURE={reference_temperature}"
        ),
        "fields": (
            ("load_collector", "Destination load collector", "THERMAL"),
            ("temperature_field", "Scalar NODE temperature Field", "TEMPERATURE"),
            ("reference_temperature", "Stress-free reference temperature", 20.0),
        ),
        "loops": (),
        "commands": ("TLOAD",),
    },
    "loads.inertia": {
        "template": (
            "*INERTIALOAD, LOAD_COLLECTOR={load_collector}, "
            "CONSIDER_POINT_MASSES={consider_point_masses}\n"
            "{element_set},\n"
            "{cx}, {cy}, {cz},\n"
            "{ax}, {ay}, {az},\n"
            "{wx}, {wy}, {wz},\n"
            "{alpha_x}, {alpha_y}, {alpha_z}"
        ),
        "fields": (
            ("load_collector", "Destination load collector", "ROT_INERTIA"),
            ("consider_point_masses", "Include POINTMASS features: 0 or 1", 1),
            ("element_set", "Target element set", "EALL"),
            ("cx", "Reference centre X", 0.0),
            ("cy", "Reference centre Y", 0.0),
            ("cz", "Reference centre Z", 0.0),
            ("ax", "Centre translational acceleration X", 0.0),
            ("ay", "Centre translational acceleration Y", 0.0),
            ("az", "Centre translational acceleration Z", 0.0),
            ("wx", "Angular velocity X", 0.0),
            ("wy", "Angular velocity Y", 0.0),
            ("wz", "Angular velocity Z", 10.0),
            ("alpha_x", "Angular acceleration X", 0.0),
            ("alpha_y", "Angular acceleration Y", 0.0),
            ("alpha_z", "Angular acceleration Z", 2.0),
        ),
        "loops": (),
        "commands": ("INERTIALOAD",),
    },
}
