"""Input-deck profile selection inside the unified Settings surface."""

from __future__ import annotations

from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from opencae.deck_formats import DeckProfile
from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import FieldLabel, SectionHeading, apply_primary_control_height, field_block


class InputDecksPage(QWidget):
    """Choose active deck profiles and open the detailed format manager in-place."""

    FORMATS = ("FEMaster", "Abaqus", "CalculiX")

    def __init__(self, settings, manager_callback=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager_callback = manager_callback
        self.selectors: dict[str, ChevronComboBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 8, 8)
        layout.setSpacing(14)

        title = FieldLabel("Input Decks")
        title.setObjectName("PreferencesPageTitle")
        layout.addWidget(title)
        description = FieldLabel(
            "Choose the active format profile for each supported deck syntax. Detailed keyword formatting remains in the profile manager."
        )
        description.setObjectName("PreferencesPageDescription")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(6)

        layout.addWidget(SectionHeading("Active profiles"))
        self.profile_host = QWidget()
        self.profile_layout = QVBoxLayout(self.profile_host)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(12)
        layout.addWidget(self.profile_host)
        self._rebuild_selectors()

        layout.addWidget(SectionHeading("Profile manager"))
        button = QPushButton("Manage Input Deck Formats…")
        button.setEnabled(callable(manager_callback))
        button.clicked.connect(self._open_manager)
        layout.addWidget(button)
        layout.addStretch(1)

    def _rebuild_selectors(self) -> None:
        """Populate each format from its built-in plus compatible custom profiles."""
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.selectors.clear()

        for format_name in self.FORMATS:
            selector = ChevronComboBox()
            selector.addItem(format_name, format_name)
            for raw in self.settings.deck_profiles.values():
                profile = DeckProfile.from_dict(raw)
                if profile is not None and profile.format_name == format_name:
                    selector.addItem(profile.name, profile.name)
            selector.setCurrentText(self.settings.active_deck_profile_name(format_name))
            apply_primary_control_height(selector)
            self.selectors[format_name] = selector
            self.profile_layout.addWidget(field_block(f"{format_name} profile", selector))

    def _open_manager(self) -> None:
        """Open the detailed manager and refresh profile choices after it closes."""
        if callable(self.manager_callback):
            self.manager_callback()
            self._rebuild_selectors()

    def values(self) -> dict[str, str]:
        """Return active profile display names keyed by underlying format."""
        return {
            format_name: selector.currentText()
            for format_name, selector in self.selectors.items()
        }
