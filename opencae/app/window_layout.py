"""Builds the main window ribbon, viewport, docks and status widgets."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSizePolicy, QToolBar

from opencae.ui.docks.output_dock import WorkspaceDock
from opencae.ui.docks.project_dock import ProjectDock
from opencae.ui.ribbon.ribbon import Ribbon
from opencae.ui.status_unit_system import UnitSystemStatus
from opencae.ui.viewport.stage_guidance import assembly_guidance
from opencae.ui.viewport.viewport_factory import create_viewport


def build_ribbon(window):
    """Create and attach the stage ribbon toolbar."""
    window.ribbon_host = QToolBar("Ribbon", window)
    window.ribbon_host.setObjectName("RibbonHost")
    window.ribbon_host.setMovable(False)
    window.ribbon_host.setFloatable(False)
    window.ribbon_host.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
    window.ribbon = Ribbon(
        window.actions,
        window.context.store,
        window.context.settings,
        window.context.solvers,
        window.refresh_action_states,
        controllers=window.controllers,
        parent=window,
    )
    window.ribbon.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Fixed,
    )
    window.ribbon_host.addWidget(window.ribbon)
    window.addToolBar(Qt.ToolBarArea.TopToolBarArea, window.ribbon_host)


def build_viewport(window):
    """Create the central viewport and connect scoped model/display invalidations."""
    window.viewport = create_viewport(window.context.store)
    window.viewport.visibility = window.visibility

    # Entity visibility can affect independently generated overlays and therefore
    # still invalidates the scene. Part topology visibility has a dedicated fast
    # path that toggles existing CAD actors instead of rebuilding all geometry.
    window.visibility.entity_changed.connect(window.viewport.request_refresh)
    window.visibility.topology_changed.connect(
        window.viewport.apply_topology_visibility
    )
    window.visibility.reset.connect(window.viewport.request_refresh)
    window.visibility.entity_changed.connect(
        lambda *_: window.viewport.show_model_selection(
            window.context.store.selection
        )
    )
    window.visibility.reset.connect(
        lambda: window.viewport.show_model_selection(
            window.context.store.selection
        )
    )

    window.setCentralWidget(window.viewport)
    window.context.store.scene_changed.connect(window.viewport.request_refresh)
    window.context.store.active_part_changed.connect(window.viewport.request_refresh)
    window.context.store.selection_changed.connect(window.viewport.show_model_selection)
    window.context.store.changed.connect(
        lambda *_: _sync_viewport_guidance(window)
    )
    window.viewport.selection_changed.connect(window.context.store.select)
    window.viewport.message.connect(window.context.store.message.emit)
    window.viewport.request_refresh(fit=True)


def build_docks(window):
    """Create the project browser and one movable lower workspace dock."""
    store = window.context.store
    window.project_dock = ProjectDock(
        store,
        window.actions,
        visibility=window.visibility,
        parent=window,
    )
    window.workspace_dock = WorkspaceDock(
        store,
        window.controllers.jobs,
        window.actions,
        window,
        results_page=window.ribbon.results_page,
        viewport=window.viewport,
    )

    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window.project_dock)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window.workspace_dock)
    window.workspace_dock.show()

    window.project_dock.tree.stage_requested.connect(window.ribbon.set_stage)
    window.project_dock.solution_tree.solution_requested.connect(window.show_solution)
    window.project_dock.solution_tree.delete_requested.connect(window.delete_result)
    window.project_dock.panel.browser_requested.connect(window.ribbon.set_browser)
    window.ribbon.result_requested.connect(window.viewport.show_solution)
    if window.ribbon.results_page is not None:
        window.viewport.section_changed.connect(
            window.ribbon.results_page.set_section_state
        )
    window.ribbon.stage_changed.connect(
        lambda stage: window.project_dock.panel.set_browser(
            "solution" if stage == "RESULTS" else "project"
        )
    )
    window.ribbon.stage_changed.connect(window.project_dock.tree.set_stage_focus)
    window.ribbon.stage_changed.connect(window.viewport.set_stage)
    window.ribbon.stage_changed.connect(
        lambda stage: _sync_viewport_guidance(window, stage)
    )
    window.resizeDocks(
        [window.project_dock],
        [285],
        Qt.Orientation.Horizontal,
    )
    window.resizeDocks(
        [window.workspace_dock],
        [300],
        Qt.Orientation.Vertical,
    )
    _sync_viewport_guidance(window)


def _sync_viewport_guidance(window, stage=None):
    """Show or clear centered guidance for stages that require assembly content."""
    notice = getattr(getattr(window.viewport, "canvas", None), "notice", None)
    if notice is None:
        return
    current_stage = stage or window.ribbon.current_stage
    message = assembly_guidance(
        current_stage,
        window.context.store.project,
    )
    if message is None:
        notice.clear()
    else:
        notice.set_message(*message)
    window.viewport.canvas._position_overlays()


def build_status(window):
    """Build the status bar and active unit-system control."""
    window.statusBar().showMessage("Ready")
    window.units = UnitSystemStatus(window)
    window.units.system_selected.connect(window.controllers.project.set_unit_system)
    window.units.edit_requested.connect(window.controllers.project.unit_preferences)
    window.statusBar().addPermanentWidget(window.units)
    window.refresh_title()
