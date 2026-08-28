"""Build scalar-bar layout and compact OpenCAE outside-range end caps."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkRenderingCore import vtkActor2D, vtkPolyDataMapper2D

from .viewport_overlay_metrics import (
    VIEW_CUBE_SIZE,
    VIEWPORT_OVERLAY_GAP,
    VIEWPORT_OVERLAY_MARGIN,
)

_DEFAULT_BOTTOM = 0.08
_DEFAULT_HEIGHT = 0.72
_MINIMUM_HEIGHT = 0.18
_OUTSIDE_CAP_PIXELS = 6


def scalar_bar_title(title) -> str:
    """Return the exact display title used as PyVista's scalar-bar key."""
    return str(title).replace(":", " — ")


def scalar_bar_args(title, plotter=None, *, outside_colors=False):
    """Return a readable right-side scalar bar positioned below the ViewCube."""
    del outside_colors
    return {
        "title": scalar_bar_title(title),
        "vertical": True,
        "position_x": 0.905,
        "position_y": _DEFAULT_BOTTOM,
        "width": 0.045,
        "height": _available_height(plotter),
        "color": "#f0f3f6",
        "title_font_size": 13,
        "label_font_size": 11,
        "background_color": "#20262d",
        "n_labels": 7,
        "fmt": "%.4g",
    }


def install_scalar_bar_end_caps(
    plotter,
    title,
    *,
    below_color=None,
    above_color=None,
    cap_pixels=_OUTSIDE_CAP_PIXELS,
):
    """Attach small, gap-free end caps using the configured outside colors.

    VTK's built-in above/below swatches cannot be sized independently from the
    scalar-bar thickness and reserve a fixed pad. OpenCAE therefore switches
    those native swatches off and draws two lightweight 2D quads directly
    against vtkScalarBarActor.GetScalarBarRect(). The geometry follows
    resize/layout changes and schedules one corrective render only when the
    scalar-bar rectangle actually moves or changes size.
    """
    scalar_actor = _scalar_actor(plotter, title)
    renderer = getattr(plotter, "renderer", None)
    render_window = _render_window(plotter)
    if scalar_actor is None or renderer is None or render_window is None:
        return None

    _disable_native_range_swatches(scalar_actor)

    state = getattr(plotter, "_opencae_scalar_bar_caps", None)
    if state is None:
        state = _new_cap_state(renderer)
        try:
            setattr(plotter, "_opencae_scalar_bar_caps", state)
        except (AttributeError, TypeError):
            return None

    state["scalar_bar"] = scalar_actor
    state["renderer"] = renderer
    state["plotter"] = plotter
    state["cap_pixels"] = max(2, int(cap_pixels))
    state["rect"] = None
    state["render_pending"] = False

    _ensure_actor(renderer, state["below_actor"])
    _ensure_actor(renderer, state["above_actor"])
    _set_actor_color(state["below_actor"], below_color)
    _set_actor_color(state["above_actor"], above_color)
    state["below_actor"].SetVisibility(bool(below_color))
    state["above_actor"].SetVisibility(bool(above_color))

    if state.get("render_window") is not render_window:
        previous = state.get("render_window")
        tag = state.get("observer_tag")
        if previous is not None and tag is not None:
            try:
                previous.RemoveObserver(tag)
            except (AttributeError, RuntimeError, TypeError):
                pass
        state["render_window"] = render_window
        state["observer_tag"] = render_window.AddObserver(
            "EndEvent",
            lambda *_: _update_cap_geometry(state),
        )
    return state


def _disable_native_range_swatches(scalar_actor):
    """Suppress PyVista/VTK's thick padded above/below range blocks."""
    try:
        scalar_actor.DrawBelowRangeSwatchOff()
        scalar_actor.DrawAboveRangeSwatchOff()
    except (AttributeError, RuntimeError, TypeError):
        pass


