"""Build scalar-bar layout that stays clear of fixed Qt viewport overlays."""

from __future__ import annotations

from .viewport_overlay_metrics import (
    VIEW_CUBE_SIZE,
    VIEWPORT_OVERLAY_GAP,
    VIEWPORT_OVERLAY_MARGIN,
)

_DEFAULT_BOTTOM = 0.08
_DEFAULT_HEIGHT = 0.72
_MINIMUM_HEIGHT = 0.18


def scalar_bar_args(title, plotter=None, *, outside_colors=False):
    """Return a readable right-side scalar bar positioned below the ViewCube."""
    args = {
        "title": str(title).replace(":", " — "),
        "vertical": True,
        "position_x": 0.905,
        "position_y": _DEFAULT_BOTTOM,
        # PyVista/VTK sizes the above/below swatches from the scalar-bar
        # thickness.  The previous 0.065 bar made those end caps visually huge;
        # a slimmer bar keeps them as small colorbar terminations.
        "width": 0.045,
        "height": _available_height(plotter),
        "color": "#f0f3f6",
        "title_font_size": 13,
        "label_font_size": 11,
        "background_color": "#20262d",
        "n_labels": 7,
        "fmt": "%.4g",
    }
    if outside_colors:
        # Passing an explicit empty annotation keeps the VTK range swatch but
        # removes the redundant literal "above" / "below" text.
        args["below_label"] = ""
        args["above_label"] = ""
    return args


def _available_height(plotter) -> float:
    """Return the largest scalar-bar height that does not enter the cube area."""
    viewport_height = _viewport_height(plotter)
    if viewport_height is None:
        return 0.64

    reserved_top = (
        VIEWPORT_OVERLAY_MARGIN
        + VIEW_CUBE_SIZE
        + VIEWPORT_OVERLAY_GAP
    ) / viewport_height
    top_limit = max(0.0, 1.0 - reserved_top)
    available = top_limit - _DEFAULT_BOTTOM
    return max(_MINIMUM_HEIGHT, min(_DEFAULT_HEIGHT, available))


def _viewport_height(plotter) -> float | None:
    """Resolve render-widget height without depending on one backend API."""
    if plotter is None:
        return None
    try:
        value = float(plotter.height())
        if value > 0:
            return value
    except (AttributeError, TypeError, ValueError, RuntimeError):
        pass
    try:
        _width, height = plotter.GetRenderWindow().GetSize()
        value = float(height)
        return value if value > 0 else None
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None
