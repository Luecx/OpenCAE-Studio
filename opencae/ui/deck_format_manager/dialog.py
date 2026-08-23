"""Provides the first integrated Input Deck Format Manager editor shell."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.templates import dialog_buttons, dialog_layout

from .catalog import GLOBAL_PAGES
from .global_settings import DeckGlobalSettings
from .navigation import DeckFormatNavigation
from .profile_toolbar import DeckProfileToolbar
from .template_editor import DeckTemplateEditor


class DeckFormatManagerDialog(QDialog):
    """Prototype the deck-profile editing workflow without export persistence."""

    applied = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """Build profile controls, ordered navigation, editor and live preview."""
        super().__init__(parent)
        self.setWindowTitle("Input Deck Format Manager[*]")
        self.resize(1450, 860)
        self.setMinimumSize(1120, 700)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._session_templates: dict[str, str] = {}
        self._current_template_key = ""
        self._loading = False

        root = dialog_layout(self)
        self.profile_toolbar = DeckProfileToolbar()
        root.addWidget(self.profile_toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.navigation = DeckFormatNavigation()
        self.navigation.setMinimumWidth(330)
        splitter.addWidget(self.navigation)
        splitter.addWidget(self._build_editor_area())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes((350, 1050))
        root.addWidget(splitter, 1)

        buttons = dialog_buttons(include_apply=True)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self.apply_changes)
        root.addWidget(buttons)

        self.navigation.current_changed.connect(self._show_record)
        self.navigation.order_changed.connect(self._mark_dirty)
        self.template_page.changed.connect(self._template_changed)
        self.profile_toolbar.save_requested.connect(self.apply_changes)
        self.profile_toolbar.selection_changed.connect(self._mark_dirty)
        self.navigation.select_key("materials.isotropic_elastic")
        self.setWindowModified(False)

    def select_key(self, key: str) -> bool:
        """Select one record in the navigation tree."""
        return self.navigation.select_key(key)

    def apply_changes(self) -> None:
        """Commit current editor state to the in-dialog profile session."""
        self._store_current_template()
        self.setWindowModified(False)
        self.applied.emit(
            self.profile_toolbar.format_name(),
            self.profile_toolbar.profile_name(),
        )

    def _build_editor_area(self) -> QWidget:
        """Build breadcrumb plus the context-sensitive right-hand editor stack."""
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(10)
        self.breadcrumb = QLabel()
        self.breadcrumb.setObjectName("SectionTitle")
        layout.addWidget(self.breadcrumb)
        self.stack = QStackedWidget()
        self.template_page = DeckTemplateEditor()
        self.global_page = DeckGlobalSettings()
        self.overview_page = QWidget()
        overview_layout = QVBoxLayout(self.overview_page)
        self.overview_title = QLabel()
        self.overview_title.setObjectName("SectionTitle")
        self.overview_text = QLabel()
        self.overview_text.setWordWrap(True)
        overview_layout.addWidget(self.overview_title)
        overview_layout.addWidget(self.overview_text)
        overview_layout.addStretch(1)
        for page in (self.template_page, self.global_page, self.overview_page):
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        return area

    def _show_record(self, key: str, label: str) -> None:
        """Switch the right page to global settings, overview, or a template."""
        self._store_current_template()
        self.breadcrumb.setText(self._breadcrumb(label))
        self._current_template_key = ""
        if key in GLOBAL_PAGES:
            self.global_page.set_section(GLOBAL_PAGES[key])
            self.stack.setCurrentWidget(self.global_page)
            return
        if self.navigation.is_category(key):
            self.overview_title.setText(label)
            self.overview_text.setText(
                "Select a child record to edit its complete keyword/data template. "
                "Use Move Up and Move Down on the left to control sibling output order."
            )
            self.stack.setCurrentWidget(self.overview_page)
            return
        self._loading = True
        self._current_template_key = key
        self.template_page.load_record(
            key,
            label,
            self._session_templates.get(key),
        )
        self._loading = False
        self.stack.setCurrentWidget(self.template_page)

    def _breadcrumb(self, label: str) -> str:
        """Build a readable breadcrumb from the selected tree hierarchy."""
        item = self.navigation.tree.currentItem()
        labels = [label]
        parent = item.parent() if item is not None else None
        while parent is not None:
            labels.append(parent.text(0))
            parent = parent.parent()
        return " > ".join(reversed(labels))

    def _template_changed(self) -> None:
        """Remember edits locally and mark the profile session dirty."""
        if self._loading or not self._current_template_key:
            return
        self._session_templates[
            self._current_template_key
        ] = self.template_page.template_text()
        self._mark_dirty()

    def _store_current_template(self) -> None:
        """Retain the selected template before navigating elsewhere."""
        if self._current_template_key:
            self._session_templates[
                self._current_template_key
            ] = self.template_page.template_text()

    def _mark_dirty(self, *_args) -> None:
        """Track unsaved editor-session changes using the standard window state."""
        self.setWindowModified(True)

    def _accept(self) -> None:
        """Apply the editor session before closing with OK."""
        self.apply_changes()
        self.accept()
