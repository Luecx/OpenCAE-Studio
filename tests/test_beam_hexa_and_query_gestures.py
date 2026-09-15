"""Regression coverage for hexahedral beam display and query click/drag gating."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pyvista as pv
from PyQt6.QtCore import QEvent, QObject, Qt

from opencae.model.entities.profiles import BoxProfile, CircleProfile, RectangleProfile
from opencae.model.entities.profiles.section_geometry import section_patches
from opencae.results.beam_physical_model import BeamOccurrence
from opencae.results.beam_physical_representation import (
    BEAM_CENTERLINE_CELL,
    PHYSICAL_BEAM_CELL,
    build_beam_physical_representation_from_occurrences,
)
from opencae.ui.viewport.result_query_state import _ResultQueryMouseFilter


def _polygon_area(polygon):
    polygon = np.asarray(polygon, dtype=float)
    y = polygon[:, 0]
    z = polygon[:, 1]
    return 0.5 * abs(float(np.sum(y * np.roll(z, -1) - z * np.roll(y, -1))))


def test_circle_profile_is_quadrangulated_for_hexa_extrusion():
    profile = CircleProfile(name="Circle", dimensions={"diameter": 2.0})
    patches = section_patches(profile, circle_segments=24)
    assert len(patches) == 36
    assert all(patch.shape == (4, 2) for patch in patches)
    np.testing.assert_allclose(
        sum(_polygon_area(patch) for patch in patches), np.pi, rtol=0.03
    )


def test_box_profile_has_explicit_corners_and_subdivided_walls():
    profile = BoxProfile(
        name="Box",
        dimensions={"width": 4.0, "height": 2.0, "thickness": 0.25},
    )
    patches = section_patches(profile)
    expected_area = 4.0 * 2.0 - (4.0 - 0.5) * (2.0 - 0.5)
    assert len(patches) == 20
    np.testing.assert_allclose(
        sum(_polygon_area(patch) for patch in patches), expected_area
    )


def test_rectangle_beam_superset_keeps_centerline_and_adds_four_vtk_hexahedra():
    source = pv.UnstructuredGrid(
        np.asarray((2, 0, 1), dtype=np.int64),
        np.asarray((3,), dtype=np.uint8),
        np.asarray(((0.0, 0.0, 0.0), (2.0, 0.0, 0.0))),
    )
    source.point_data["node_id"] = np.asarray((1, 2), dtype=np.int64)
    source.cell_data["element_id"] = np.asarray((7,), dtype=np.int64)
    occurrence = BeamOccurrence(
        solver_element_id=7,
        part_id="part",
        instance_id="",
        source_element_id=7,
        connectivity=(1, 2),
        n1=(0.0, 1.0, 0.0),
        section=None,
        profile=RectangleProfile(name="R", dimensions={"width": 2.0, "height": 1.0}),
    )
    representation = build_beam_physical_representation_from_occurrences(
        (occurrence,), source, source_element_ids=True
    )
    expanded = representation.expand(source)

    centerline = np.flatnonzero(
        np.asarray(expanded.cell_data[BEAM_CENTERLINE_CELL], dtype=bool)
    )
    physical = np.flatnonzero(
        np.asarray(expanded.cell_data[PHYSICAL_BEAM_CELL], dtype=bool)
    )
    assert expanded.n_cells == 5
    assert len(centerline) == 1
    assert int(expanded.celltypes[int(centerline[0])]) == int(pv.CellType.LINE)
    assert len(physical) == 4
    assert np.all(np.asarray(expanded.celltypes)[physical] == int(pv.CellType.HEXAHEDRON))
    assert all(expanded.get_cell(int(index)).n_points == 8 for index in physical)


class _Point:
    def __init__(self, x, y):
        self._x = float(x)
        self._y = float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y


class _MouseEvent:
    def __init__(
        self,
        event_type,
        x,
        y,
        *,
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.NoButton,
    ):
        self._type = event_type
        self._point = _Point(x, y)
        self._button = button
        self._buttons = buttons
        self.accepted = False

    def type(self):
        return self._type

    def position(self):
        return self._point

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier

    def accept(self):
        self.accepted = True


class _Iren:
    def __init__(self):
        self.presses = 0
        self.releases = 0

    def LeftButtonPressEvent(self):
        self.presses += 1

    def LeftButtonReleaseEvent(self):
        self.releases += 1


class _Plotter(QObject):
    def __init__(self):
        super().__init__()
        self._Iren = _Iren()
        self._active_button = Qt.MouseButton.NoButton
        self.press_info = None

    def _setEventInformation(self, x, y, ctrl, shift, key, repeat=0, keysum=None):
        self.press_info = (x, y, ctrl, shift, key, repeat, keysum)


class _State:
    def __init__(self):
        self.owner = SimpleNamespace(
            plotter=_Plotter(),
            _event_display_position=lambda _watched, event: (
                event.position().x(), event.position().y()
            ),
        )
        self.picks = []

    def handles_direct_click(self):
        return True

    def pick_display_position(self, cursor):
        self.picks.append(tuple(cursor))
        return True


def test_result_query_click_is_consumed_before_camera_rotation():
    state = _State()
    gate = _ResultQueryMouseFilter(state)
    watched = state.owner.plotter
    assert gate.eventFilter(
        watched,
        _MouseEvent(
            QEvent.Type.MouseButtonPress, 100, 100,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        ),
    )
    assert gate.eventFilter(
        watched,
        _MouseEvent(
            QEvent.Type.MouseMove, 102, 101,
            buttons=Qt.MouseButton.LeftButton,
        ),
    )
    assert gate.eventFilter(
        watched,
        _MouseEvent(
            QEvent.Type.MouseButtonRelease, 102, 101,
            button=Qt.MouseButton.LeftButton,
        ),
    )
    assert state.owner.plotter._Iren.presses == 0
    assert state.picks == [(102.0, 101.0)]


def test_result_query_drag_starts_camera_only_after_threshold():
    state = _State()
    gate = _ResultQueryMouseFilter(state)
    watched = state.owner.plotter
    gate.eventFilter(
        watched,
        _MouseEvent(
            QEvent.Type.MouseButtonPress, 100, 100,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        ),
    )
    move = _MouseEvent(
        QEvent.Type.MouseMove, 108, 100, buttons=Qt.MouseButton.LeftButton
    )
    assert gate.eventFilter(watched, move) is False
    assert state.owner.plotter._Iren.presses == 1
    assert state.owner.plotter.press_info[:2] == (100.0, 100.0)
    release = _MouseEvent(
        QEvent.Type.MouseButtonRelease, 108, 100,
        button=Qt.MouseButton.LeftButton,
    )
    assert gate.eventFilter(watched, release) is False
    assert state.picks == []
