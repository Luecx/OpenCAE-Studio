"""Provide the integrated Input Deck Format Manager editor shell."""

from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.deck_formats import DeckProfile
from opencae.ui.templates import (
    LabelRole,
    SectionHeading,
    dialog_buttons,
    dialog_layout,
    label,
)

from .catalog import GLOBAL_PAGES
from .global_settings import DEFAULT_GLOBAL_SETTINGS, DeckGlobalSettings
from .navigation import DeckFormatNavigation
from .profile_state import build_profile, record_states_from_profile
from .profile_toolbar import DeckProfileToolbar
from .template_catalog import TEMPLATE_SPECS
from .template_editor import DeckTemplateEditor


class DeckFormatManagerDialog(QDialog):
    """Edit and persist deck profiles consumed by the normal export pipeline."""

    applied = pyqtSignal(str, str)

    def __init__(self, parent=None, *, settings=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Input Deck Format Manager[*]")
        self.resize(1450, 860)
        self.setMinimumSize(1120, 700)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._session_records: dict[str, dict[str, dict[str, object]]] = {}
        self._session_orders: dict[str, dict[str, tuple[str, ...]]] = {}
        self._session_globals: dict[str, dict[str, object]] = {}
        self._current_template_key = ""
        self._loading = False

        root = dialog_layout(self)
        self.profile_toolbar = DeckProfileToolbar()
        root.addWidget(self.profile_toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.navigation = DeckFormatNavigation()
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

        self._load_persisted_profiles()
        self._active_profile = self.profile_toolbar.profile_name()
        self.navigation.set_format(self.profile_toolbar.format_name())

        self.navigation.current_changed.connect(self._show_record)
        self.navigation.order_changed.connect(self._order_changed)
        self.template_page.changed.connect(self._record_changed)
        self.global_page.changed.connect(self._global_changed)
        self.profile_toolbar.save_requested.connect(self.apply_changes)
        self.profile_toolbar.selection_changed.connect(self._profile_changed)
        self.profile_toolbar.profile_copied.connect(self._profile_copied)
        self.profile_toolbar.profile_created.connect(self._profile_created)
        self.profile_toolbar.profile_deleted.connect(self._profile_deleted)

        self._restore_profile_state(self._active_profile)
        self.navigation.select_key("materials.elastic.isotropic")
        self._apply_editability()
        self.setWindowModified(False)

    def select_key(self, key: str) -> bool:
        return self.navigation.select_key(key)

    def apply_changes(self) -> None:
        """Persist the current editable profile and select it for its base format."""
        self._store_current_profile_state()
        if self.profile_toolbar.is_editable():
            profile = self._runtime_profile(self._active_profile)
            if self.settings is not None:
                self.settings.save_deck_profile(profile)
        self._persist_active_selection()
        self.setWindowModified(False)
        self.applied.emit(self.profile_toolbar.format_name(), self._active_profile)

    def _build_editor_area(self) -> QWidget:
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

    def _load_persisted_profiles(self) -> None:
        """Load user profiles from AppSettings before connecting selection signals."""
        if self.settings is not None:
            for raw in self.settings.deck_profiles.values():
                profile = DeckProfile.from_dict(raw)
                if profile is None:
                    continue
                if self.profile_toolbar.register_profile(
                    profile.name, profile.format_name
                ):
                    self._session_records[profile.name] = record_states_from_profile(
                        profile
                    )
                    self._session_orders[profile.name] = dict(profile.order)
                    self._session_globals[profile.name] = dict(profile.settings)

            initial = self.settings.active_deck_profile_name("FEMaster")
            if not self.profile_toolbar.set_profile(initial):
                self.profile_toolbar.set_profile("FEMaster")

    def _show_record(self, key: str, label_text: str) -> None:
        self._display_record(key, label_text, store_current=True)

    def _display_record(self, key: str, label_text: str, *, store_current: bool) -> None:
        if store_current:
            self._store_current_record()
        self.breadcrumb.setText(self._breadcrumb(label_text))
        self._current_template_key = ""
        if key in GLOBAL_PAGES:
            self.global_page.set_section(GLOBAL_PAGES[key])
            self.stack.setCurrentWidget(self.global_page)
            return
        if self.navigation.is_category(key):
            self.overview_title.setText(label_text)
            self.overview_text.setText(
                "Select a child record to inspect its keyword/data template. "
                "Move Up and Move Down control sibling output order."
            )
            self.stack.setCurrentWidget(self.overview_page)
            return

        self._loading = True
        self._current_template_key = key
        state = self._session_records.get(self._active_profile, {}).get(key)
        self.template_page.load_record(
            key,
            label_text,
            state,
            supported=self.navigation.is_supported(
                key, self.profile_toolbar.format_name()
            ),
        )
        self._loading = False
        self.stack.setCurrentWidget(self.template_page)

    def _profile_changed(self) -> None:
        previous = getattr(self, "_active_profile", "")
        if previous:
            self._store_current_profile_state(previous)
        self._active_profile = self.profile_toolbar.profile_name()
        self.navigation.set_format(self.profile_toolbar.format_name())
        self._restore_profile_state(self._active_profile)
        self._apply_editability()
        item = self.navigation.tree.currentItem()
        if item is not None:
            self._display_record(
                self.navigation.current_key(), item.text(0), store_current=False
            )
        self.setWindowModified(False)

    def _profile_copied(self, source: str, target: str) -> None:
        self._store_current_profile_state(source)
        self._session_records[target] = deepcopy(
            self._session_records.get(source, {})
        )
        self._session_orders[target] = deepcopy(
            self._session_orders.get(source, self._default_order)
        )
        self._session_globals[target] = deepcopy(
            self._session_globals.get(source, DEFAULT_GLOBAL_SETTINGS)
        )

    def _profile_created(self, name: str, _format_name: str) -> None:
        self._session_records[name] = {}
        self._session_orders[name] = deepcopy(self._default_order)
        self._session_globals[name] = dict(DEFAULT_GLOBAL_SETTINGS)

    def _profile_deleted(self, name: str) -> None:
        self._session_records.pop(name, None)
        self._session_orders.pop(name, None)
        self._session_globals.pop(name, None)
        if self.settings is not None:
            self.settings.delete_deck_profile(name)

    def _restore_profile_state(self, name: str) -> None:
        order = self._session_orders.get(name, self._default_order)
        self.navigation.set_order_state(order)
        globals_state = self._session_globals.get(name, DEFAULT_GLOBAL_SETTINGS)
        self.global_page.load_state(globals_state)

    def _store_current_profile_state(self, profile: str | None = None) -> None:
        target = profile or self._active_profile
        if not target:
            return
        self._store_current_record(profile=target)
        self._session_orders[target] = self.navigation.order_state()
        self._session_globals[target] = self.global_page.state()

    def _runtime_profile(self, name: str) -> DeckProfile:
        format_name = self.profile_toolbar.format_name()
        support = {
            key: self.navigation.is_supported(key, format_name)
            for key in TEMPLATE_SPECS
        }
        return build_profile(
            name,
            format_name,
            self._session_records.get(name, {}),
            self._session_orders.get(name, self._default_order),
            self._session_globals.get(name, DEFAULT_GLOBAL_SETTINGS),
            support,
        )

    def _persist_active_selection(self) -> None:
        if self.settings is not None:
            self.settings.set_active_deck_profile(
                self.profile_toolbar.format_name(),
                self.profile_toolbar.profile_name(),
            )

    def _apply_editability(self) -> None:
        editable = self.profile_toolbar.is_editable()
        self.navigation.set_editable(editable)
        self.template_page.set_editable(editable)
        self.global_page.set_editable(editable)
        if self.apply_button is not None:
            self.apply_button.setEnabled(editable)

    def _breadcrumb(self, label_text: str) -> str:
        item = self.navigation.tree.currentItem()
        labels = [label_text]
        parent = item.parent() if item is not None else None
        while parent is not None:
            labels.append(parent.text(0))
            parent = parent.parent()
        return " > ".join(reversed(labels))

    def _record_changed(self) -> None:
        if (
            self._loading
            or not self._current_template_key
            or not self.profile_toolbar.is_editable()
        ):
            return
        self._session_records.setdefault(self._active_profile, {})[
            self._current_template_key
        ] = self.template_page.record_state()
        self._mark_dirty()

    def _global_changed(self) -> None:
        if self._loading or not self.profile_toolbar.is_editable():
            return
        self._session_globals[self._active_profile] = self.global_page.state()
        self._mark_dirty()

    def _store_current_record(self, *, profile: str | None = None) -> None:
        target = profile or self._active_profile
        if not target or not self._current_template_key:
            return
        if target in {"FEMaster", "Abaqus"}:
            return
        self._session_records.setdefault(target, {})[
            self._current_template_key
        ] = self.template_page.record_state()

    def _order_changed(self) -> None:
        if not self.profile_toolbar.is_editable():
            return
        self._session_orders[self._active_profile] = self.navigation.order_state()
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        if self.profile_toolbar.is_editable():
            self.setWindowModified(True)

    def _accept(self) -> None:
        """Persist edits and active profile before closing with OK."""
        self._store_current_profile_state()
        if self.profile_toolbar.is_editable() and self.settings is not None:
            self.settings.save_deck_profile(self._runtime_profile(self._active_profile))
        self._persist_active_selection()
        self.accept()
