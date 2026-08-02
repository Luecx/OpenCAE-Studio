from __future__ import annotations

import json
from pathlib import Path
from PyQt6.QtCore import QSettings

from opencae.units import UnitSystem, default_systems

_DEFAULT_SOLVERS = {
    "FEMaster": {"enabled": False, "executable": "", "extra_arguments": ""},
    "Abaqus": {"enabled": False, "executable": "", "extra_arguments": ""},
    "CalculiX": {"enabled": False, "executable": "", "extra_arguments": ""},
}


class AppSettings:
    def __init__(self): self._settings = QSettings("OpenCAE", "OpenCAE Studio")
    def value(self, key: str, default=None): return self._settings.value(key, default)
    def set_value(self, key: str, value) -> None: self._settings.setValue(key, value)

    @property
    def selected_solver(self) -> str: return str(self.value("solver/selected", ""))
    @selected_solver.setter
    def selected_solver(self, value: str) -> None: self.set_value("solver/selected", value)

    @property
    def solver_configs(self) -> dict:
        raw = self.value("solver/configs", "")
        try: stored = json.loads(str(raw)) if raw else {}
        except Exception: stored = {}
        configs = {name: dict(values) for name, values in _DEFAULT_SOLVERS.items()}
        for name, values in stored.items():
            if name in configs: configs[name].update(values)
        return configs

    @solver_configs.setter
    def solver_configs(self, configs: dict) -> None:
        self.set_value("solver/configs", json.dumps(configs))

    def solver_config(self, name: str) -> dict:
        return dict(self.solver_configs.get(name, {}))

    def enabled_solvers(self) -> list[str]:
        result = []
        for name, config in self.solver_configs.items():
            executable = str(config.get("executable", ""))
            if config.get("enabled") and executable and Path(executable).is_file(): result.append(name)
        return result


    @property
    def unit_systems(self) -> list[UnitSystem]:
        raw = self.value("units/systems", "")
        try: values = json.loads(str(raw)) if raw else []
        except Exception: values = []
        systems = [UnitSystem.from_dict(item) for item in values if isinstance(item, dict)]
        return systems or default_systems()

    @unit_systems.setter
    def unit_systems(self, systems) -> None:
        self.set_value("units/systems", json.dumps([item.to_dict() for item in systems]))

    @property
    def selected_unit_system(self) -> str:
        names = [item.name for item in self.unit_systems]
        selected = str(self.value("units/selected", names[0] if names else ""))
        return selected if selected in names else (names[0] if names else "")

    @selected_unit_system.setter
    def selected_unit_system(self, value: str) -> None:
        self.set_value("units/selected", value)

    def unit_system(self, name: str = "") -> UnitSystem:
        systems = self.unit_systems
        return next((item for item in systems if item.name == (name or self.selected_unit_system)), systems[0])

    @property
    def working_directory(self) -> str: return str(self.value("solver/working_directory", ""))
    @working_directory.setter
    def working_directory(self, value: str) -> None: self.set_value("solver/working_directory", value)

    @property
    def solver(self) -> str: return self.selected_solver
    @solver.setter
    def solver(self, value: str) -> None: self.selected_solver = value
    @property
    def solver_executable(self) -> str: return str(self.solver_config(self.selected_solver).get("executable", ""))
    @property
    def extra_arguments(self) -> str: return str(self.solver_config(self.selected_solver).get("extra_arguments", ""))
