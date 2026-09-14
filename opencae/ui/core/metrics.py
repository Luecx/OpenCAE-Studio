"""Central pixel metrics for reusable OpenCAE desktop UI surfaces."""

# Main / Sketch ribbon --------------------------------------------------------
RIBBON_ICON_SIZE = 42
RIBBON_BUTTON_WIDTH = 78
RIBBON_BUTTON_HEIGHT = 82
RIBBON_PAGE_HEIGHT = 104
STAGE_BAR_HEIGHT = 43

# Results ribbon --------------------------------------------------------------
# Results intentionally keeps the denser legacy geometry.  Do not merge these
# values with the main ribbon metrics: doing so would be a visual redesign.
RESULTS_RIBBON_ICON_SIZE = 28
RESULTS_RIBBON_BUTTON_WIDTH = 76
RESULTS_RIBBON_BUTTON_HEIGHT = 70

# Workspaces / docks ----------------------------------------------------------
TREE_ROW_HEIGHT = 26
DOCK_MIN_WIDTH = 280
OUTPUT_MIN_HEIGHT = 190

# Dialog and field controls --------------------------------------------------
# These values intentionally preserve the existing visual contracts. Keeping
# them in the core metrics module lets primitive controls and compatibility
# templates use one source of truth instead of duplicating pixel constants.
PRIMARY_CONTROL_HEIGHT = 40
INLINE_ACTION_SIZE = PRIMARY_CONTROL_HEIGHT
COMBO_POPUP_ROW_HEIGHT = 36
COMBO_POPUP_EXTRA_HEIGHT = 8
FIELD_LABEL_SPACING = 6

# Compact viewport command bars ---------------------------------------------
VIEWPORT_TOOL_HEIGHT = 28
