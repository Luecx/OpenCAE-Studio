"""Reusable visual scaffold for application Settings pages."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from opencae.ui.core.fields import FieldSpec, create_editor, editor_value
from opencae.ui.templates import FieldLabel, SectionHeading, field_block


class PreferencePage(QWidget):
    """Build one Settings page with a header, semantic sections and value readers."""

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self._readers: dict[str, Callable[[], object]] = {}
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(2, 2, 8, 8)
        self.root.setSpacing(14)

        heading = QLabel(str(title))
        heading.setObjectName("PreferencesPageTitle")
        self.root.addWidget(heading)

        summary = FieldLabel(str(description))
        summary.setObjectName("PreferencesPageDescription")
        summary.setWordWrap(True)
        self.root.addWidget(summary)
        self.root.addSpacing(6)

    def add_section(self, title: str, description: str = "") -> None:
        """Start a visual setting family, optionally with muted explanatory text."""
        self.root.addWidget(SectionHeading(str(title)))
        if description:
            label = FieldLabel(str(description))
            label.setWordWrap(True)
            self.root.addWidget(label)

    def add_field(
        self,
        settings,
        key: str,
        label: str,
        *,
        default,
        kind: str = "text",
        choices=(),
        minimum=-1.0e12,
        maximum=1.0e12,
        decimals: int = 4,
        suffix: str = "",
    ):
        """Create one canonical editor backed by an exact persistent preference key."""
        value = _setting(settings, key, default)
        editor = create_editor(
            FieldSpec(
                key,
                label,
                kind=kind,
                default=value,
                choices=tuple(choices),
                minimum=minimum,
                maximum=maximum,
                decimals=decimals,
                suffix=suffix,
            )
        )
        self.root.addWidget(field_block(label, editor))
        self._readers[str(key)] = lambda editor=editor: editor_value(editor)
        return editor

    def add_toggle(self, settings, key: str, text: str, *, default: bool):
        """Create a compact checkbox whose text explains the enabled behavior."""
        toggle = QCheckBox(str(text))
        toggle.setChecked(bool(_setting(settings, key, default)))
        self.root.addWidget(toggle)
        self._readers[str(key)] = toggle.isChecked
        return toggle

    def add_custom_field(
        self,
        key: str,
        label: str,
        widget: QWidget,
        reader: Callable[[], object],
    ) -> QWidget:
        """Register a focused custom editor while preserving the page value contract."""
        self.root.addWidget(field_block(label, widget))
        self._readers[str(key)] = reader
        return widget

    def finish(self) -> None:
        """Keep settings grouped at the top when the dialog is taller than a page."""
        self.root.addStretch(1)

    def values(self) -> dict[str, object]:
        """Return exact QSettings keys and normalized Python values for this page."""
        return {key: reader() for key, reader in self._readers.items()}


def _setting(settings, key: str, default):
    """Read one typed preference from AppSettings or a compatible settings object."""
    reader = getattr(settings, "preference", None)
    if callable(reader):
        return reader(key, default)
    value = settings.value(key, default)
    if isinstance(default, bool):
        return str(value).strip().lower() not in {"0", "false", "no", "off"}
    return value
