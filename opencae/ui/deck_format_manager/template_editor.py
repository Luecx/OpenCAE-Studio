"""Provides the record-level template and live-preview editor page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QPlainTextEdit, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from opencae.ui.core.fields import FieldSpec, create_editor
from opencae.ui.templates import (
    ButtonSpec,
    LabelRole,
    SectionHeading,
    apply_primary_control_height,
    button,
    field_block,
    label,
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
        self._fields: tuple[tuple[str, str, str], ...] = ()
        self._repeat_fields: tuple[str, ...] = ()
        self._repeat_examples: tuple[dict[str, str], ...] = ()
        self._repeatable = False
        self._editable = True

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addLayout(self._build_controls())

        editor_split = QSplitter(Qt.Orientation.Horizontal)
        editor_split.addWidget(self._build_template_panel())
        editor_split.addWidget(self._build_fields_panel())
        editor_split.setStretchFactor(0, 3)
        editor_split.setStretchFactor(1, 2)
        editor_split.setSizes((720, 400))
        root.addWidget(editor_split, 3)

        preview_header = QHBoxLayout()
        preview_header.addWidget(SectionHeading("Output Preview"))
        preview_header.addStretch(1)
        preview_header.addWidget(label("Representative values", role=LabelRole.MUTED))
        root.addLayout(preview_header)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(170)
        self.preview.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        root.addWidget(self.preview, 2)

        self.template.textChanged.connect(self._template_changed)
        self.enabled.toggled.connect(self._template_changed)
        self.float_format.currentTextChanged.connect(self._template_changed)
        self.repeat_rows.toggled.connect(self._template_changed)
        self.fields.itemDoubleClicked.connect(lambda _item, _column: self.insert_selected_field())
        self.insert_button.clicked.connect(self.insert_selected_field)

    def load_record(self, key: str, label_text: str, text: str | None = None) -> None:
        """Load a record specification while optionally restoring session text."""
        self._key = key
        spec = template_spec(key, label_text)
        self._fields = tuple(spec["fields"])
        self._repeatable = bool(spec.get("repeatable", False))
        self._repeat_fields = tuple(spec.get("repeat_fields", ()))
        self._repeat_examples = tuple(spec.get("repeat_examples", ()))
        self.repeat_rows.blockSignals(True)
        self.repeat_rows.setChecked(bool(spec.get("repeat_default", False)))
        self.repeat_rows.setVisible(self._repeatable)
        self.repeat_rows.blockSignals(False)
        self.template.blockSignals(True)
        self.template.setPlainText(text if text is not None else str(spec["template"]))
        self.template.blockSignals(False)
        self._populate_fields()
        self._update_preview()
        self.set_editable(self._editable)

    def set_editable(self, editable: bool) -> None:
        """Toggle record inputs while keeping help fields and preview readable."""
        self._editable = bool(editable)
        for control in (self.enabled, self.float_format, self.repeat_rows, self.template, self.insert_button):
            control.setEnabled(self._editable)

    def template_text(self) -> str:
        """Return the complete keyword-and-data template currently being edited."""
        return self.template.toPlainText()

    def available_field_names(self) -> tuple[str, ...]:
        """Return the placeholder names exposed for the current record."""
        return tuple(name for name, _description, _example in self._fields)

    def is_repeatable(self) -> bool:
        """Return whether this record supports repeated data rows."""
        return self._repeatable

    def insert_field(self, name: str) -> None:
        """Insert one available placeholder at the current template cursor."""
        if not self._editable or name not in self.available_field_names():
            return
        cursor = self.template.textCursor()
        cursor.insertText("{" + name + "}")
        self.template.setTextCursor(cursor)
        self.template.setFocus()

    def insert_selected_field(self) -> None:
        """Insert the field selected in the helper table at the edit cursor."""
        item = self.fields.currentItem()
        if item is not None:
            self.insert_field(str(item.data(0, _FIELD_ROLE)))

    def _build_controls(self) -> QHBoxLayout:
        """Build canonical record-level controls."""
        controls = QHBoxLayout()
        enabled = create_editor(FieldSpec("enabled", "Enabled", kind="bool", default=True))
        repeat = create_editor(FieldSpec("repeat", "Repeat data rows", kind="bool", default=False))
        if not isinstance(enabled, QCheckBox) or not isinstance(repeat, QCheckBox):
            raise TypeError("Deck boolean controls must use QCheckBox")
        self.enabled = enabled
        self.enabled.setText("Enabled")
        self.repeat_rows = repeat
        self.repeat_rows.setText("Repeat data rows")
        self.repeat_rows.hide()
        self.float_format = create_editor(
            FieldSpec(
                "float_format",
                "Float format",
                kind="choice",
                choices=(".6g", ".8g", ".12g", ".6f", ".12e"),
                default=".6g",
            )
        )
        controls.addWidget(self.enabled)
        controls.addWidget(self.repeat_rows)
        controls.addStretch(1)
        controls.addWidget(field_block("Float format", self.float_format))
        return controls

    def _build_template_panel(self) -> QWidget:
        """Build the unified keyword/data template panel."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.addWidget(SectionHeading("Template Editor"))
        helper = label(
            "Keyword options and data lines are edited together. Placeholders may be used anywhere in the block.",
            role=LabelRole.MUTED,
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.template = QPlainTextEdit()
        self.template.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.template.setTabChangesFocus(False)
        layout.addWidget(self.template, 1)
        return panel

    def _build_fields_panel(self) -> QWidget:
        """Build the helper panel documenting every usable placeholder."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.addWidget(SectionHeading("Available Fields"))
        helper = label(
            "Double-click a field or select it and insert it at the template cursor.",
            role=LabelRole.MUTED,
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.fields = QTreeWidget()
        self.fields.setHeaderLabels(("Field", "Meaning", "Scope", "Example"))
        self.fields.setRootIsDecorated(False)
        self.fields.setAlternatingRowColors(True)
        self.fields.setColumnWidth(0, 165)
        self.fields.setColumnWidth(1, 235)
        self.fields.setColumnWidth(2, 105)
        layout.addWidget(self.fields, 1)
        self.insert_button = apply_primary_control_height(
            button(ButtonSpec("Insert at Cursor"), clicked=self.insert_selected_field)
        )
        layout.addWidget(self.insert_button)
        return panel

    def _populate_fields(self) -> None:
        """Refresh placeholder documentation and repeated-row scope information."""
        self.fields.clear()
        for name, description, example in self._fields:
            scope = "Repeated row" if name in self._repeat_fields else "Record"
            item = QTreeWidgetItem(("{" + name + "}", description, scope, example))
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
        text = render_preview(
            self.template.toPlainText(),
            self._fields,
            repeat_rows=self._repeat_examples,
            repeat=self._repeatable and self.repeat_rows.isChecked(),
        )
        if self._key.startswith("materials.") and self._key != "materials.header":
            text = "*MATERIAL, NAME=STEEL\n" + text
        self.preview.setPlainText(text if self.enabled.isChecked() else "<record disabled>")
