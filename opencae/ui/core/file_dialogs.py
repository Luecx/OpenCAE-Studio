"""Provide file choosers with configurable shared directory history."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QFileDialog


_LAST_DIRECTORY_KEY = "file_dialog/last_directory"
_REMEMBER_KEY = "files/remember_last_directory"
_DEFAULT_DIRECTORY_KEY = "files/default_directory"


def open_file(parent, title: str, file_filter: str, initial: str = "", settings=None) -> str:
    """Open a file chooser using explicit, remembered, then configured paths."""
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
    """Open a save chooser and remember the directory when configured to do so."""
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
    """Resolve a chooser start path from explicit input and workstation preferences."""
    initial = str(initial or "").strip()
    remembered = (
        str(settings.value(_LAST_DIRECTORY_KEY, "") or "").strip()
        if _bool_value(settings.value(_REMEMBER_KEY, True), True)
        else ""
    )
    configured = str(settings.value(_DEFAULT_DIRECTORY_KEY, "") or "").strip()
    base = remembered or configured

    if not initial:
        return base

    path = Path(initial).expanduser()
    if path.is_absolute():
        return str(path)
    if base:
        return str(Path(base).expanduser() / path)
    return str(path)


def _remember_directory(path: str, settings) -> None:
    """Persist the accepted parent directory when history is enabled."""
    if not _bool_value(settings.value(_REMEMBER_KEY, True), True):
        return
    try:
        directory = str(Path(path).expanduser().resolve().parent)
    except (OSError, RuntimeError, ValueError):
        directory = str(Path(path).expanduser().parent)
    if directory:
        settings.setValue(_LAST_DIRECTORY_KEY, directory)
        settings.sync()


def _bool_value(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    return str(value).strip().casefold() not in {"0", "false", "no", "off", ""}


def _settings(settings):
    return settings if settings is not None else QSettings()
