"""Canonical defaults for persistent application preferences.

These values describe application/workstation behavior. Project-owned geometry,
mesh and analysis entities keep their own persisted settings; the geometry and
mesh entries here are only defaults copied into newly created Parts.
"""

PREFERENCE_DEFAULTS = {
    "ui/confirm_delete": True,
    "ui/restore_layout": True,
    "appearance/font_scale": 100,
    "viewport/projection": "Perspective",
    "viewport/show_view_cube": True,
    "viewport/auto_fit_loaded_content": True,
    "files/remember_last_directory": True,
    "files/default_directory": "",
    "geometry/heal_on_import": True,
    "geometry/tolerance": 1.0e-7,
    "geometry/sew_faces": True,
    "geometry/make_solids": True,
    "geometry/remove_degenerate": True,
    "geometry/display_size_factor": 0.025,
    "mesh/algorithm_2d": "Frontal-Delaunay",
    "mesh/algorithm_3d": "HXT",
    "mesh/element_order": 1,
    "mesh/optimize": True,
    "mesh/high_order_optimize": True,
    "mesh/recombine_all": False,
    "mesh/num_threads": 0,
    "results/show_mesh_lines": True,
    "results/show_boundary_lines": True,
    "results/show_undeformed": False,
}

GEOMETRY_DEFAULT_KEYS = {
    "heal_on_import": "geometry/heal_on_import",
    "tolerance": "geometry/tolerance",
    "sew_faces": "geometry/sew_faces",
    "make_solids": "geometry/make_solids",
    "remove_degenerate": "geometry/remove_degenerate",
    "display_size_factor": "geometry/display_size_factor",
}

MESH_DEFAULT_KEYS = {
    "algorithm_2d": "mesh/algorithm_2d",
    "algorithm_3d": "mesh/algorithm_3d",
    "element_order": "mesh/element_order",
    "optimize": "mesh/optimize",
    "high_order_optimize": "mesh/high_order_optimize",
    "recombine_all": "mesh/recombine_all",
    "num_threads": "mesh/num_threads",
}
