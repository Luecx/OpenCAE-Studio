"""Builds the main window ribbon, viewport, docks and status widgets."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSizePolicy, QToolBar

from opencae.ui.docks.output_dock import OutputDock
from opencae.ui.docks.project_dock import ProjectDock
from opencae.ui.ribbon.ribbon import Ribbon
from opencae.ui.status_unit_system import UnitSystemStatus
from opencae.ui.viewport.viewport_factory import create_viewport


def build_ribbon(window):
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
    window.viewport = create_viewport(window.context.store)
    window.viewport.visibility = window.visibility
    window.visibility.changed.connect(window.viewport.request_refresh)
    window.visibility.changed.connect(
        lambda: window.viewport.show_model_selection(window.context.store.selection)
    )
    window.setCentralWidget(window.viewport)
    window.context.store.scene_changed.connect(window.viewport.request_refresh)
    window.context.store.active_part_changed.connect(window.viewport.request_refresh)
    window.viewport.selection_changed.connect(window.context.store.select)
    window.context.store.selection_changed.connect(window.viewport.show_model_selection)
    window.viewport.message.connect(window.context.store.message.emit)
    window.viewport.request_refresh(fit=True)


def build_docks(window):
    store = window.context.store
    window.project_dock = ProjectDock(
        store,
        window.actions,
        visibility=window.visibility,
        parent=window,
    )
    window.output_dock = OutputDock(
        store,
        window.controllers.jobs,
        window.actions,
        window,
    )
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window.project_dock)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window.output_dock)
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
    window.resizeDocks(
        [window.project_dock],
        [285],
        Qt.Orientation.Horizontal,
    )
    window.resizeDocks(
        [window.output_dock],
        [205],
        Qt.Orientation.Vertical,
    )


def build_status(window):
    window.statusBar().showMessage("Ready")
    window.units = UnitSystemStatus(window)
    window.units.system_selected.connect(window.controllers.project.set_unit_system)
    window.units.edit_requested.connect(window.controllers.project.unit_preferences)
    window.statusBar().addPermanentWidget(window.units)
    window.refresh_title()
