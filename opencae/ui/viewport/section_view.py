"""Render and update clipped result sections with correctly mapped contour data."""

from __future__ import annotations

import math

import numpy as np
from vtkmodules.vtkCommonDataModel import vtkPlane

from opencae.ui.core.theme import PALETTE


_SECTION_CAP_NAME = "solution-section-cap"


class SectionViewController:
    """Own the result clipping plane and its interactive viewport widget.

    The mapper clipping plane removes the hidden side of the rendered exterior,
    but mapper clipping alone leaves solid FE meshes visually hollow.  A second
    actor therefore renders the geometric slice through the *volume* dataset.
    Because PyVista/VTK interpolates point data on that slice, contour values on
    the cut face remain consistent with the surrounding result surface.
    """

    def __init__(self, owner):
        self.owner = owner
        self.plane = vtkPlane()
        self._actors = ()
        self._grid = None
        self._cap_actor = None
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
        self._remove_cap()
        self._clear_widget()
        self._actors = ()
        self._grid = None

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
        self._grid = grid
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
        self._update_cap()
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

    def update_grid(self, grid, actors) -> None:
        """Refresh section geometry after an animation frame changes the grid.

        The plane widget and interaction state stay alive.  Only the source grid,
        actor list and interpolated cut face are refreshed, avoiding a visible
        widget rebuild on every animation tick.
        """
        self._grid = grid
        self._actors = tuple(actor for actor in actors if actor is not None)
        if not self._state["enabled"] or grid is None:
            self._remove_cap()
            return
        self._apply_clipping()
        self._update_cap()

    def _widget_changed(self, normal, origin) -> None:
        if not self._state["enabled"]:
            return
        self._state["origin"] = tuple(float(value) for value in origin)
        self._state["normal"] = self._normalize(normal)
        self._update_plane(self._state["origin"], self._state["normal"])
        self._update_cap()
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

    def _update_cap(self) -> None:
        primary = self._actors[0] if self._actors else None
        if primary is None or self._grid is None:
            self._remove_cap()
            return
        cut = section_cut_surface(
            self._grid,
            self._state["origin"],
            self.plane.GetNormal(),
        )
        if cut is None:
            self._remove_cap()
            return

        source_mapper = self._mapper(primary)
        scalar = self._selected_scalar(source_mapper, cut)
        if self._cap_actor is None:
            kwargs = {
                "name": _SECTION_CAP_NAME,
                "pickable": False,
                "render": False,
                "reset_camera": False,
                "show_scalar_bar": False,
                "lighting": True,
            }
            if scalar is not None:
                kwargs["scalars"] = scalar
                kwargs["preference"] = (
                    "point" if scalar in cut.point_data else "cell"
                )
            self._cap_actor = self.owner.plotter.add_mesh(cut, **kwargs)

        cap_mapper = self._mapper(self._cap_actor)
        if cap_mapper is None or not self._bind_cap_dataset(cap_mapper, cut, scalar):
            self._remove_cap()
            return
        self._sync_cap_style(primary, scalar)

    @staticmethod
    def _bind_cap_dataset(mapper, dataset, scalar) -> bool:
        """Bind a new slice through PyVista's mapper pipeline, including scalars.

        PyVista's ``DataSetMapper`` inserts an ``ActiveScalarsAlgorithm`` when a
        named array is selected.  Assigning with VTK ``SetInputData`` bypasses
        PyVista's dataset setter and can disconnect that pipeline when a moved
        section creates a replacement slice.  Using the public mapper API keeps
        the selected result array deterministic across every plane movement.
        """
        try:
            mapper.dataset = dataset
            if scalar is None:
                mapper.scalar_visibility = False
                return True
            if scalar in dataset.point_data:
                preference = "point"
            elif scalar in dataset.cell_data:
                preference = "cell"
            else:
                return False
            mapper.set_active_scalars(scalar, preference=preference)
            mapper.scalar_visibility = True
            mapper.Modified()
            return True
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
            return False

    def _sync_cap_style(self, source_actor, scalar) -> None:
        source_mapper = self._mapper(source_actor)
        cap_mapper = self._mapper(self._cap_actor)
        if source_mapper is None or cap_mapper is None:
            return
        try:
            source_property = source_actor.GetProperty()
            cap_property = self._cap_actor.GetProperty()
            cap_property.DeepCopy(source_property)
        except (AttributeError, RuntimeError, TypeError):
            pass
        try:
            if scalar is None or not source_mapper.GetScalarVisibility():
                cap_mapper.scalar_visibility = False
            else:
                cap_mapper.lookup_table = source_mapper.GetLookupTable()
                cap_mapper.scalar_range = source_mapper.GetScalarRange()
                cap_mapper.scalar_visibility = True
            cap_mapper.Modified()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _remove_cap(self) -> None:
        if self._cap_actor is None:
            return
        try:
            self.owner.plotter.remove_actor(
                _SECTION_CAP_NAME,
                reset_camera=False,
                render=False,
            )
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
            pass
        self._cap_actor = None

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
    def _selected_scalar(mapper, dataset):
        if mapper is None:
            return None
        try:
            if not mapper.GetScalarVisibility():
                return None
            name = mapper.GetArrayName()
        except (AttributeError, RuntimeError, TypeError):
            return None
        if isinstance(name, bytes):
            name = name.decode(errors="replace")
        name = str(name or "")
        if name and (name in dataset.point_data or name in dataset.cell_data):
            return name
        return None

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


def section_cut_surface(grid, origin, normal):
    """Return a filled 2-D cut through volumetric cells, or ``None``.

    Slicing a 3-D VTK cell produces 2-D polygons and interpolates its point
    arrays onto the intersection.  Slicing shells produces only 1-D lines; those
    are deliberately rejected because a shell has no volume to cap.
    """
    if grid is None or origin is None:
        return None
    try:
        cut = grid.slice(normal=normal, origin=origin)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if cut is None or not getattr(cut, "n_cells", 0):
        return None
    if not _contains_surface_cells(cut):
        return None
    return cut


def _contains_surface_cells(dataset) -> bool:
    """Return whether a sliced dataset contains at least one 2-D cell."""
    count = int(getattr(dataset, "n_cells", 0) or 0)
    if count <= 0:
        return False
    celltypes = np.asarray(getattr(dataset, "celltypes", ()), dtype=int)
    candidates = range(count)
    if celltypes.size == count:
        candidates = (
            int(np.flatnonzero(celltypes == cell_type)[0])
            for cell_type in np.unique(celltypes)
        )
    for index in candidates:
        try:
            cell = dataset.get_cell(index)
        except (AttributeError, IndexError, RuntimeError, TypeError, ValueError):
            continue
        dimension = getattr(cell, "dimension", None)
        if callable(dimension):
            dimension = dimension()
        if dimension is None:
            try:
                dimension = cell.GetCellDimension()
            except (AttributeError, RuntimeError, TypeError):
                continue
        if int(dimension) >= 2:
            return True
    return False
