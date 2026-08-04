from __future__ import annotations

import math

import numpy as np
from vtkmodules.vtkCommonDataModel import vtkPlane

from opencae.ui.core.theme import PALETTE


class SectionViewController:
    """Owns the result clipping plane and its interactive viewport widget."""

    def __init__(self, owner):
        self.owner = owner
        self.plane = vtkPlane()
        self._actors = ()
        self._widget = None
        self._state = {
            "enabled": False,
            "origin": None,
            "normal": (1.0, 0.0, 0.0),
            "invert": False,
            "show_plane": True,
        }

    def clear_scene(self) -> None:
        self._remove_clipping()
        self._clear_widget()
        self._actors = ()

    def apply(self, settings: dict | None, grid, actors) -> None:
        self.clear_scene()
        incoming = dict(settings or {})
        self._state.update(
            enabled=bool(incoming.get("enabled", False)),
            origin=incoming.get("origin"),
            normal=self._normalize(incoming.get("normal", (1.0, 0.0, 0.0))),
            invert=bool(incoming.get("invert", False)),
            show_plane=bool(incoming.get("show_plane", True)),
        )
        self._actors = tuple(actor for actor in actors if actor is not None)
        if not self._state["enabled"] or grid is None:
            self._publish()
            return

        bounds = tuple(float(value) for value in grid.bounds)
        origin = self._state["origin"]
        if origin is None:
            origin = self._bounds_center(bounds)
        origin = tuple(float(value) for value in origin)
        self._state["origin"] = origin

        self._update_plane(origin, self._state["normal"])
        self._apply_clipping()
        if self._state["show_plane"]:
            self._widget = self.owner.plotter.add_plane_widget(
                self._widget_changed,
                normal=self._state["normal"],
                origin=origin,
                bounds=bounds,
                factor=1.12,
                color=PALETTE["accent"],
                tubing=False,
                outline_translation=False,
                origin_translation=True,
                implicit=True,
                test_callback=False,
                normal_rotation=True,
                interaction_event="always",
                outline_opacity=0.20,
            )
        self._publish()

    def _widget_changed(self, normal, origin) -> None:
        if not self._state["enabled"]:
            return
        self._state["origin"] = tuple(float(value) for value in origin)
        self._state["normal"] = self._normalize(normal)
        self._update_plane(self._state["origin"], self._state["normal"])
        self.owner.plotter.render()
        self._publish()

    def _update_plane(self, origin, normal) -> None:
        effective_normal = np.asarray(normal, dtype=float)
        if self._state["invert"]:
            effective_normal *= -1.0
        self.plane.SetOrigin(*origin)
        self.plane.SetNormal(*effective_normal)
        self.plane.Modified()

    def _apply_clipping(self) -> None:
        for actor in self._actors:
            mapper = self._mapper(actor)
            if mapper is None:
                continue
            mapper.RemoveAllClippingPlanes()
            mapper.AddClippingPlane(self.plane)
            mapper.Modified()

    def _remove_clipping(self) -> None:
        for actor in self._actors:
            mapper = self._mapper(actor)
            if mapper is not None:
                mapper.RemoveAllClippingPlanes()
                mapper.Modified()

    def _clear_widget(self) -> None:
        if self._widget is None:
            return
        try:
            self.owner.plotter.clear_plane_widgets()
        except (AttributeError, RuntimeError):
            pass
        self._widget = None

    def _publish(self) -> None:
        self.owner.section_changed.emit(dict(self._state))

    @staticmethod
    def _mapper(actor):
        try:
            return actor.GetMapper()
        except (AttributeError, RuntimeError):
            return getattr(actor, "mapper", None)

    @staticmethod
    def _bounds_center(bounds) -> tuple[float, float, float]:
        return (
            0.5 * (bounds[0] + bounds[1]),
            0.5 * (bounds[2] + bounds[3]),
            0.5 * (bounds[4] + bounds[5]),
        )

    @staticmethod
    def _normalize(value) -> tuple[float, float, float]:
        vector = tuple(float(component) for component in value)
        length = math.sqrt(sum(component * component for component in vector))
        if length <= 1.0e-14:
            return (1.0, 0.0, 0.0)
        return tuple(component / length for component in vector)