def _new_cap_state(renderer):
    below_actor, below_poly = _rectangle_actor()
    above_actor, above_poly = _rectangle_actor()
    return {
        "below_actor": below_actor,
        "below_poly": below_poly,
        "above_actor": above_actor,
        "above_poly": above_poly,
        "scalar_bar": None,
        "renderer": renderer,
        "plotter": None,
        "render_window": None,
        "observer_tag": None,
        "cap_pixels": _OUTSIDE_CAP_PIXELS,
        "rect": None,
        "render_pending": False,
    }


def _rectangle_actor():
    points = vtkPoints()
    points.SetNumberOfPoints(4)
    for index in range(4):
        points.SetPoint(index, 0.0, 0.0, 0.0)
    cells = vtkCellArray()
    cells.InsertNextCell(4)
    for index in range(4):
        cells.InsertCellPoint(index)
    poly = vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    mapper = vtkPolyDataMapper2D()
    mapper.SetInputData(poly)
    actor = vtkActor2D()
    actor.SetMapper(mapper)
    actor.SetPickable(False)
    return actor, poly


def _scalar_actor(plotter, title):
    key = scalar_bar_title(title)
    try:
        bars = plotter.scalar_bars
        if key in bars:
            return bars[key]
    except (AttributeError, KeyError, TypeError, RuntimeError):
        pass
    try:
        return plotter.scalar_bar
    except (AttributeError, RuntimeError):
        return None


def _render_window(plotter):
    try:
        return plotter.GetRenderWindow()
    except (AttributeError, RuntimeError):
        pass
    try:
        return plotter.render_window
    except (AttributeError, RuntimeError):
        return None


def _ensure_actor(renderer, actor):
    """Attach one cap through PyVista's public API or a plain VTK renderer."""
    add_actor = getattr(renderer, "add_actor", None)
    if callable(add_actor):
        try:
            add_actor(
                actor,
                reset_camera=False,
                pickable=False,
                render=False,
            )
            return
        except (AttributeError, RuntimeError, TypeError):
            pass
    try:
        if not renderer.HasViewProp(actor):
            renderer.AddActor2D(actor)
    except (AttributeError, RuntimeError, TypeError):
        try:
            renderer.AddActor2D(actor)
        except (AttributeError, RuntimeError, TypeError):
            pass


def _set_actor_color(actor, value):
    if not value:
        return
    color = QColor(str(value))
    if not color.isValid():
        return
    actor.GetProperty().SetColor(color.redF(), color.greenF(), color.blueF())
    actor.GetProperty().SetOpacity(color.alphaF())


def _update_cap_geometry(state):
    scalar_actor = state.get("scalar_bar")
    renderer = state.get("renderer")
    if scalar_actor is None or renderer is None:
        return
    rect = [0, 0, 0, 0]
    try:
        scalar_actor.GetScalarBarRect(rect, renderer)
    except (AttributeError, RuntimeError, TypeError):
        return
    rect = tuple(int(value) for value in rect)
    if rect[2] <= 0 or rect[3] <= 0:
        return
    bottom, top = _cap_rectangles(rect, state["cap_pixels"])
    _set_rectangle(state["below_poly"], bottom)
    _set_rectangle(state["above_poly"], top)
    if rect == state.get("rect"):
        return
    state["rect"] = rect
    if state.get("render_pending"):
        return
    state["render_pending"] = True
    plotter = state.get("plotter")
    if plotter is None:
        return

    def render_updated_caps():
        state["render_pending"] = False
        try:
            plotter.render()
        except (AttributeError, RuntimeError):
            pass

    QTimer.singleShot(0, render_updated_caps)


def _cap_rectangles(rect, cap_pixels=_OUTSIDE_CAP_PIXELS):
    """Return display-pixel rectangles touching the bottom/top bar edges."""
    x, y, width, height = (int(value) for value in rect)
    cap = max(2, int(cap_pixels))
    return (
        (x, y - cap, width, cap),
        (x, y + height, width, cap),
    )


def _set_rectangle(poly, rect):
    x, y, width, height = rect
    points = poly.GetPoints()
    points.SetPoint(0, x, y, 0.0)
    points.SetPoint(1, x + width, y, 0.0)
    points.SetPoint(2, x + width, y + height, 0.0)
    points.SetPoint(3, x, y + height, 0.0)
    points.Modified()
    poly.Modified()


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
