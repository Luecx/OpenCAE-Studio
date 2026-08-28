"""Emit analysis loadcases and their numerical controls for FEMaster."""

from ..command import command

_TYPES = {
    "Linear Static": "LINEARSTATIC",
    "Linear Static Topology": "LINEARSTATICTOPO",
    "Nonlinear Static": "NONLINEARSTATIC",
    "Eigenfrequency": "EIGENFREQ",
    "Linear Buckling": "LINEARBUCKLING",
    "Transient": "LINEARTRANSIENT",
    "Linear Transient": "LINEARTRANSIENT",
}


def write_step(step, writer, context):
    command(
        writer,
        "LOADCASE",
        TYPE=_TYPES.get(step.step_type, "LINEARSTATIC"),
        NAME=context.solver_name(step, step.name),
    )
    support_names = [
        context.solver_name(entity, entity.name)
        if entity
        else context.current_name(ref)
        for ref in step.support_refs
        for entity in [context.resolve(ref)]
    ]
    load_names = [
        context.solver_name(entity, entity.name)
        if entity
        else context.current_name(ref)
        for ref in step.load_refs
        for entity in [context.resolve(ref)]
    ]
    if support_names:
        command(writer, "SUPPORTS", [(name,) for name in support_names])
    if step.uses_loads and load_names:
        command(writer, "LOADS", [(name,) for name in load_names])

    settings = dict(step.settings or {})
    if step.step_type in {
        "Linear Static",
        "Linear Static Topology",
        "Nonlinear Static",
        "Linear Buckling",
        "Transient",
    }:
        command(
            writer,
            "SOLVER",
            DEVICE=settings.get("device", "CPU"),
            METHOD=settings.get("method", "DIRECT"),
        )
    if step.step_type in {
        "Linear Static",
        "Linear Static Topology",
        "Nonlinear Static",
    }:
        command(
            writer,
            "CONSTRAINTMETHOD",
            TYPE=settings.get("constraint_method", "NULLSPACE"),
        )
    if step.step_type in {"Eigenfrequency", "Linear Buckling"}:
        command(writer, "NUMEIGENVALUES", [(step.number_of_modes,)])
    if step.step_type == "Nonlinear Static":
        _write_nonlinear(step, settings, writer)
    if step.step_type == "Transient":
        command(
            writer,
            "TIME",
            [(
                settings.get("start_time", 0.0),
                step.time_period,
                settings.get("time_step", 0.01),
            )],
        )
        command(
            writer,
            "NEWMARK",
            [(
                settings.get("newmark_beta", 0.25),
                settings.get("newmark_gamma", 0.5),
            )],
        )
        command(
            writer,
            "DAMPING",
            [(
                settings.get("rayleigh_alpha", 0.0),
                settings.get("rayleigh_beta", 0.0),
            )],
            TYPE="RAYLEIGH",
        )
        command(
            writer,
            "WRITEEVERY",
            [(settings.get("write_every", 1),)],
            TYPE="STEPS",
        )


def _write_nonlinear(step, settings, writer):
    """Lower solver-neutral load/path controls into portable FEMaster options.

    The Step model intentionally retains richer adaptive controls.  They are not
    written here until the minimum supported FEMaster executable accepts them;
    emitting a keyword merely because a newer parser knows it makes decks fail on
    otherwise supported installations during analysis preparation.
    """
    control = str(settings.get("control", "LOAD")).upper()
    path_control = control in {"PATH", "ARC_LENGTH"}
    initial = (
        settings.get("initial_arc_length", settings.get("initial_increment", 0.05))
        if path_control
        else settings.get("initial_increment", 0.1)
    )
    minimum = (
        settings.get("minimum_arc_length", settings.get("minimum_increment", 1e-5))
        if path_control
        else settings.get("minimum_increment", 1e-6)
    )
    maximum = (
        settings.get("maximum_arc_length", settings.get("maximum_increment", 0.1))
        if path_control
        else settings.get("maximum_increment", 0.1)
    )
    command(
        writer,
        "NONLINEAR",
        CONTROL="ARC_LENGTH" if path_control else "LOAD",
        INITIAL_INCREMENT=initial,
        MINIMUM_INCREMENT=minimum,
        MAXIMUM_INCREMENT=maximum,
        MAX_INCREMENTS=settings.get("max_increments", 100),
        ADAPTIVE=settings.get("adaptive", True),
        MAXITER=settings.get("max_iterations", 25),
        TOL=settings.get("tolerance", 1e-8),
        REGULARIZE_ZERO_ROWS=settings.get("regularize_zero_rows", False),
        ARC_LENGTH_PSI=(settings.get("arc_length_psi", 1.0) if path_control else None),
    )
