"""Coordinates project file, settings, and unit-system application flows."""

from pathlib import Path

from opencae.geometry.cache import CACHE
from opencae.model.entities.jobs import ResultSet
from opencae.model.naming import next_name
from opencae.model.project import Project
from opencae.persistence.project_io import load_project, save_project
from opencae.results import FrdLoader
from opencae.store.commands import CompositeCommand, UpdateFieldCommand
from opencae.ui.core.application_preferences import apply_application_preferences
from opencae.ui.core.file_dialogs import open_file, save_file
from opencae.ui.dialogs.preferences import PreferencesDialog
from opencae.ui.dialogs.project_settings import ProjectSettingsDialog
from opencae.ui.preferences.runtime import apply_window_preferences

from .dialog_runner import get_values


class ProjectController:
    """Orchestrate document lifecycle actions for the desktop application."""

    def __init__(self, store, parent, settings):
        self.store = store
        self.parent = parent
        self.settings = settings

    def new(self):
        """Replace the current document with a clean Project."""
        project = Project()
        project.unit_system = self.settings.selected_unit_system
        CACHE.clear()
        self.store.replace(project, "New project")

    def open(self):
        """Load a current-format project without disturbing the open one on error."""
        path = open_file(
            self.parent,
            "Open Project",
            "OpenCAE project (*.ocae);;JSON (*.json)",
        )
        if not path:
            return

        try:
            project = load_project(Path(path))
            self._ensure_unit_system(project)
        except Exception as exc:
            self.store.message.emit(f"Could not open project: {exc}")
            return

        CACHE.clear()
        self.store.replace(project, f"Opened {path}")
        self._fit_loaded_content()

    def open_results(self):
        """Attach an external FRD result set to the current Project."""
        path = open_file(
            self.parent,
            "Open Results",
            "FRD results (*.frd);;All files (*)",
        )
        if not path:
            return
        try:
            fields = FrdLoader().fields(path)
        except Exception as exc:
            self.store.message.emit(f"Could not open results: {exc}")
            return
        name = next_name(Path(path).stem or "Solution", self.store.project.results)
        result = ResultSet(
            name=name,
            job_ref=None,
            source_file=str(Path(path)),
            status="Available",
            fields=fields,
            metadata={"external": True},
        )
        self.store.add_entity(
            f"Opened results {Path(path).name}",
            self.store.project.id,
            "results",
            result,
        )
        self.parent.show_solution(result)

    def save(self, save_as=False):
        """Save atomically, leaving the current path unchanged after failures."""
        path = self.store.project.path
        if save_as or path is None:
            value = save_file(
                self.parent,
                "Save Project",
                "OpenCAE project (*.ocae)",
                str(path or "project.ocae"),
            )
            if not value:
                return
            path = Path(value)
        try:
            save_project(self.store.project, path)
        except Exception as exc:
            self.store.message.emit(f"Could not save project: {exc}")
            return
        self.store.message.emit(f"Saved {path}")

    def settings_dialog(self):
        """Edit project name and unit system as one reversible command."""
        dialog = ProjectSettingsDialog(self.settings.unit_systems, self.parent)
        dialog._editors["name"].setText(self.store.project.name)
        dialog._editors["unit_system"].setCurrentText(
            self.store.project.unit_system
        )
        values = get_values(dialog)
        if values:
            self.settings.selected_unit_system = values["unit_system"]
            command = CompositeCommand(
                (
                    UpdateFieldCommand(
                        self.store.project.id,
                        "name",
                        self.store.project.name,
                        values["name"],
                    ),
                    UpdateFieldCommand(
                        self.store.project.id,
                        "unit_system",
                        self.store.project.unit_system,
                        values["unit_system"],
                    ),
                )
            )
            self.store.execute("Updated project properties", command)

    def preferences(self, page="General"):
        """Open the authoritative application Settings dialog."""
        # QAction.triggered forwards a checked bool to slots. Treat that as the
        # normal no-argument invocation rather than as an initial page name.
        if isinstance(page, bool):
            page = "General"

        context = getattr(self.parent, "context", None)
        solvers = getattr(context, "solvers", {}) if context is not None else {}
        dialog = PreferencesDialog(
            self.settings,
            solvers=solvers,
            parent=self.parent,
            initial_page=str(page or "General"),
        )
        dialog.applied.connect(self._apply_preferences)
        dialog.exec()

    def _apply_preferences(self, values):
        """Persist one validated Settings snapshot and refresh live-safe UI state."""
        preferences = dict(values.get("preferences", {}) or {})
        for key, value in preferences.items():
            self.settings.set_preference(key, value)

        self.settings.solver_configs = dict(values.get("solver_configs", {}) or {})
        requested_solver = str(values.get("selected_solver", "") or "")
        configs = self.settings.solver_configs
        self.settings.selected_solver = (
            requested_solver if requested_solver in configs else next(iter(configs), "")
        )

        systems = list(values.get("unit_systems", ()) or ())
        if systems:
            self.settings.unit_systems = systems
        selected_unit = str(values.get("selected_unit_system", "") or "")
        if selected_unit:
            self.settings.selected_unit_system = selected_unit

        self.settings.sync()

        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            apply_application_preferences(app, self.settings)
        apply_window_preferences(self.parent, self.settings)

        if selected_unit:
            self.set_unit_system(selected_unit)
        ribbon = getattr(self.parent, "ribbon", None)
        if ribbon is not None and hasattr(ribbon, "refresh_solvers"):
            ribbon.refresh_solvers()
        self.parent.refresh_action_states()
        self.store.message.emit("Settings updated")

    def unit_preferences(self):
        """Open the Unit Systems page in the global Settings dialog."""
        self.preferences("Unit Systems")

    def set_unit_system(self, name):
        """Set a configured unit system through the Project Store."""
        if name not in {item.name for item in self.settings.unit_systems}:
            return
        self.settings.selected_unit_system = name
        if self.store.project.unit_system == name:
            return
        self.store.execute(
            f"Changed unit system to {name}",
            UpdateFieldCommand(
                self.store.project.id,
                "unit_system",
                self.store.project.unit_system,
                name,
            ),
        )

    def _ensure_unit_system(self, project):
        """Reject unknown persisted units instead of silently changing semantics."""
        names = {item.name for item in self.settings.unit_systems}
        if project.unit_system not in names:
            raise ValueError(
                f"Project uses unknown unit system '{project.unit_system}'"
            )

    def _fit_loaded_content(self):
        """Frame newly opened project content when the viewport preference allows it."""
        if not bool(
            self.settings.preference("viewport/auto_fit_loaded_content", True)
        ):
            return
        viewport = getattr(self.parent, "viewport", None)
        if viewport is not None:
            viewport.request_refresh(fit=True)

    @staticmethod
    def _apply_project_settings(project, values):
        """Apply settings to a detached Project candidate."""
        project.name = values["name"]
        project.unit_system = values["unit_system"]
