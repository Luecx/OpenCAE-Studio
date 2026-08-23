"""Provides the integrated Input Deck Format Manager editor shell."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QSplitter, QStackedWidget, QVBoxLayout, QWidget

from opencae.ui.templates import LabelRole, SectionHeading, dialog_buttons, dialog_layout, label

from .catalog import GLOBAL_PAGES
from .global_settings import DeckGlobalSettings
from .navigation import DeckFormatNavigation
from .profile_toolbar import DeckProfileToolbar
from .template_editor import DeckTemplateEditor


class DeckFormatManagerDialog(QDialog):
    """Prototype profile editing while keeping built-in format profiles immutable."""

    applied = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """Build profile controls, ordered navigation, editor and live preview."""
        super().__init__(parent)
        self.setWindowTitle("Input Deck Format Manager[*]")
        self.resize(1450, 860)
        self.setMinimumSize(1120, 700)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._session_templates: dict[str, dict[str, str]] = {}
        self._session_orders: dict[str, dict[str, tuple[str, ...]]] = {}
        self._current_template_key = ""
        self._loading = False

        root = dialog_layout(self)
        self.profile_toolbar = DeckProfileToolbar()
        root.addWidget(self.profile_toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.navigation = DeckFormatNavigation()
        self.navigation.set_format(self.profile_toolbar.format_name())
        self.navigation.setMinimumWidth(330)
        self._default_order = self.navigation.order_state()
        splitter.addWidget(self.navigation)
        splitter.addWidget(self._build_editor_area())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes((350, 1050))
        root.addWidget(splitter, 1)

        buttons = dialog_buttons(include_apply=True)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        self.apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if self.apply_button is not None:
            self.apply_button.clicked.connect(self.apply_changes)
        root.addWidget(buttons)

        self._active_profile = self.profile_toolbar.profile_name()
        self.navigation.current_changed.connect(self._show_record)
        self.navigation.order_changed.connect(self._order_changed)
        self.template_page.changed.connect(self._template_changed)
        self.profile_toolbar.save_requested.connect(self.apply_changes)
        self.profile_toolbar.selection_changed.connect(self._profile_changed)
        self.profile_toolbar.profile_copied.connect(self._profile_copied)
        self.profile_toolbar.profile_created.connect(self._profile_created)
        self.profile_toolbar.profile_deleted.connect(self._profile_deleted)
        self.navigation.select_key("materials.isotropic_elastic")
        self._apply_editability()
        self.setWindowModified(False)

    def select_key(self, key: str) -> bool:
        """Select one record in the navigation tree."""
        return self.navigation.select_key(key)

    def apply_changes(self) -> None:
        """Commit current user-profile state to the in-dialog session."""
        if not self.profile_toolbar.is_editable():
            return
        self._store_current_template()
        self._session_orders[self._active_profile] = self.navigation.order_state()
        self.setWindowModified(False)
        self.applied.emit(self.profile_toolbar.format_name(), self._active_profile)

    def _build_editor_area(self) -> QWidget:
        """Build breadcrumb plus the context-sensitive right-hand editor stack."""
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(10)
        self.breadcrumb = label("", role=LabelRole.GROUP)
        layout.addWidget(self.breadcrumb)
        self.stack = QStackedWidget()
        self.template_page = DeckTemplateEditor()
        self.global_page = DeckGlobalSettings()
        self.overview_page = QWidget()
        overview_layout = QVBoxLayout(self.overview_page)
        self.overview_title = SectionHeading("")
        self.overview_text = label("", role=LabelRole.MUTED)
        self.overview_text.setWordWrap(True)
        overview_layout.addWidget(self.overview_title)
        overview_layout.addWidget(self.overview_text)
        overview_layout.addStretch(1)
        for page in (self.template_page, self.global_page, self.overview_page):
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        return area

    def _show_record(self, key: str, label_text: str) -> None:
        """Switch the right page after preserving the current editable template."""
        self._display_record(key, label_text, store_current=True)

    def _display_record(self, key: str, label_text: str, *, store_current: bool) -> None:
        """Display settings, support information, categories, or one record template."""
        if store_current:
            self._store_current_template()
        self.breadcrumb.setText(self._breadcrumb(label_text))
        self._current_template_key = ""
        if key in GLOBAL_PAGES:
            self.global_page.set_section(GLOBAL_PAGES[key])
            self.stack.setCurrentWidget(self.global_page)
            return
        if self.navigation.is_category(key):
            self.overview_title.setText(label_text)
            self.overview_text.setText(
                "Select a child record to edit its complete keyword/data template. "
                "Use Move Up and Move Down on the left to control sibling output order."
            )
            self.stack.setCurrentWidget(self.overview_page)
            return
        format_name = self.profile_toolbar.format_name()
        if not self.navigation.is_supported(key, format_name):
            self.overview_title.setText(f"{label_text} — Not Supported")
            self.overview_text.setText(
                f"{label_text} is part of the OpenCAE constraint model, but {format_name} "
                "does not support this record. It remains visible so profile capability "
                "differences are explicit instead of silently hiding model features."
            )
            self.stack.setCurrentWidget(self.overview_page)
            return
        self._loading = True
        self._current_template_key = key
        text = self._session_templates.get(self._active_profile, {}).get(key)
        self.template_page.load_record(key, label_text, text)
        self._loading = False
        self.stack.setCurrentWidget(self.template_page)

    def _profile_changed(self) -> None:
        """Switch isolated editor/order state when the selected profile changes."""
        previous = self._active_profile
        self._store_current_template(profile=previous)
        if previous:
            self._session_orders[previous] = self.navigation.order_state()
        self._active_profile = self.profile_toolbar.profile_name()
        self.navigation.set_format(self.profile_toolbar.format_name())
        order = self._session_orders.get(self._active_profile, self._default_order)
        self.navigation.set_order_state(order)
        self._apply_editability()
        item = self.navigation.tree.currentItem()
        if item is not None:
            self._display_record(self.navigation.current_key(), item.text(0), store_current=False)
        self.setWindowModified(False)

    def _profile_copied(self, source: str, target: str) -> None:
        """Copy current template/order state when creating a profile copy."""
        self._store_current_template(profile=source)
        self._session_templates[target] = deepcopy(self._session_templates.get(source, {}))
        self._session_orders[target] = deepcopy(
            self._session_orders.get(source, self.navigation.order_state())
        )

    def _profile_created(self, name: str, _format_name: str) -> None:
        """Initialize a new editable profile from default ordering and templates."""
        self._session_templates[name] = {}
        self._session_orders[name] = deepcopy(self._default_order)

    def _profile_deleted(self, name: str) -> None:
        """Discard session state for a deleted user profile."""
        self._session_templates.pop(name, None)
        self._session_orders.pop(name, None)

    def _apply_editability(self) -> None:
        """Make built-in FEMaster/Abaqus profiles view-only throughout the editor."""
        editable = self.profile_toolbar.is_editable()
        self.navigation.set_editable(editable)
        self.template_page.set_editable(editable)
        self.global_page.set_editable(editable)
        if self.apply_button is not None:
            self.apply_button.setEnabled(editable)

    def _breadcrumb(self, label_text: str) -> str:
        """Build a readable breadcrumb from the selected tree hierarchy."""
        item = self.navigation.tree.currentItem()
        labels = [label_text]
        parent = item.parent() if item is not None else None
        while parent is not None:
            labels.append(parent.text(0))
            parent = parent.parent()
        return " > ".join(reversed(labels))

    def _template_changed(self) -> None:
        """Remember edits locally and mark the user profile dirty."""
        if self._loading or not self._current_template_key or not self.profile_toolbar.is_editable():
            return
        self._session_templates.setdefault(self._active_profile, {})[
            self._current_template_key
        ] = self.template_page.template_text()
        self._mark_dirty()

    def _store_current_template(self, *, profile: str | None = None) -> None:
        """Retain the selected template for a user profile before navigation."""
        target = profile or self._active_profile
        if not target or not self._current_template_key:
            return
        # The two built-in profiles are never given mutable session overrides.
        if target in {"FEMaster", "Abaqus"}:
            return
        self._session_templates.setdefault(target, {})[
            self._current_template_key
        ] = self.template_page.template_text()

    def _order_changed(self) -> None:
        """Store ordering only for editable user profiles."""
        if not self.profile_toolbar.is_editable():
            return
        self._session_orders[self._active_profile] = self.navigation.order_state()
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        """Track unsaved user-profile changes using standard window state."""
        if self.profile_toolbar.is_editable():
            self.setWindowModified(True)

    def _accept(self) -> None:
        """Apply editable profile state before closing with OK."""
        if self.profile_toolbar.is_editable():
            self.apply_changes()
        self.accept()
