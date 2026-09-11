"""Apply persisted application preferences to already constructed UI surfaces."""

from __future__ import annotations


def apply_window_preferences(window, settings) -> None:
    """Apply live-safe Settings values to the current main window in one place."""
    viewport = getattr(window, "viewport", None)
    if viewport is not None:
        _apply_viewport(viewport, settings)
    ribbon = getattr(window, "ribbon", None)
    results = getattr(ribbon, "results_page", None) if ribbon is not None else None
    if results is not None:
        _apply_result_defaults(results, settings)


def wire_window_preferences(window, settings) -> None:
    """Persist user-driven viewport changes that also have a Settings representation."""
    viewport = getattr(window, "viewport", None)
    toolbar = getattr(viewport, "toolbar", None) if viewport is not None else None
    signal = getattr(toolbar, "projection_changed", None)
    if signal is not None:
        signal.connect(
            lambda parallel: settings.set_value(
                "viewport/projection",
                "Parallel" if parallel else "Perspective",
            )
        )


def _apply_viewport(viewport, settings) -> None:
    projection = str(settings.preference("viewport/projection", "Perspective"))
    parallel = projection.casefold() == "parallel"
    plotter = getattr(viewport, "plotter", None)
    setter = getattr(plotter, "set_parallel_projection", None)
    if callable(setter):
        setter(parallel)
    toolbar = getattr(viewport, "toolbar", None)
    if toolbar is not None and hasattr(toolbar, "set_projection"):
        toolbar.set_projection(parallel)

    cube = getattr(viewport, "view_cube", None)
    if cube is not None:
        cube.setVisible(bool(settings.preference("viewport/show_view_cube", True)))


def _apply_result_defaults(page, settings) -> None:
    defaults = (
        ("mesh_lines", "results/show_mesh_lines", True),
        ("boundary_lines", "results/show_boundary_lines", True),
        ("undeformed", "results/show_undeformed", False),
    )
    changed = False
    for attribute, key, fallback in defaults:
        button = getattr(page, attribute, None)
        if button is None:
            continue
        requested = bool(settings.preference(key, fallback))
        if button.isChecked() != requested:
            button.blockSignals(True)
            button.setChecked(requested)
            button.blockSignals(False)
            changed = True
    if changed and getattr(page, "result", None) is not None:
        page._emit()
