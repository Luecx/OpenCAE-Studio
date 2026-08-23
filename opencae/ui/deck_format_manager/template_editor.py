"""Provides the record-level template and live-preview editor page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .catalog import render_preview, template_spec


_FIELD_ROLE = int(Qt.ItemDataRole.UserRole)


class DeckTemplateEditor(QWidget):
    """Edit one complete keyword/data block and inspect its available fields."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build the unified template editor, field browser, and output preview."""
        super().__init__(parent)
        self._key = ""
        self._label = ""
        self._fields: tuple[tuple[str, str, str], ...] = ()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        controls = QHBoxLayout()
        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(True)
        controls.addWidget(self.enabled)
        controls.addStretch(1)
        controls.addWidget(QLabel("Float Format:"))
        self.float_format = QComboBox()
        self.float_format.addItems((".6g", ".8g", ".12g", ".6f", ".12e"))
        self.float_format.setMinimumWidth(110)
        controls.addWidget(self.float_format)
        root.addLayout(controls)

        editor_split = QSplitter(Qt.Orientation.Horizontal)
        editor_split.addWidget(self._build_template_panel())
        editor_split.addWidget(self._build_fields_panel())
        editor_split.setStretchFactor(0, 3)
        editor_split.setStretchFactor(1, 2)
        editor_split.setSizes((720, 400))
        root.addWidget(editor_split, 3)

        preview_header = QHBoxLayout()
        title = QLabel("Output Preview")
        title.setObjectName("SectionTitle")
        preview_header.addWidget(title)
        preview_header.addStretch(1)
        preview_header.addWidget(QLabel("Representative values"))
        root.addLayout(preview_header)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(170)
        self.preview.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        root.addWidget(self.preview, 2)

        self.template.textChanged.connect(self._template_changed)
        self.enabled.toggled.connect(self._template_changed)
        self.float_format.currentTextChanged.connect(self._template_changed)
        self.fields.itemDoubleClicked.connect(
            lambda _item, _column: self.insert_selected_field()
        )
        self.insert_button.clicked.connect(self.insert_selected_field)

    def load_record(self, key: str, label: str, text: str | None = None) -> None:
        """Load a record specification while optionally restoring session text."""
        self._key = key
        self._label = label
        spec = template_spec(key, label)
        self._fields = tuple(spec["fields"])
        self.template.blockSignals(True)
        self.template.setPlainText(text if text is not None else str(spec["template"]))
        self.template.blockSignals(False)
        self._populate_fields()
        self._update_preview()

    def template_text(self) -> str:
        """Return the complete keyword-and-data template currently being edited."""
        return self.template.toPlainText()

    def available_field_names(self) -> tuple[str, ...]:
        """Return the placeholder names exposed for the current record."""
        return tuple(name for name, _description, _example in self._fields)

    def insert_field(self, name: str) -> None:
        """Insert one available placeholder at the current template cursor."""
        if name not in self.available_field_names():
            return
        cursor = self.template.textCursor()
        cursor.insertText("{" + name + "}")
        self.template.setTextCursor(cursor)
        self.template.setFocus()

    def insert_selected_field(self) -> None:
        """Insert the field selected in the helper table at the edit cursor."""
        item = self.fields.currentItem()
        if item is None:
            return
        self.insert_field(str(item.data(0, _FIELD_ROLE)))

    def _build_template_panel(self) -> QWidget:
        """Build the left half containing the unified record template."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        title = QLabel("Template Editor")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        helper = QLabel(
            "Keyword options and data lines are edited together. Placeholders may "
            "be used anywhere in the block."
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.template = QPlainTextEdit()
        self.template.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.template.setTabChangesFocus(False)
        layout.addWidget(self.template, 1)
        return panel

    def _build_fields_panel(self) -> QWidget:
        """Build the right helper panel documenting every usable placeholder."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        title = QLabel("Available Fields")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        helper = QLabel(
            "Double-click a field or select it and insert it at the template cursor."
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.fields = QTreeWidget()
        self.fields.setHeaderLabels(("Field", "Meaning", "Example"))
        self.fields.setRootIsDecorated(False)
        self.fields.setAlternatingRowColors(True)
        self.fields.setColumnWidth(0, 170)
        self.fields.setColumnWidth(1, 220)
        layout.addWidget(self.fields, 1)
        self.insert_button = QPushButton("Insert at Cursor")
        layout.addWidget(self.insert_button)
        return panel

    def _populate_fields(self) -> None:
        """Refresh the placeholder documentation for the selected record."""
        self.fields.clear()
        for name, description, example in self._fields:
            item = QTreeWidgetItem(("{" + name + "}", description, example))
            item.setData(0, _FIELD_ROLE, name)
            self.fields.addTopLevelItem(item)
        if self.fields.topLevelItemCount():
            self.fields.setCurrentItem(self.fields.topLevelItem(0))

    def _template_changed(self, *_args) -> None:
        """Refresh the preview and mark the current session record dirty."""
        self._update_preview()
        self.changed.emit()

    def _update_preview(self) -> None:
        """Render a sample block without invoking a solver exporter."""
        text = render_preview(self.template.toPlainText(), self._fields)
        if self._key.startswith("materials.") and self._key != "materials.header":
            text = "*MATERIAL, NAME=STEEL\n" + text
        self.preview.setPlainText(
            text if self.enabled.isChecked() else "<record disabled>"
        )
