"""Persist application/workstation settings independently of project documents."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QSettings

from opencae.deck_formats import DeckProfile
from opencae.units import UnitSystem, default_systems

from .app_preference_defaults import (
    GEOMETRY_DEFAULT_KEYS,
    MESH_DEFAULT_KEYS,
    PREFERENCE_DEFAULTS,
)


_DEFAULT_SOLVERS = {
    "FEMaster": {"enabled": False, "executable": "", "extra_arguments": ""},
    "Abaqus": {"enabled": False, "executable": "", "extra_arguments": ""},
    "CalculiX": {"enabled": False, "executable": "", "extra_arguments": ""},
}


class AppSettings:
    """Persistent application preferences backed by Qt settings."""

    def __init__(self):
        self._settings = QSettings("OpenCAE", "OpenCAE Studio")

    def value(self, key: str, default=None):
        return self._settings.value(key, default)

    def set_value(self, key: str, value) -> None:
        self._settings.setValue(key, value)

    def sync(self) -> None:
        """Flush pending workstation settings to the platform settings backend."""
        self._settings.sync()

    def preference(self, key: str, default=None):
        """Read one scalar preference with the canonical default's Python type."""
        fallback = PREFERENCE_DEFAULTS.get(key, default)
        raw = self.value(key, fallback)
        if isinstance(fallback, bool):
            if isinstance(raw, bool):
                return raw
            return str(raw).strip().casefold() not in {"0", "false", "no", "off", ""}
        if isinstance(fallback, int) and not isinstance(fallback, bool):
            try:
                return int(raw)
            except (TypeError, ValueError):
                return int(fallback)
        if isinstance(fallback, float):
            try:
                return float(raw)
            except (TypeError, ValueError):
                return float(fallback)
        return raw

    def set_preference(self, key: str, value) -> None:
        """Persist one application preference using its exact canonical key."""
        self.set_value(str(key), value)

    def geometry_default_values(self) -> dict[str, object]:
        """Return GeometrySettings-compatible values for newly created Parts."""
        return {
            field: self.preference(key, PREFERENCE_DEFAULTS[key])
            for field, key in GEOMETRY_DEFAULT_KEYS.items()
        }

    def mesh_default_values(self) -> dict[str, object]:
        """Return MeshSettings-compatible values for newly created Parts."""
        return {
            field: self.preference(key, PREFERENCE_DEFAULTS[key])
            for field, key in MESH_DEFAULT_KEYS.items()
        }

    def default_deck_profile_id(self, solver_name: str, adapter=None) -> str:
        """Return a persisted solver deck default or the adapter's built-in profile."""
        from opencae.deck_formats.selection import (
            compatible_profile_ids,
            default_profile_id,
        )

        if adapter is None:
            return str(self.value(f"solver/default_deck_profile/{solver_name}", ""))
        fallback = default_profile_id(adapter)
        requested = str(
            self.value(f"solver/default_deck_profile/{solver_name}", fallback) or fallback
        )
        return (
            requested
            if requested in compatible_profile_ids(self, adapter)
            else fallback
        )

    def _json_value(self, key: str, default):
        raw = self.value(key, "")
        try:
            value = json.loads(str(raw)) if raw else default
        except (json.JSONDecodeError, TypeError, ValueError):
            value = default
        return value

    @property
    def selected_solver(self) -> str:
        return str(self.value("solver/selected", ""))

    @selected_solver.setter
    def selected_solver(self, value: str) -> None:
        self.set_value("solver/selected", value)

    @property
    def solver_configs(self) -> dict:
        stored = self._json_value("solver/configs", {})
        configs = {name: dict(values) for name, values in _DEFAULT_SOLVERS.items()}
        for name, values in stored.items():
            if name in configs:
                configs[name].update(values)
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
            if config.get("enabled") and executable and Path(executable).is_file():
                result.append(name)
        return result

    @property
    def deck_profiles(self) -> dict[str, dict]:
        """Return persisted user deck profiles keyed by display name."""
        value = self._json_value("deck_formats/profiles", {})
        return {
            str(name): dict(profile)
            for name, profile in value.items()
            if isinstance(profile, dict)
        }

    @deck_profiles.setter
    def deck_profiles(self, profiles: dict[str, dict]) -> None:
        self.set_value("deck_formats/profiles", json.dumps(profiles))

    @property
    def active_deck_profiles(self) -> dict[str, str]:
        """Return the selected manager profile name for each underlying format."""
        value = self._json_value("deck_formats/active", {})
        return {str(key): str(name) for key, name in value.items()}

    @active_deck_profiles.setter
    def active_deck_profiles(self, values: dict[str, str]) -> None:
        self.set_value("deck_formats/active", json.dumps(values))

    def save_deck_profile(self, profile: DeckProfile) -> None:
        """Persist one editable profile while preserving its stable identity."""
        profiles = self.deck_profiles
        for name, raw in tuple(profiles.items()):
            existing = DeckProfile.from_dict(raw)
            if (
                existing is not None
                and existing.profile_id == profile.profile_id
                and name != profile.name
            ):
                profiles.pop(name, None)
        profiles[profile.name] = profile.to_dict()
        self.deck_profiles = profiles

    def deck_profile_by_id(self, profile_id: str) -> DeckProfile | None:
        """Resolve one custom profile by stable identity rather than display name."""
        identity = str(profile_id or "")
        for raw in self.deck_profiles.values():
            profile = DeckProfile.from_dict(raw)
            if profile is not None and profile.profile_id == identity:
                return profile
        return None

    def delete_deck_profile(self, name: str) -> None:
        """Delete one user profile and fall back to its built-in base format."""
        profiles = self.deck_profiles
        profile = DeckProfile.from_dict(profiles.pop(str(name), None))
        self.deck_profiles = profiles
        active = self.active_deck_profiles
        for format_name, selected in tuple(active.items()):
            if selected == name:
                active[format_name] = profile.format_name if profile else format_name
        self.active_deck_profiles = active

    def set_active_deck_profile(self, format_name: str, profile_name: str) -> None:
        """Choose the profile highlighted when the format manager opens."""
        active = self.active_deck_profiles
        active[str(format_name)] = str(profile_name)
        self.active_deck_profiles = active

    def active_deck_profile_name(self, format_name: str) -> str:
        """Return the manager selection, defaulting to the immutable built-in."""
        return self.active_deck_profiles.get(str(format_name), str(format_name))

    def active_deck_profile(self, format_name: str) -> DeckProfile | None:
        """Return the manager-selected custom profile, or ``None`` for built-in."""
        name = self.active_deck_profile_name(format_name)
        if name == format_name:
            return None
        profile = DeckProfile.from_dict(self.deck_profiles.get(name))
        if profile is None or profile.format_name != format_name:
            return None
        return profile

    @property
    def unit_systems(self) -> list[UnitSystem]:
        values = self._json_value("units/systems", [])
        systems = [
            UnitSystem.from_dict(item) for item in values if isinstance(item, dict)
        ]
        return systems or default_systems()

    @unit_systems.setter
    def unit_systems(self, systems) -> None:
        self.set_value(
            "units/systems", json.dumps([item.to_dict() for item in systems])
        )

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
        return next(
            (
                item
                for item in systems
                if item.name == (name or self.selected_unit_system)
            ),
            systems[0],
        )

    @property
    def working_directory(self) -> str:
        return str(self.value("solver/working_directory", ""))

    @working_directory.setter
    def working_directory(self, value: str) -> None:
        self.set_value("solver/working_directory", value)

    @property
    def solver(self) -> str:
        return self.selected_solver

    @solver.setter
    def solver(self, value: str) -> None:
        self.selected_solver = value

    @property
    def solver_executable(self) -> str:
        return str(self.solver_config(self.selected_solver).get("executable", ""))

    @property
    def extra_arguments(self) -> str:
        return str(self.solver_config(self.selected_solver).get("extra_arguments", ""))
