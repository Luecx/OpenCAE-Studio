"""Define the complete solver-neutral nonlinear-control editor record."""

from __future__ import annotations


def nonlinear_template_spec() -> dict:
    """Return the portable FEMaster record plus all persisted semantic fields.

    Some newer FEMaster parsers expose additional adaptive tuning keywords.  The
    editable Step state keeps those values, but the built-in FEMaster template only
    writes the keyword surface accepted by the minimum supported executable.
    """
    return {
        "template": (
            "*NONLINEAR, CONTROL={control}, MAX_INCREMENTS={max_increments}, "
            "INITIAL_INCREMENT={initial_increment}, MINIMUM_INCREMENT={minimum_increment}, "
            "MAXIMUM_INCREMENT={maximum_increment}, MAXITER={max_iterations}, "
            "TOL={tolerance}, ADAPTIVE={adaptive}, "
            "REGULARIZE_ZERO_ROWS={regularize_zero_rows}, ARC_LENGTH_PSI={arc_length_psi}"
        ),
        "fields": (
            ("control", "LOAD or ARC_LENGTH", "LOAD"),
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
            ("max_iterations", "Newton iteration limit per attempted increment", 25),
            ("tolerance", "Equilibrium convergence tolerance", 1.0e-8),
            ("regularize_zero_rows", "Weak-row regularization ON or OFF", "OFF"),
            ("regularization_alpha", "Weak-row regularization scale", 1.0e-4),
        ),
        "loops": (),
        "commands": ("NONLINEAR",),
    }


__all__ = ["nonlinear_template_spec"]
