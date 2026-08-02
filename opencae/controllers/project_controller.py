from pathlib import Path

from PyQt6.QtWidgets import QFileDialog

from opencae.geometry.cache import CACHE
from opencae.model.project import Project
from opencae.model.entities.jobs import ResultSet
from opencae.results import FrdLoader
from opencae.model.naming import next_name
from opencae.persistence.project_io import load_project, save_project
from opencae.ui.dialogs.preferences import PreferencesDialog
from opencae.ui.dialogs.project_settings import ProjectSettingsDialog
from .dialog_runner import get_values


class ProjectController:
    def __init__(self, store, parent, settings): self.store = store; self.parent = parent; self.settings = settings

    def new(self):
        CACHE.clear(); project = Project(); project.unit_system = self.settings.selected_unit_system
        self.store.replace(project, "New project")

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self.parent, "Open Project", "", "OpenCAE project (*.ocae);;JSON (*.json)")
        if path:
            CACHE.clear(); project = load_project(Path(path)); self._ensure_unit_system(project)
            self.store.replace(project, f"Opened {path}")


    def open_results(self):
        path, _ = QFileDialog.getOpenFileName(self.parent, "Open Results", "", "FRD results (*.frd);;All files (*)")
        if not path: return
        try: fields = FrdLoader().fields(path)
        except Exception as exc:
            self.store.message.emit(f"Could not open results: {exc}"); return
        name = next_name(Path(path).stem or "Solution", self.store.project.results)
        result = ResultSet(name=name, job_name="External", source_file=str(Path(path)), status="Available", fields=fields, metadata={"external": True})
        self.store.mutate(f"Opened results {Path(path).name}", lambda project: project.results.append(result))
        self.parent.show_solution(result)

    def save(self, save_as=False):
        path = self.store.project.path
        if save_as or path is None:
            value, _ = QFileDialog.getSaveFileName(self.parent, "Save Project", str(path or Path.cwd() / "project.ocae"), "OpenCAE project (*.ocae)")
            if not value: return
            path = Path(value)
        save_project(self.store.project, path); self.store.message.emit(f"Saved {path}")

    def settings_dialog(self):
        dialog = ProjectSettingsDialog(self.settings.unit_systems, self.parent)
        dialog._editors["name"].setText(self.store.project.name); dialog._editors["unit_system"].setCurrentText(self.store.project.unit_system)
        values = get_values(dialog)
        if values:
            self.settings.selected_unit_system = values["unit_system"]
            self.store.mutate("Updated project settings", lambda project: self._apply_project_settings(project, values))

    def preferences(self, page="General"):
        values = get_values(PreferencesDialog(self.settings, self.parent, page))
        if not values: return
        self.settings.solver_configs = values.pop("solver_configs"); self.settings.unit_systems = values.pop("unit_systems")
        selected = values.pop("selected_unit_system"); self.settings.selected_unit_system = selected
        for key, value in values.items(): self.settings.set_value("ui/" + key, value)
        enabled = self.settings.enabled_solvers()
        if self.settings.selected_solver not in enabled: self.settings.selected_solver = enabled[0] if enabled else ""
        self.set_unit_system(selected); self.parent.ribbon.refresh_solvers(); self.parent.refresh_action_states(); self.store.message.emit("Preferences updated")


    def unit_preferences(self): self.preferences("Unit Systems")

    def set_unit_system(self, name):
        if name not in {item.name for item in self.settings.unit_systems}: return
        self.settings.selected_unit_system = name
        self.store.mutate(f"Changed unit system to {name}", lambda project: setattr(project, "unit_system", name))

    def _ensure_unit_system(self, project):
        names = {item.name for item in self.settings.unit_systems}
        if project.unit_system not in names: project.unit_system = self.settings.selected_unit_system

    @staticmethod
    def _apply_project_settings(project, values):
        project.name = values["name"]; project.unit_system = values["unit_system"]
