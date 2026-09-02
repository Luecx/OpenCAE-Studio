"""Provide file choosers that consistently remember the last visited directory."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QFileDialog


_LAST_DIRECTORY_KEY = "file_dialog/last_directory"


def open_file(parent, title: str, file_filter: str, initial: str = "", settings=None) -> str:
    """Open a file chooser starting from the explicit path or last visited directory."""
    store = _settings(settings)
    value, _ = QFileDialog.getOpenFileName(
        parent,
        str(title),
        _initial_path(initial, store),
        str(file_filter),
    )
    if value:
        _remember_directory(value, store)
    return str(value or "")


def save_file(parent, title: str, file_filter: str, initial: str = "", settings=None) -> str:
    """Open a save chooser and remember the directory of an accepted target."""
    store = _settings(settings)
    value, _ = QFileDialog.getSaveFileName(
        parent,
        str(title),
        _initial_path(initial, store),
        str(file_filter),
    )
    if value:
        _remember_directory(value, store)
    return str(value or "")


def _initial_path(initial: str, settings) -> str:
    """Resolve relative filenames against the last accepted file-dialog directory."""
    initial = str(initial or "").strip()
    remembered = str(settings.value(_LAST_DIRECTORY_KEY, "") or "").strip()
    if not initial:
        return remembered

    path = Path(initial).expanduser()
    if path.is_absolute():
        return str(path)
    if remembered:
        return str(Path(remembered) / path)
    return str(path)


def _remember_directory(path: str, settings) -> None:
    """Persist only the parent directory so different file types can reuse it."""
    try:
        directory = str(Path(path).expanduser().resolve().parent)
    except (OSError, RuntimeError, ValueError):
        directory = str(Path(path).expanduser().parent)
    if directory:
        settings.setValue(_LAST_DIRECTORY_KEY, directory)
        settings.sync()


def _settings(settings):
    return settings if settings is not None else QSettings()
