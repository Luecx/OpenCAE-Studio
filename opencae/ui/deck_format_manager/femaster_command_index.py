"""List the native FEMaster keywords covered by the flat-deck format editor."""

from __future__ import annotations


FEMASTER_DOCUMENTED_COMMANDS = frozenset(
    {
        "HEADING",
        "MODEL",
        "NODE",
        "ELEMENT",
        "NSET",
        "ELSET",
        "SURFACE",
        "SFSET",
        "MATERIAL",
        "ELASTIC",
        "HYPERELASTIC",
        "DENSITY",
        "THERMALEXPANSION",
        "PROFILE",
        "SOLID SECTION",
        "SHELL SECTION",
        "BEAM SECTION",
        "TRUSS SECTION",
        "ORIENTATION",
        "FIELD",
        "NORMAL",
        "AMPLITUDE",
        "SUPPORT",
        "CLOAD",
        "DLOAD",
        "PLOAD",
        "VLOAD",
        "TLOAD",
        "INERTIALOAD",
        "COUPLING",
        "TIE",
        "CONNECTOR",
        "RBM",
        "CONTACT",
        "LOADCASE",
        "SUPPORTS",
        "LOADS",
        "END",
        "SOLVER",
        "CONSTRAINTMETHOD",
        "NONLINEAR",
        "TIME",
        "NEWMARK",
        "DAMPING",
        "FREQUENCIES",
        "NUMEIGENVALUES",
        "SIGMA",
        "WRITEEVERY",
        "INITIALVELOCITY",
        "INERTIARELIEF",
        "REBALANCELOADS",
        "OVERVIEW",
        "REQUESTSTIFFNESS",
        "REQUESTSTGEOM",
        "CONSTRAINTSUMMARY",
        "POINTMASS",
        "TOPODENSITY",
        "TOPOORIENT",
        "TOPOEXPONENT",
    }
)

STRUCTURED_MODEL_COMMANDS = frozenset(
    {
        "PART",
        "END PART",
        "ASSEMBLY",
        "END ASSEMBLY",
        "INSTANCE",
        "END INSTANCE",
    }
)

# OpenCAE exposes Equation as a first-class constraint. FEMaster's current source
# accepts the Abaqus-compatible EQUATION grammar, even though the native keyword
# index does not list it as a native command. It therefore stays in the editor.
OPENCAE_ADDITIONAL_COMMANDS = frozenset({"EQUATION"})


__all__ = [
    "FEMASTER_DOCUMENTED_COMMANDS",
    "OPENCAE_ADDITIONAL_COMMANDS",
    "STRUCTURED_MODEL_COMMANDS",
]
