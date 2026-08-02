from __future__ import annotations

import numpy as np
import pyvista as pv

from .seed_sampling import divisions, edge_overrides, sample_polyline


class SeedOverlay:
    POINTS = "seed-preview-points"
    LABELS = "seed-preview-labels"

    def __init__(self):
        self.positions = {}

    def clear(self, plotter, render=True):
        for name in (self.POINTS, self.LABELS):
            try:
                plotter.remove_actor(name, reset_camera=False, render=False)
            except Exception:
                pass
        self.positions.clear()
        if render:
            plotter.render()

    def show(self, plotter, snapshot, seeds):
        self.clear(plotter, render=False)
        if snapshot is None or not seeds:
            plotter.render()
            return
        default = next((item for item in seeds if item.seed_type == "Default"), None)
        overrides = edge_overrides(seeds)
        all_points, centers, labels = [], [], []
        for patch in snapshot.edges:
            count = divisions(patch, overrides.get(patch.tag), default)
            if count is None:
                continue
            points = sample_polyline(patch, count)
            all_points.extend(points)
            center = points[len(points) // 2]
            self.positions[f"Edge-{patch.tag}"] = center
            centers.append(center)
            labels.append(str(count))
        if all_points:
            plotter.add_mesh(
                pv.PolyData(np.asarray(all_points)), color="#f2b84b",
                point_size=7.0, render_points_as_spheres=True,
                lighting=False, pickable=False, name=self.POINTS,
                render=False,
            )
        if centers:
            plotter.add_point_labels(
                np.asarray(centers), labels, name=self.LABELS, font_size=10,
                text_color="#f7f9fb", point_size=0, shape="rounded_rect",
                fill_shape=True, margin=4, always_visible=False, render=False,
            )
        plotter.render()

    def nearest(self, renderer, x, y, height, radius=24.0):
        try:
            from vtkmodules.vtkRenderingCore import vtkCoordinate
            best = (radius * radius, None)
            for label, point in self.positions.items():
                coordinate = vtkCoordinate()
                coordinate.SetCoordinateSystemToWorld()
                coordinate.SetValue(*point)
                px, py = coordinate.GetComputedDisplayValue(renderer)
                distance = (x - px) ** 2 + ((height - y) - py) ** 2
                if distance < best[0]:
                    best = (distance, label)
            return best[1]
        except Exception:
            return None
