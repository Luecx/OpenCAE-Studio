"""Filesystem and native file-dialog preferences."""

from __future__ import annotations

from opencae.ui.core.directory_path import DirectoryPathEditor

from .page import PreferencePage


class FilesPage(PreferencePage):
    """Edit shared file-dialog history and default directory behavior."""

    def __init__(self, settings, parent=None):
        super().__init__(
            "Files & Projects",
            "Configure where OpenCAE file choosers start. Project data itself remains stored with the project.",
            parent,
        )
        self.add_section("File dialogs")
        self.add_toggle(
            settings,
            "files/remember_last_directory",
            "Remember the last directory used by Open and Save dialogs",
            default=True,
        )
        directory = DirectoryPathEditor(
            str(settings.preference("files/default_directory", "") or "")
        )
        self.add_custom_field(
            "files/default_directory",
            "Default directory when no history is available",
            directory,
            directory.text,
        )
        self.finish()
