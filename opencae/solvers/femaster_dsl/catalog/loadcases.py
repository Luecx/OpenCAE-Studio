from ..spec import CommandSpec

COMMANDS = (
    CommandSpec("LOADCASE", frozenset({"TYPE", "NAME"}), frozenset({"TYPE"}), variants=("LINEARSTATIC", "LINEARSTATICTOPO", "NONLINEARSTATIC", "EIGENFREQ", "LINEARBUCKLING", "LINEARTRANSIENT")),
    CommandSpec("END"), CommandSpec("SUPPORTS"), CommandSpec("LOADS"),
    CommandSpec("SOLVER", frozenset({"DEVICE", "METHOD"}), variants=("CPU", "GPU", "DIRECT", "ITERATIVE")),
    CommandSpec("CONSTRAINTMETHOD", frozenset({"TYPE"}), variants=("NULLSPACE", "LAGRANGE", "ELIMINATION")),
    CommandSpec("NONLINEAR", frozenset({"CONTROL", "ARC_LENGTH_PSI", "INITIAL_INCREMENT", "MINIMUM_INCREMENT", "MAXIMUM_INCREMENT", "MAX_INCREMENTS", "ADAPTIVE", "MAXITER", "TOL", "REGULARIZE_ZERO_ROWS"})),
    CommandSpec("INERTIARELIEF", frozenset({"CONSIDER_POINT_MASSES"})),
    CommandSpec("REBALANCELOADS"), CommandSpec("REQUESTSTIFFNESS"), CommandSpec("REQUESTSTGEOM"),
    CommandSpec("NUMEIGENVALUES"), CommandSpec("SIGMA"),
    CommandSpec("TOPODENSITY", frozenset({"FIELD"}), frozenset({"FIELD"})),
    CommandSpec("TOPOORIENT", frozenset({"FIELD"}), frozenset({"FIELD"})), CommandSpec("TOPOEXPONENT"),
    CommandSpec("TIME"), CommandSpec("NEWMARK"), CommandSpec("DAMPING", frozenset({"TYPE"}), variants=("RAYLEIGH",)),
    CommandSpec("WRITEEVERY", frozenset({"TYPE"}), variants=("STEPS", "TIME")),
    CommandSpec("INITIALVELOCITY", frozenset({"FIELD"}), frozenset({"FIELD"})),
    CommandSpec("CONSTRAINTSUMMARY"), CommandSpec("OVERVIEW"),
)
