"""Define native FEMaster loadcase, numerical-control and diagnostic templates."""

from __future__ import annotations


_LOADCASE_TYPES = {
    "linear_static": "LINEARSTATIC",
    "nonlinear_static": "NONLINEARSTATIC",
    "linear_buckling": "LINEARBUCKLING",
    "topology_static": "LINEARSTATICTOPO",
    "eigenfrequency": "EIGENFREQ",
    "linear_transient": "LINEARTRANSIENT",
    "linear_harmonic": "LINEARHARMONIC",
}


def loadcase_template_specs() -> dict[str, dict]:
    """Return one literal LOADCASE header for every documented analysis type."""
    return {
        f"analysis.loadcases.{key}": {
            "template": f"*LOADCASE, TYPE={kind}, NAME={{loadcase_name}}",
            "fields": (("loadcase_name", "Optional loadcase name", "SERVICE_LOAD"),),
            "loops": (),
            "commands": ("LOADCASE",),
        }
        for key, kind in _LOADCASE_TYPES.items()
    }


def _collector_selection(command: str, collection: str, item: str) -> dict:
    """Build a SUPPORTS or LOADS collector-selection record."""
    return {
        "template": (
            f"*{command}\n"
            f"{{for {item} in {collection}}}\n"
            f"{{{item}.name}}\n"
            "{endfor}"
        ),
        "fields": (),
        "loops": (
            {
                "collection": collection,
                "item": item,
                "description": f"Collector names selected by {command}.",
                "fields": (("name", "Collector name", "SERVICE"),),
                "examples": ({"name": "SERVICE"}, {"name": "PERMANENT"}),
            },
        ),
        "commands": (command,),
    }


