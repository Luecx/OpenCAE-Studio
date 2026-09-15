"""Coordinates project file, settings, and unit-system application flows."""

from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

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
        """Open a clean Project in the multi-document workspace."""
        project = Project()
        project.unit_system = self.settings.selected_unit_system
        CACHE.clear()
        self._open_project(project, "New project")

    def open(self):
        """Load a current-format project without disturbing open projects on error."""
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
        if not self._open_project(project, f"Opened {path}"):
            return
        self._fit_loaded_content()

    def open_results(self):
        """Attach exactly one external FRD result set to the current Project."""
        path = open_file(
            self.parent,
            "Open Results",
            "FRD results (*.frd);;All files (*)",
        )
        if not path:
            return
        source = Path(path)
        if source.suffix.lower() != ".frd":
            self.store.message.emit(
                "Could not open results: OpenCAE Results accepts FRD files only"
            )
            return
        try:
            fields = FrdLoader().fields(source)
        except Exception as exc:
            self.store.message.emit(f"Could not open results: {exc}")
            return
        name = next_name(source.stem or "Solution", self.store.project.results)
        result = ResultSet(
            name=name,
            job_ref=None,
            source_file=str(source),
            status="Available",
            fields=fields,
            metadata={"external": True},
        )
        self.store.add_entity(
            f"Opened results {source.name}",
            self.store.project.id,
            "results",
            result,
        )
        self.parent.show_solution(result)

    def save(self, save_as=False):
        """Save the active project atomically."""
        return self._save_project_instance(self.store.project, save_as=bool(save_as))

    def close_project(self, index):
        """Ask whether to save one open Project, then remove it from the workspace."""
        projects = tuple(getattr(self.store, "projects", (self.store.project,)))
        try:
            index = int(index)
        except (TypeError, ValueError):
            return False
        if not 0 <= index < len(projects):
            return False

        project = projects[index]
        if self._project_has_active_tasks(project):
            QMessageBox.warning(
                self.parent,
                "Project is busy",
                "Stop or finish active project tasks before closing this project.",
            )
            return False

        name = str(getattr(project, "name", "Project") or "Project")
        prompt = QMessageBox(self.parent)
        prompt.setIcon(QMessageBox.Icon.Question)
        prompt.setWindowTitle("Close Project")
        prompt.setText(f"Save '{name}' before closing it?")
        prompt.setInformativeText(
            "Choose Save to write the project first, Don't Save to close it "
            "without saving, or Cancel to keep it open."
        )
        save_button = prompt.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard_button = prompt.addButton(
            "Don't Save",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = prompt.addButton(QMessageBox.StandardButton.Cancel)
        prompt.setDefaultButton(save_button)
        prompt.setEscapeButton(cancel_button)
        prompt.exec()

        clicked = prompt.clickedButton()
        if clicked is cancel_button or clicked is None:
            return False
        if clicked is save_button and not self._save_project_instance(project):
            return False
        if clicked is not save_button and clicked is not discard_button:
            return False

        closer = getattr(self.store, "close_project", None)
        if not callable(closer) or not closer(index):
            return False
        CACHE.clear()
        self.store.message.emit(f"Closed {name}")
        return True

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

    def _save_project_instance(self, project, *, save_as=False):
        """Persist one specific Project without changing the active document."""
        path = getattr(project, "path", None)
        if save_as or path is None:
            value = save_file(
                self.parent,
                "Save Project",
                "OpenCAE project (*.ocae)",
                str(path or "project.ocae"),
            )
            if not value:
                return False
            path = Path(value)
        try:
            save_project(project, Path(path))
        except Exception as exc:
            self.store.message.emit(f"Could not save project: {exc}")
            return False
        self.store.message.emit(f"Saved {path}")
        return True

    def _project_has_active_tasks(self, project):
        """Keep asynchronous solver/result work from outliving its Project."""
        controllers = getattr(self.parent, "controllers", None)
        jobs = getattr(controllers, "jobs", None)
        if jobs is None:
            return False
        project_job_ids = {job.id for job in getattr(project, "jobs", ())}
        runners = set(getattr(jobs, "_runners", {}))
        metadata_tasks = set(getattr(jobs, "_result_metadata_tasks", {}))
        return bool(project_job_ids.intersection(runners | metadata_tasks))

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

    def _open_project(self, project, description):
        """Use multi-document opening when available, retaining legacy store support."""
        add_project = getattr(self.store, "add_project", None)
        try:
            if callable(add_project):
                add_project(project, description)
            else:
                self.store.replace(project, description)
        except ValueError as exc:
            self.store.message.emit(f"Could not open project: {exc}")
            return False
        return True

    @staticmethod
    def _apply_project_settings(project, values):
        """Apply settings to a detached Project candidate."""
        project.name = values["name"]
        project.unit_system = values["unit_system"]
