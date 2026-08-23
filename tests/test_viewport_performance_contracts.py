"""Regression contracts for viewport invalidation and render-preparation behavior."""

from pathlib import Path

import numpy as np

from opencae.geometry.snapshots import (
    EdgePatch,
    GeometrySnapshot,
    SurfacePatch,
    VertexPatch,
)
from opencae.ui.viewport.geometry_render_cache import GeometryRenderCache


ROOT = Path(__file__).resolve().parents[1]


def _snapshot(fingerprint: str) -> GeometrySnapshot:
    """Build one tiny triangular CAD snapshot for render-cache tests."""
    return GeometrySnapshot(
        part_id="part-1",
        fingerprint=fingerprint,
        surfaces=[
            SurfacePatch(
                tag=1,
                points=np.asarray(
                    (
                        (0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0),
                        (0.0, 1.0, 0.0),
                    ),
                    dtype=float,
                ),
                faces=np.asarray((3, 0, 1, 2), dtype=np.int64),
            )
        ],
        edges=[
            EdgePatch(
                tag=2,
                points=np.asarray(
                    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
                    dtype=float,
                ),
                lines=np.asarray((2, 0, 1), dtype=np.int64),
            )
        ],
        vertices=[
            VertexPatch(tag=3, point=np.asarray((0.0, 0.0, 0.0)))
        ],
    )


def test_geometry_render_cache_reuses_prepared_polydata_for_same_fingerprint():
    """Repeated Geometry scene builds must not rerun clean/normal preparation."""
    cache = GeometryRenderCache()
    snapshot = _snapshot("geometry-a")

    first = cache.prepared(snapshot)
    second = cache.prepared(snapshot)

    assert first[0][1] is second[0][1]
    assert first[1][2] is second[1][2]
    assert first[2][3] is second[2][3]


def test_geometry_render_cache_replaces_stale_part_fingerprint():
    """A rebuilt Part must not reuse VTK datasets prepared for old geometry."""
    cache = GeometryRenderCache()
    first = cache.prepared(_snapshot("geometry-a"))
    second = cache.prepared(_snapshot("geometry-b"))

    assert first[0][1] is not second[0][1]


def test_scene_refresh_leaves_final_render_to_viewport_batch():
    """Full scene refresh must not render before pending overlays are restored."""
    source = (
        ROOT / "opencae/ui/viewport/pyvista_scene.py"
    ).read_text(encoding="utf-8")
    refresh = source[source.index("    def refresh("):source.index("    def clear(")]

    assert "plotter.render()" not in refresh


def test_result_query_does_not_install_left_clicking_pyvista_picker():
    """Result queries must pass through the shared camera-drag click gate."""
    source = (
        ROOT / "opencae/ui/viewport/result_query_state.py"
    ).read_text(encoding="utf-8")

    assert "enable_surface_point_picking" not in source
    assert "left_clicking=True" not in source
    assert "pick_display_position" in source


def test_jobs_panel_contains_no_solver_output_view():
    """The bottom Jobs surface is a Job list; solver text belongs to monitors."""
    source = (
        ROOT / "opencae/ui/panels/jobs_panel.py"
    ).read_text(encoding="utf-8")

    assert "MonospaceOutputView" not in source
    assert "output_changed" not in source
    assert "JOB_MONITOR" in source
