from __future__ import annotations

import os
from typing import Iterable

# pyvistaqt selects the active Qt binding through qtpy. Set this before
# importing pyvistaqt so the application consistently uses PyQt6.
os.environ.setdefault("QT_API", "pyqt6")

import numpy as np
import pyvista as pv
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from .icons import IconKind, make_icon
from .theme import PALETTE


class Viewport(QWidget):
    """Native VTK/PyVista viewport embedded in the PyQt6 application."""

    selectionChanged = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(700, 460)

        self._show_mesh = True
        self._show_contour = False
        self._actors: list = []
        self._model_meshes = self._create_demo_bracket()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.plotter = QtInteractor(
            self,
            multi_samples=8,
            line_smoothing=True,
            polygon_smoothing=True,
            auto_update=5.0,
        )
        root.addWidget(self.plotter.interactor)

        self.plotter.set_background(PALETTE["viewport"])
        self.plotter.enable_anti_aliasing("ssaa")
        self.plotter.add_axes(
            line_width=2,
            cone_radius=0.35,
            shaft_length=0.72,
            tip_length=0.28,
            labels_off=False,
        )
        self.plotter.add_text(
            "PART / Bracket\nShaded with mesh",
            position="upper_left",
            font_size=9,
            color="#aab5c0",
            name="viewport-status",
        )

        self._build_tool_overlay()
        self._build_scene(reset_camera=True)
        self._enable_picking()

    # ------------------------------------------------------------------
    # Public API expected by MainWindow
    # ------------------------------------------------------------------
    def fit_view(self) -> None:
        self.plotter.reset_camera()
        self.plotter.render()

    def toggle_mesh(self) -> None:
        self._show_mesh = not self._show_mesh
        self._build_scene(reset_camera=False)

    def toggle_contour(self) -> None:
        self._show_contour = not self._show_contour
        self._build_scene(reset_camera=False)

    def set_view(self, direction: str) -> None:
        views = {
            "isometric": self.plotter.view_isometric,
            "front": self.plotter.view_xz,
            "right": self.plotter.view_yz,
            "top": self.plotter.view_xy,
        }
        views.get(direction, self.plotter.view_isometric)()
        self.plotter.reset_camera()
        self.plotter.render()

    # ------------------------------------------------------------------
    # Qt overlay
    # ------------------------------------------------------------------
    def _build_tool_overlay(self) -> None:
        self._tools = QWidget(self)
        self._tools.setObjectName("ViewportTools")
        self._tools.setStyleSheet(
            f"""
            QWidget#ViewportTools {{
                background: {PALETTE['panel']};
                border: 1px solid {PALETTE['border']};
                border-radius: 3px;
            }}
            QToolButton {{
                border: 0;
                border-radius: 2px;
                background: transparent;
                padding: 2px;
            }}
            QToolButton:hover {{ background: {PALETTE['panel_alt']}; }}
            QToolButton:checked {{ background: {PALETTE['accent']}; }}
            """
        )
        layout = QVBoxLayout(self._tools)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        buttons = [
            ("Fit", IconKind.REFERENCE, self.fit_view, False),
            ("Mesh", IconKind.ELEMENT_SET, self.toggle_mesh, True),
            ("Contour", IconKind.CONTOUR, self.toggle_contour, True),
            ("Probe", IconKind.PROBE, self._activate_probe, False),
        ]
        for text, icon_kind, callback, checkable in buttons:
            button = QToolButton(self._tools)
            button.setIcon(make_icon(icon_kind, 26))
            button.setIconSize(QSize(24, 24))
            button.setToolTip(text)
            button.setFixedSize(31, 31)
            button.setCheckable(checkable)
            if text == "Mesh":
                button.setChecked(True)
                self._mesh_button = button
            elif text == "Contour":
                self._contour_button = button
            button.clicked.connect(callback)
            layout.addWidget(button)

        self._tools.adjustSize()
        self._tools.raise_()

        self._view_bar = QWidget(self)
        self._view_bar.setObjectName("ViewBar")
        self._view_bar.setStyleSheet(
            f"""
            QWidget#ViewBar {{
                background: {PALETTE['panel']};
                border: 1px solid {PALETTE['border']};
                border-radius: 3px;
            }}
            QToolButton {{
                color: {PALETTE['muted']};
                border: 0;
                padding: 4px 8px;
                background: transparent;
                font-size: 11px;
            }}
            QToolButton:hover {{
                color: {PALETTE['text']};
                background: {PALETTE['panel_alt']};
            }}
            """
        )
        bar_layout = QHBoxLayout(self._view_bar)
        bar_layout.setContentsMargins(2, 2, 2, 2)
        bar_layout.setSpacing(0)
        for label, view in (("ISO", "isometric"), ("FRONT", "front"), ("RIGHT", "right"), ("TOP", "top")):
            button = QToolButton(self._view_bar)
            button.setText(label)
            button.clicked.connect(lambda checked=False, target=view: self.set_view(target))
            bar_layout.addWidget(button)
        self._view_bar.adjustSize()
        self._view_bar.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._tools.move(max(8, self.width() - self._tools.width() - 14), 52)
        self._view_bar.move(max(8, self.width() - self._view_bar.width() - 14), 12)
        self._tools.raise_()
        self._view_bar.raise_()

    # ------------------------------------------------------------------
    # Scene creation and display
    # ------------------------------------------------------------------
    @staticmethod
    def _create_demo_bracket() -> list[pv.PolyData]:
        """Create a lightweight multi-body bracket for the UI prototype.

        This deliberately avoids boolean CAD operations, making startup robust
        on machines without optional geometry backends.
        """
        base = pv.Box(bounds=(-70, 70, -42, 42, -8, 8)).triangulate().subdivide(1)

        # Upright web and two supporting ribs.
        web = pv.Box(bounds=(-10, 10, -13, 13, 5, 92)).triangulate().subdivide(1)
        rib_left = pv.Box(bounds=(-48, -8, -10, 10, 5, 52)).triangulate().subdivide(1)
        rib_left.rotate_y(-42, inplace=True, point=(0, 0, 5))
        rib_right = rib_left.copy()
        rib_right.reflect((1, 0, 0), point=(0, 0, 0), inplace=True)

        # Circular boss. A dark inner cylinder is rendered separately to mimic
        # the through-hole while keeping the demo geometry dependency-free.
        boss = pv.Cylinder(center=(0, 0, 87), direction=(0, 1, 0), radius=27, height=26, resolution=64)
        boss = boss.triangulate().subdivide(1)
        hole = pv.Cylinder(center=(0, 0, 87), direction=(0, 1, 0), radius=13, height=27, resolution=64)

        mount_left = pv.Cylinder(center=(-49, 0, 9), direction=(0, 0, 1), radius=10, height=19, resolution=48)
        mount_right = mount_left.copy()
        mount_right.translate((98, 0, 0), inplace=True)

        return [base, web, rib_left, rib_right, boss, mount_left, mount_right, hole]

    def _build_scene(self, reset_camera: bool) -> None:
        camera = self.plotter.camera_position if not reset_camera else None
        self.plotter.clear_actors()
        self._actors.clear()

        structural = self._model_meshes[:-1]
        hole = self._model_meshes[-1]

        scalar_bar_added = False
        for index, mesh in enumerate(structural):
            display_mesh = mesh.copy(deep=True)
            kwargs: dict = {
                "show_edges": self._show_mesh,
                "edge_color": "#25313a",
                "line_width": 0.65,
                "smooth_shading": True,
                "pbr": True,
                "metallic": 0.12,
                "roughness": 0.62,
                "pickable": True,
            }

            if self._show_contour:
                values = self._result_values(display_mesh)
                display_mesh.point_data["Equivalent stress"] = values
                kwargs.update(
                    scalars="Equivalent stress",
                    cmap="turbo",
                    clim=(0.0, 250.0),
                    show_scalar_bar=not scalar_bar_added,
                    scalar_bar_args={
                        "title": "Equivalent stress [MPa]",
                        "vertical": True,
                        "position_x": 0.84,
                        "position_y": 0.10,
                        "height": 0.34,
                        "width": 0.08,
                        "title_font_size": 10,
                        "label_font_size": 9,
                        "color": "#d8dee6",
                        "fmt": "%.0f",
                    },
                )
                scalar_bar_added = True
            else:
                kwargs["color"] = "#75838e" if index != 4 else "#82919b"

            actor = self.plotter.add_mesh(display_mesh, **kwargs)
            self._actors.append(actor)

        # Fake the through-hole with a viewport-colored inner surface.
        self.plotter.add_mesh(
            hole,
            color=PALETTE["viewport"],
            smooth_shading=True,
            show_edges=False,
            pickable=False,
        )

        self.plotter.add_text(
            f"PART / Bracket\n{'Equivalent stress' if self._show_contour else 'Shaded'}"
            f"{' with mesh' if self._show_mesh else ''}",
            position="upper_left",
            font_size=9,
            color="#aab5c0",
            name="viewport-status",
        )
        self.plotter.add_text(
            "241,890 nodes   ·   152,624 elements",
            position="lower_left",
            font_size=9,
            color="#aab5c0",
            name="mesh-status",
        )

        if reset_camera:
            self.plotter.view_isometric()
            self.plotter.reset_camera()
            self.plotter.camera.zoom(1.18)
        elif camera is not None:
            self.plotter.camera_position = camera

        self.plotter.render()
        self._mesh_button.setChecked(self._show_mesh)
        self._contour_button.setChecked(self._show_contour)

    @staticmethod
    def _result_values(mesh: pv.DataSet) -> np.ndarray:
        points = mesh.points
        x = points[:, 0]
        z = points[:, 2]
        x_span = max(float(np.ptp(x)), 1.0)
        z_span = max(float(np.ptp(z)), 1.0)
        x_norm = (x - x.min()) / x_span
        z_norm = (z - z.min()) / z_span
        # Synthetic field for the UI prototype: stress increases toward the
        # right mounting side and the base/web transition.
        concentration = np.exp(-((x - 9.0) / 28.0) ** 2 - ((z - 12.0) / 24.0) ** 2)
        values = 22.0 + 100.0 * x_norm + 52.0 * (1.0 - z_norm) + 90.0 * concentration
        return np.clip(values, 0.0, 250.0)

    # ------------------------------------------------------------------
    # Picking
    # ------------------------------------------------------------------
    def _enable_picking(self) -> None:
        try:
            self.plotter.enable_surface_point_picking(
                callback=self._on_pick,
                show_message=False,
                show_point=True,
                point_size=12,
                color="#4aa3ff",
                left_clicking=True,
                clear_on_no_selection=True,
            )
        except TypeError:
            # Compatibility fallback for older pyvista versions.
            self.plotter.enable_point_picking(
                callback=self._on_pick,
                show_message=False,
                show_point=True,
                point_size=12,
                color="#4aa3ff",
                left_clicking=True,
            )

    def _on_pick(self, point) -> None:
        if point is None:
            self.selectionChanged.emit("Selection cleared")
            return
        coordinates = np.asarray(point, dtype=float).reshape(-1)
        if coordinates.size >= 3:
            self.selectionChanged.emit(
                f"Surface picked at ({coordinates[0]:.2f}, {coordinates[1]:.2f}, {coordinates[2]:.2f}) mm"
            )

    def _activate_probe(self) -> None:
        self.selectionChanged.emit("Probe active — left-click a surface in the 3D viewport")
