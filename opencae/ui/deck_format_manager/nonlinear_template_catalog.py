"""Define the complete solver-neutral nonlinear-control editor record."""

from __future__ import annotations


def nonlinear_template_spec() -> dict:
    """Return the FEMaster nonlinear record with all persisted control fields."""
    return {
        "template": (
            "*NONLINEAR, CONTROL={control}, MAX_INCREMENTS={max_increments}, "
            "INITIAL_INCREMENT={initial_increment}, MINIMUM_INCREMENT={minimum_increment}, "
            "MAXIMUM_INCREMENT={maximum_increment}, MAXITER={max_iterations}, "
            "TOL={tolerance}, ADAPTIVE={adaptive}, GROWTH_FACTOR={growth_factor}, "
            "CUTBACK_FACTOR={cutback_factor}, FAST_ITERATIONS={fast_iterations}, "
            "SLOW_ITERATIONS={slow_iterations}, MAXIMUM_CUTBACKS={maximum_cutbacks}, "
            "REGULARIZE_ZERO_ROWS={regularize_zero_rows}, "
            "REGULARIZATION_ALPHA={regularization_alpha}, ARC_LENGTH_PSI={arc_length_psi}"
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