TEMPLATE_SPECS = {
    "analysis.selections.supports": _collector_selection(
        "SUPPORTS", "support_collectors", "collector"
    ),
    "analysis.selections.loads": _collector_selection(
        "LOADS", "load_collectors", "collector"
    ),
    "analysis.controls.solver": {
        "template": "*SOLVER, DEVICE={device}, METHOD={method}",
        "fields": (
            ("device", "CPU or GPU", "CPU"),
            ("method", "DIRECT or INDIRECT", "DIRECT"),
        ),
        "loops": (),
        "commands": ("SOLVER",),
    },
    "analysis.controls.constraint_method": {
        "template": "*CONSTRAINTMETHOD, TYPE={method}",
        "fields": (
            ("method", "NULLSPACE, LAGRANGE or ELIMINATION", "NULLSPACE"),
        ),
        "loops": (),
        "commands": ("CONSTRAINTMETHOD",),
    },
    "analysis.controls.nonlinear": {
        "template": (
            "*NONLINEAR, CONTROL={control}, MAX_INCREMENTS={max_increments},\n"
            " INITIAL_INCREMENT={initial_increment}, MINIMUM_INCREMENT={minimum_increment},\n"
            " MAXIMUM_INCREMENT={maximum_increment}, MAXITER={max_iterations},\n"
            " TOL={tolerance}, ADAPTIVE={adaptive}"
        ),
        "fields": (
            ("control", "LOAD or ARC_LENGTH", "LOAD"),
            ("increments", "Legacy INCREMENTS shorthand", 20),
            ("max_increments", "Maximum accepted nonlinear increments", 100),
            ("initial_increment", "Initial load/arc-length step", 0.05),
            ("minimum_increment", "Minimum adaptive increment", 1.0e-5),
            ("maximum_increment", "Maximum adaptive increment", 0.1),
            ("arc_length_psi", "Arc-length load weighting", 1.0),
            ("adaptive", "Adaptive stepping ON or OFF", "ON"),
            ("growth_factor", "Fast-convergence growth factor", 1.5),
            ("cutback_factor", "Rejected-step cutback factor", 0.5),
            ("fast_iterations", "Fast convergence threshold", 6),
            ("slow_iterations", "Slow convergence threshold", 10),
            ("maximum_cutbacks", "Maximum repeated cutbacks", 20),
            ("max_iterations", "Newton iteration limit per attempted increment", 20),
            ("tolerance", "Equilibrium convergence tolerance", 1.0e-8),
            ("regularize_zero_rows", "Weak-row regularization ON or OFF", "ON"),
            ("regularization_alpha", "Weak-row regularization scale", 1.0e-4),
        ),
        "loops": (),
        "commands": ("NONLINEAR",),
    },
    "analysis.controls.time": {
        "template": "*TIME\n{start_time}, {end_time}, {time_increment}",
        "fields": (
            ("start_time", "Transient start time", 0.0),
            ("end_time", "Transient end time", 2.0),
            ("time_increment", "Fixed integration time step", 0.005),
        ),
        "loops": (),
        "commands": ("TIME",),
    },
    "analysis.controls.newmark": {
        "template": "*NEWMARK\n{beta}, {gamma}",
        "fields": (
            ("beta", "Newmark beta", 0.25),
            ("gamma", "Newmark gamma", 0.5),
        ),
        "loops": (),
        "commands": ("NEWMARK",),
    },
    "analysis.controls.damping": {
        "template": "*DAMPING, TYPE=RAYLEIGH\n{alpha}, {beta}",
        "fields": (
            ("alpha", "Mass-proportional Rayleigh coefficient", 0.0),
            ("beta", "Stiffness-proportional Rayleigh coefficient", 1.0e-5),
        ),
        "loops": (),
        "commands": ("DAMPING",),
    },
    "analysis.controls.frequencies": {
        "template": "*FREQUENCIES, SCALE=LINEAR\n{start}, {end}, {count}",
        "fields": (
            ("start", "First excitation frequency", 10.0),
            ("end", "Last excitation frequency", 1000.0),
            ("count", "Number of frequency points", 100),
            ("scale", "Frequency spacing; currently LINEAR", "LINEAR"),
        ),
        "loops": (),
        "commands": ("FREQUENCIES",),
    },
    "analysis.controls.num_eigenvalues": {
        "template": "*NUMEIGENVALUES\n{count}",
        "fields": (("count", "Positive number of requested eigenpairs", 10),),
        "loops": (),
        "commands": ("NUMEIGENVALUES",),
    },
    "analysis.controls.sigma": {
        "template": "*SIGMA\n{sigma}",
        "fields": (("sigma", "Buckling spectral shift; zero selects automatic strategy", 0.0),),
        "loops": (),
        "commands": ("SIGMA",),
    },
    "analysis.controls.write_every": {
        "template": "*WRITEEVERY, TYPE={mode}\n{interval}",
        "fields": (
            ("mode", "STEPS or TIME", "STEPS"),
            ("interval", "Step count or physical-time output interval", 10),
        ),
        "loops": (),
        "commands": ("WRITEEVERY",),
    },
    "analysis.controls.initial_velocity": {
        "template": "*INITIALVELOCITY, FIELD={field_name}",
        "fields": (
            ("field_name", "Six-component NODE initial-velocity Field", "V0"),
        ),
        "loops": (),
        "commands": ("INITIALVELOCITY",),
    },
    "analysis.controls.inertia_relief": {
        "template": "*INERTIARELIEF, CONSIDER_POINT_MASSES={consider_point_masses}",
        "fields": (("consider_point_masses", "Include POINTMASS features: 0 or 1", 1),),
        "loops": (),
        "commands": ("INERTIARELIEF",),
    },
    "analysis.controls.rebalance_loads": {
        "template": "*REBALANCELOADS",
        "fields": (),
        "loops": (),
        "commands": ("REBALANCELOADS",),
    },
    "analysis.topology.density": {
        "template": "*TOPODENSITY, FIELD={field_name}",
        "fields": (("field_name", "Scalar ELEMENT density Field", "RHO"),),
        "loops": (),
        "commands": ("TOPODENSITY",),
    },
    "analysis.topology.orientation": {
        "template": "*TOPOORIENT, FIELD={field_name}",
        "fields": (("field_name", "Three-component ELEMENT orientation Field", "ORIENT"),),
        "loops": (),
        "commands": ("TOPOORIENT",),
    },
    "analysis.topology.exponent": {
        "template": "*TOPOEXPONENT\n{exponent}",
        "fields": (("exponent", "Topology stiffness penalization exponent", 3.0),),
        "loops": (),
        "commands": ("TOPOEXPONENT",),
    },
    "analysis.diagnostics.overview": {
        "template": "*OVERVIEW",
        "fields": (),
        "loops": (),
        "commands": ("OVERVIEW",),
    },
    "analysis.diagnostics.stiffness": {
        "template": "*REQUESTSTIFFNESS, FILE={file_name}",
        "fields": (("file_name", "Optional stiffness-matrix output filename", "K.txt"),),
        "loops": (),
        "commands": ("REQUESTSTIFFNESS",),
    },
    "analysis.diagnostics.geometric_stiffness": {
        "template": "*REQUESTSTGEOM, FILE={file_name}",
        "fields": (("file_name", "Optional geometric-stiffness output filename", "KG.txt"),),
        "loops": (),
        "commands": ("REQUESTSTGEOM",),
    },
    "analysis.diagnostics.constraint_summary": {
        "template": "*CONSTRAINTSUMMARY",
        "fields": (),
        "loops": (),
        "commands": ("CONSTRAINTSUMMARY",),
    },
    "analysis.end": {
        "template": "*END",
        "fields": (),
        "loops": (),
        "commands": ("END",),
    },
}
TEMPLATE_SPECS.update(loadcase_template_specs())
