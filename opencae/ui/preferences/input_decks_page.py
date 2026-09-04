"""Default input-deck profiles for new Analyses."""

from __future__ import annotations

from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from opencae.deck_formats.selection import default_profile_id, profile_choices
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import FieldLabel, SectionHeading, apply_primary_control_height, field_block


class InputDecksPage(QWidget):
    """Choose each solver's default generator/profile and open the format manager."""

    def __init__(self, settings, solvers, manager_callback=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.solvers = dict(solvers or {})
        self.manager_callback = manager_callback
        self.selectors: dict[str, ChevronComboBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = FieldLabel("Input Decks")
        title.setObjectName("PreferencesPageTitle")
        layout.addWidget(title)
        description = FieldLabel(
            "Choose the default deck generator/profile used when a new Analysis is created for each solver."
        )
        description.setObjectName("PreferencesPageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(6)

        layout.addWidget(SectionHeading("Defaults for new analyses"))
        self.profile_host = QWidget()
        self.profile_layout = QVBoxLayout(self.profile_host)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(12)
        layout.addWidget(self.profile_host)
        self._rebuild_selectors()

        layout.addWidget(SectionHeading("Advanced formatting"))
        hint = FieldLabel(
            "The format manager controls keyword spelling, comments, numeric formatting and custom profile definitions."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        button = QPushButton("Manage Input Deck Formats…")
        button.setEnabled(callable(manager_callback))
        button.clicked.connect(self._open_manager)
        layout.addWidget(button)
        layout.addStretch(1)

    def _rebuild_selectors(self) -> None:
        """Rebuild solver-compatible profile choices after the manager changes."""
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.selectors.clear()

        for solver_name, adapter in self.solvers.items():
            selector = ChevronComboBox()
            for profile_id, name in profile_choices(self.settings, adapter):
                selector.addItem(name, profile_id)
            selected = self.settings.default_deck_profile_id(solver_name, adapter)
            index = selector.findData(selected)
            if index < 0:
                index = selector.findData(default_profile_id(adapter))
            selector.setCurrentIndex(max(0, index))
            apply_primary_control_height(selector)
            self.selectors[solver_name] = selector
            self.profile_layout.addWidget(
                field_block(f"{solver_name} default profile", selector)
            )

    def _open_manager(self) -> None:
        """Open the detailed manager and refresh profile choices after it closes."""
        if callable(self.manager_callback):
            self.manager_callback()
            self._rebuild_selectors()

    def values(self) -> dict[str, str]:
        """Return exact preference keys mapped to stable deck-profile identities."""
        return {
            f"solver/default_deck_profile/{solver_name}": str(
                selector.currentData() or ""
            )
            for solver_name, selector in self.selectors.items()
        }
