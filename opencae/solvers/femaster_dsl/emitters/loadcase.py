from ..command import command

_TYPES = {"Linear Static": "LINEARSTATIC", "Linear Static Topology": "LINEARSTATICTOPO", "Nonlinear Static": "NONLINEARSTATIC", "Eigenfrequency": "EIGENFREQ", "Linear Buckling": "LINEARBUCKLING", "Transient": "LINEARTRANSIENT", "Linear Transient": "LINEARTRANSIENT"}


def write_step(step, writer, context):
    command(writer, "LOADCASE", TYPE=_TYPES.get(step.step_type, "LINEARSTATIC"), NAME=step.name)
    if step.active_supports: command(writer, "SUPPORTS", [(name,) for name in step.active_supports])
    if step.uses_loads and step.active_loads: command(writer, "LOADS", [(name,) for name in step.active_loads])
    settings = step.settings
    if step.step_type in {"Linear Static", "Nonlinear Static", "Linear Buckling", "Transient"}:
        command(writer, "SOLVER", DEVICE=settings.get("device", "CPU"), METHOD=settings.get("method", "DIRECT"))
    if step.step_type in {"Linear Static", "Linear Static Topology", "Nonlinear Static"}:
        command(writer, "CONSTRAINTMETHOD", TYPE=settings.get("constraint_method", "NULLSPACE"))
    if step.step_type in {"Eigenfrequency", "Linear Buckling"}: command(writer, "NUMEIGENVALUES", [(step.number_of_modes,)])
    if step.step_type == "Nonlinear Static":
        command(writer, "NONLINEAR", CONTROL=settings.get("control", "LOAD"), INITIAL_INCREMENT=settings.get("initial_increment", 0.1), MINIMUM_INCREMENT=settings.get("minimum_increment", 1e-6), MAXIMUM_INCREMENT=settings.get("maximum_increment", 0.1), MAX_INCREMENTS=settings.get("max_increments", 100), ADAPTIVE=settings.get("adaptive", True), MAXITER=settings.get("max_iterations", 25), TOL=settings.get("tolerance", 1e-8), REGULARIZE_ZERO_ROWS=settings.get("regularize_zero_rows", False), ARC_LENGTH_PSI=settings.get("arc_length_psi") if settings.get("control") == "ARC_LENGTH" else None)
    if step.step_type == "Transient":
        command(writer, "TIME", [(settings.get("start_time", 0.0), step.time_period, settings.get("time_step", 0.01))])
        command(writer, "NEWMARK", [(settings.get("newmark_beta", 0.25), settings.get("newmark_gamma", 0.5))])
        command(writer, "DAMPING", [(settings.get("rayleigh_alpha", 0.0), settings.get("rayleigh_beta", 0.0))], TYPE="RAYLEIGH")
        command(writer, "WRITEEVERY", [(settings.get("write_every", 1),)], TYPE="STEPS")
