"""Provides the first integrated Input Deck Format Manager editor shell."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.templates import dialog_buttons, dialog_layout

from .catalog import GLOBAL_PAGES
from .global_settings import DeckGlobalSettings
from .navigation import DeckFormatNavigation
from .template_editor import DeckTemplateEditor


class DeckFormatManagerDialog(QDialog):
    """Prototype the deck-profile editing workflow without export persistence."""

    applied = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """Build the profile toolbar, ordered navigation, editor and preview."""
        super().__init__(parent)
        self.setWindowTitle("Input Deck Format Manager")
        self.resize(1450, 860)
        self.setMinimumSize(1120, 700)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._profiles = {
            "FEMaster": ["FEMaster - Default", "FEMaster - Custom"],
            "Abaqus": ["Abaqus - Default"],
        }
        self._session_templates: dict[str, str] = {}
        self._current_template_key = ""
        self._loading = False

        root = dialog_layout(self)
        root.addLayout(self._build_toolbar())

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
        self.template_page.changed.connect(self._template_changed)
        self.format_combo.currentTextChanged.connect(self._format_changed)
        self.profile_combo.currentTextChanged.connect(lambda _text: self._mark_dirty())
        self._format_changed(self.format_combo.currentText())
        self.navigation.select_key("materials.isotropic_elastic")

    def select_key(self, key: str) -> bool:
        """Select one record in the navigation tree."""
        return self.navigation.select_key(key)

    def apply_changes(self) -> None:
        """Commit current editor state to the in-dialog profile session."""
        self._store_current_template()
        self.setWindowModified(False)
        self.applied.emit(self.format_combo.currentText(), self.profile_combo.currentText())

    def _build_toolbar(self) -> QHBoxLayout:
        """Build the profile-management controls requested for the manager."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Built-in Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(("FEMaster", "Abaqus"))
        self.format_combo.setMinimumWidth(190)
        layout.addWidget(self.format_combo)
        layout.addSpacing(12)
        layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(260)
        layout.addWidget(self.profile_combo, 1)

        self.new_button = self._toolbar_button("New Profile", IconKind.FILE, self._new_profile)
        self.copy_button = self._toolbar_button("Copy", IconKind.DUPLICATE, self._copy_profile)
        self.delete_button = self._toolbar_button("Delete", IconKind.DELETE, self._delete_profile)
        self.save_button = self._toolbar_button("Save", IconKind.SAVE, self.apply_changes)
        for button in (self.new_button, self.copy_button, self.delete_button, self.save_button):
            layout.addWidget(button)
        return layout

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

    @staticmethod
    def _toolbar_button(text: str, icon: IconKind, callback) -> QPushButton:
        """Create one compact top profile-management action button."""
        button = QPushButton(text)
        button.setIcon(make_icon(icon, 18))
        button.clicked.connect(callback)
        return button

    def _show_record(self, key: str, label: str) -> None:
        """Switch the right page to global settings, overview, or a template."""
        self._store_current_template()
        self.breadcrumb.setText(self._breadcrumb(key, label))
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
        self.template_page.load_record(key, label, self._session_templates.get(key))
        self._loading = False
        self.stack.setCurrentWidget(self.template_page)

    def _breadcrumb(self, key: str, label: str) -> str:
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
        self._session_templates[self._current_template_key] = self.template_page.template_text()
        self._mark_dirty()

    def _store_current_template(self) -> None:
        """Retain the selected template before navigating elsewhere."""
        if self._current_template_key:
            self._session_templates[self._current_template_key] = self.template_page.template_text()

    def _format_changed(self, name: str) -> None:
        """Refresh the temporary profile list for the selected built-in format."""
        current = self.profile_combo.currentText()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self._profiles.get(name, ()))
        if current in self._profiles.get(name, ()):
            self.profile_combo.setCurrentText(current)
        self.profile_combo.blockSignals(False)
        self._mark_dirty(False)

    def _new_profile(self) -> None:
        """Create a session-only profile so the management workflow can be tested."""
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        profile = name.strip()
        values = self._profiles.setdefault(self.format_combo.currentText(), [])
        if profile not in values:
            values.append(profile)
            self.profile_combo.addItem(profile)
        self.profile_combo.setCurrentText(profile)
        self._mark_dirty()

    def _copy_profile(self) -> None:
        """Copy the selected profile inside the current editor session."""
        current = self.profile_combo.currentText() or "Profile"
        values = self._profiles.setdefault(self.format_combo.currentText(), [])
        base = current + " Copy"
        candidate = base
        number = 2
        while candidate in values:
            candidate = f"{base} {number}"
            number += 1
        values.append(candidate)
        self.profile_combo.addItem(candidate)
        self.profile_combo.setCurrentText(candidate)
        self._mark_dirty()

    def _delete_profile(self) -> None:
        """Delete user profiles while keeping the first built-in default profile."""
        index = self.profile_combo.currentIndex()
        if index <= 0:
            return
        values = self._profiles.get(self.format_combo.currentText(), [])
        if 0 <= index < len(values):
            values.pop(index)
        self.profile_combo.removeItem(index)
        self._mark_dirty()

    def _mark_dirty(self, dirty: bool = True) -> None:
        """Track unsaved editor-session changes using the standard window state."""
        self.setWindowModified(dirty)

    def _accept(self) -> None:
        """Apply the editor session before closing with OK."""
        self.apply_changes()
        self.accept()
