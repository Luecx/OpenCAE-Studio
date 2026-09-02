"""Regression coverage for remembered file-browser locations."""

from pathlib import Path

from opencae.ui.core.file_dialogs import (
    _LAST_DIRECTORY_KEY,
    _initial_path,
    _remember_directory,
)


class _Settings:
    def __init__(self):
        self.values = {}
        self.sync_count = 0

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        self.sync_count += 1


def test_relative_file_name_uses_last_browser_directory(tmp_path):
    settings = _Settings()
    settings.values[_LAST_DIRECTORY_KEY] = str(tmp_path)

    assert Path(_initial_path("project.ocae", settings)) == tmp_path / "project.ocae"
    assert _initial_path("", settings) == str(tmp_path)


def test_accepted_file_updates_last_browser_directory(tmp_path):
    settings = _Settings()
    target = tmp_path / "nested" / "model.inp"

    _remember_directory(str(target), settings)

    assert Path(settings.values[_LAST_DIRECTORY_KEY]) == target.parent
    assert settings.sync_count == 1
