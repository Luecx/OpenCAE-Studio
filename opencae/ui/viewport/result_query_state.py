from __future__ import annotations

import logging

import numpy as np

from .result_query import element_values, node_values
from .safe_operations import disable_picking, remove_actor

LOGGER = logging.getLogger(__name__)


class ResultQueryState:
    def __init__(self, owner):
        self.owner = owner
        self.mode = ""
        self.field = None
        self._marker = "result-query-marker"
        self._edges = "result-query-edges"

    def configure(self, mode, field=None):
        self.mode, self.field = mode or "", field
        self._remove_marker()
        disable_picking(self.owner.plotter)
        if not self.mode or self.owner.stage != "RESULTS":
            self.owner.query_panel.clear_query()
            return
        self.owner.query_panel.show_prompt(self.mode)
        self.owner.canvas._position_overlays()
        picker = "point" if self.mode == "node" else "cell"
        if self._enable_picker(picker): return
        if picker != "cell" and self._enable_picker("cell"): return
        message = "Result query picking could not be enabled"
        self.owner.query_panel.show_prompt(message)
        if hasattr(self.owner, "message"): self.owner.message.emit(message)

    def _enable_picker(self, picker):
        try:
            self.owner.plotter.enable_surface_point_picking(
                callback=self._picked,
                left_clicking=True,
                show_message=False,
                show_point=False,
                picker=picker,
                pickable_window=True,
            )
            return True
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False
        except Exception:
            LOGGER.exception("Unexpected failure while enabling result query picker %s", picker)
            return False

    def clear(self):
        self._remove_marker()
        self.owner.query_panel.clear_query()

    def _remove_marker(self):
        for name in (self._marker, self._edges): remove_actor(self.owner.plotter, name)

    def _picked(self, point):
        grid = self.owner.scene.result_grid
        if point is None or grid is None: return
        suffix = f" — {self.field.name} / {self.field.metadata.get('component','Magnitude')}" if self.field is not None else ""
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
            np.asarray([marker]), color="#f2b84b", point_size=14,
            render_points_as_spheres=True, name=self._marker, pickable=False, render=False,
        )
        self.owner.query_panel.show_result(title, result)
        self.owner.canvas._position_overlays()
        self.owner.plotter.render()

    def _highlight_element(self, grid, index):
        remove_actor(self.owner.plotter, self._edges)
        try:
            edges = grid.extract_cells([int(index)]).extract_all_edges()
            self.owner.plotter.add_mesh(
                edges, color="#f2b84b", line_width=4.0, lighting=False,
                name=self._edges, pickable=False, render=False,
            )
        except (AttributeError, IndexError, RuntimeError, ValueError):
            return
        except Exception:
            LOGGER.exception("Unexpected failure while highlighting queried element %s", index)
