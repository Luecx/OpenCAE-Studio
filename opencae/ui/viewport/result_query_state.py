"""Own drag-safe node and element query state for displayed solver results."""

from __future__ import annotations

import logging

import numpy as np

from .result_query import element_values, node_values
from .safe_operations import disable_picking, remove_actor

LOGGER = logging.getLogger(__name__)


class ResultQueryState:
    """Resolve result queries only from click gestures accepted by the viewport."""

    def __init__(self, owner):
        self.owner = owner
        self.mode = ""
        self.field = None
        self._marker = "result-query-marker"
        self._edges = "result-query-edges"

    def configure(self, mode, field=None):
        """Enable or disable node/element querying without installing a VTK click observer."""
        self.mode, self.field = mode or "", field
        self._remove_marker()
        # PyVista's left_clicking picker fires at the end of camera drags. Mouse
        # gesture classification therefore belongs to PyVistaViewport's Qt event
        # filter; this object receives only releases already classified as clicks.
        disable_picking(self.owner.plotter)
        if not self.handles_direct_click():
            self.owner.query_panel.clear_query()
            return
        self.owner.query_panel.show_prompt(self.mode)
        self.owner.canvas._position_overlays()

    def handles_direct_click(self) -> bool:
        """Return whether the current Results state should consume an ordinary click."""
        return bool(
            self.mode in {"node", "element"}
            and self.owner.stage == "RESULTS"
            and self.owner.scene.result_grid is not None
            and self.owner.scene.result_actor is not None
        )

    def pick_display_position(self, cursor) -> bool:
        """Resolve one accepted Qt click to a world point on the result actor."""
        if not self.handles_direct_click():
            return False
        try:
            from vtkmodules.vtkRenderingCore import vtkCellPicker

            picker = vtkCellPicker()
            picker.SetTolerance(0.0005)
            picker.PickFromListOn()
            picker.AddPickList(self.owner.scene.result_actor)
            hit = bool(
                picker.Pick(
                    float(cursor[0]),
                    float(cursor[1]),
                    0.0,
                    self.owner.plotter.renderer,
                )
            )
            if not hit:
                return False
            point = tuple(float(value) for value in picker.GetPickPosition())
        except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
            return False
        self._picked(point)
        return True

    def clear(self):
        """Clear the current result-query marker and overlay text."""
        self._remove_marker()
        self.owner.query_panel.clear_query()

    def _remove_marker(self):
        """Remove transient query marker actors without forcing a render."""
        for name in (self._marker, self._edges):
            remove_actor(self.owner.plotter, name)

    def _picked(self, point):
        """Present node or element values at a picked result-surface position."""
        grid = self.owner.scene.result_grid
        if point is None or grid is None:
            return
        suffix = (
            f" — {self.field.name} / {self.field.metadata.get('component', 'Magnitude')}"
            if self.field is not None
            else ""
        )
        if self.mode == "node":
            index, result = node_values(grid, point, self.field)
            marker = grid.points[index]
            title = "Node Query" + suffix
        else:
            index, result = element_values(grid, point, self.field)
            marker = grid.get_cell(index).center
            title = "Element Query" + suffix
            self._highlight_element(grid, index)
        self.owner.plotter.add_points(
            np.asarray([marker]),
            color="#f2b84b",
            point_size=14,
            render_points_as_spheres=True,
            name=self._marker,
            pickable=False,
            render=False,
        )
        self.owner.query_panel.show_result(title, result)
        self.owner.canvas._position_overlays()
        self.owner.plotter.render()

    def _highlight_element(self, grid, index):
        """Draw the queried element's edges without disturbing result picking."""
        remove_actor(self.owner.plotter, self._edges)
        try:
            edges = grid.extract_cells([int(index)]).extract_all_edges()
            self.owner.plotter.add_mesh(
                edges,
                color="#f2b84b",
                line_width=4.0,
                lighting=False,
                name=self._edges,
                pickable=False,
                render=False,
            )
        except (AttributeError, IndexError, RuntimeError, ValueError):
            return
        except Exception:
            LOGGER.exception(
                "Unexpected failure while highlighting queried element %s",
                index,
            )
