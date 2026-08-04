"""Declares the action groups shown on the Optimization ribbon page."""

from opencae.ui.actions.ids import A

from .specs import RibbonGroupSpec


def groups():
    """Return the ordered Optimization ribbon groups."""

    return (
        RibbonGroupSpec("SETUP", (A.OPT_NEW,)),
        RibbonGroupSpec(
            "RESPONSES",
            (A.OPT_RESPONSE, A.OPT_OBJECTIVE, A.OPT_CONSTRAINT),
        ),
        RibbonGroupSpec(
            "REGULARIZATION",
            (A.OPT_FILTER, A.OPT_SYMMETRY),
        ),
        RibbonGroupSpec("CONTROLS", (A.OPT_CONTROLS,)),
        RibbonGroupSpec(
            "EXECUTION",
            (A.OPT_VALIDATE, A.OPT_RUN, A.OPT_STOP),
        ),
        RibbonGroupSpec(
            "ITERATIONS",
            (A.OPT_PREVIOUS, A.OPT_NEXT, A.OPT_THRESHOLD),
        ),
    )
