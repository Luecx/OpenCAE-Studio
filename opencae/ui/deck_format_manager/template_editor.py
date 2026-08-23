"""Provide the record-level template, field browser and live-preview editor page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

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

from .catalog import formatted_spec, render_preview, template_spec
from .code_editor import DeckCodeEditor
from .template_language import loop_from_spec, loop_skeleton


_INSERT_ROLE = int(Qt.ItemDataRole.UserRole)
_FIELD_NAME_ROLE = _INSERT_ROLE + 1


class DeckTemplateEditor(QWidget):
    """Edit one complete keyword/data block and inspect its available inputs."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        """Build the unified template editor, input browser and output preview."""
        super().__init__(parent)
        self._key = ""
        self._spec: dict = {"fields": (), "loops": ()}
        self._editable = True
        self._supported = True

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

        self.preview = DeckCodeEditor()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(170)
        root.addWidget(self.preview, 2)

        self.template.textChanged.connect(self._template_changed)
        self.enabled.toggled.connect(self._template_changed)
        self.float_format.currentTextChanged.connect(self._float_format_changed)
        self.fields.itemDoubleClicked.connect(
            lambda _item, _column: self.insert_selected_field()
        )

    def load_record(
        self,
        key: str,
        label_text: str,
        state: dict | None = None,
        *,
        supported: bool = True,
    ) -> None:
        """Load one explicit record spec and optional profile-local editor state."""
        self._key = key
        self._spec = template_spec(key, label_text)
        self._supported = bool(supported)
        state = dict(state or {})

        self.template.blockSignals(True)
        self.float_format.blockSignals(True)
        self.enabled.blockSignals(True)
        try:
            self.template.setPlainText(str(state.get("template", self._spec["template"])))
            self.float_format.setCurrentText(str(state.get("float_format", ".6g")))
            default_enabled = bool(state.get("enabled", self._spec.get("enabled", True)))
            self.enabled.setChecked(default_enabled and self._supported)
        finally:
            self.template.blockSignals(False)
            self.float_format.blockSignals(False)
            self.enabled.blockSignals(False)

        self._populate_fields()
        self._update_preview()
        self.set_editable(self._editable)

    def set_editable(self, editable: bool) -> None:
        """Toggle profile editing while keeping unsupported records viewable."""
        self._editable = bool(editable)
        can_edit_record = self._editable and self._supported
        for control in (
            self.enabled,
            self.float_format,
            self.template,
            self.insert_button,
        ):
            control.setEnabled(can_edit_record)

    def record_state(self) -> dict[str, object]:
        """Return the complete profile-local state for the current record."""
        return {
            "template": self.template.toPlainText(),
            "enabled": self.enabled.isChecked() and self._supported,
            "float_format": self.float_format.currentText() or ".6g",
        }

    def template_text(self) -> str:
        """Return the complete keyword-and-data template currently being edited."""
        return self.template.toPlainText()

    def available_field_names(self) -> tuple[str, ...]:
        """Return every record or loop-scoped placeholder name."""
        names = [
            name
            for name, _description, _example in tuple(self._spec.get("fields", ()))
        ]
        for loop_spec in self._spec.get("loops", ()):
            loop = loop_from_spec(loop_spec)
            names.extend(
                f"{loop.item}.{name}"
                for name, _description, _example in loop.fields
            )
        return tuple(names)

    def insert_field(self, name: str) -> None:
        """Insert one documented placeholder at the current template cursor."""
        if not self.template.isEnabled() or name not in self.available_field_names():
            return
        self._insert_text("{" + name + "}")

    def insert_selected_field(self) -> None:
        """Insert the selected placeholder or loop skeleton at the edit cursor."""
        item = self.fields.currentItem()
        if item is None or not self.template.isEnabled():
            return
        insertion = item.data(0, _INSERT_ROLE)
        if insertion:
            self._insert_text(str(insertion))

    def _insert_text(self, text: str) -> None:
        """Insert raw template syntax at the current cursor and retain focus."""
        cursor = self.template.textCursor()
        cursor.insertText(text)
        self.template.setTextCursor(cursor)
        self.template.setFocus()

    def _build_controls(self) -> QHBoxLayout:
        """Build canonical record-level controls."""
        controls = QHBoxLayout()
        enabled = create_editor(
            FieldSpec("enabled", "Enabled", kind="bool", default=True)
        )
        if not isinstance(enabled, QCheckBox):
            raise TypeError("Deck enabled control must use QCheckBox")
        self.enabled = enabled
        self.enabled.setText("Enabled")
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
            "Use {for item in collection} ... {endfor} to repeat deck lines. "
            "Placeholders may be used in keyword options or data lines.",
            role=LabelRole.MUTED,
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.template = DeckCodeEditor()
        layout.addWidget(self.template, 1)
        return panel

    def _build_fields_panel(self) -> QWidget:
        """Build the helper panel documenting fields and loop collections."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.addWidget(SectionHeading("Available Fields"))
        helper = label(
            "Loop rows show valid {for ...} syntax. Expand them to see the "
            "fields available inside that loop.",
            role=LabelRole.MUTED,
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)
        self.fields = QTreeWidget()
        self.fields.setHeaderLabels(
            ("Field / Syntax", "Meaning", "Scope", "Example")
        )
        self.fields.setRootIsDecorated(True)
        self.fields.setAlternatingRowColors(True)
        self.fields.setColumnWidth(0, 220)
        self.fields.setColumnWidth(1, 250)
        self.fields.setColumnWidth(2, 140)
        layout.addWidget(self.fields, 1)
        self.insert_button = apply_primary_control_height(
            button(ButtonSpec("Insert at Cursor"), clicked=self.insert_selected_field)
        )
        layout.addWidget(self.insert_button)
        return panel

    def _populate_fields(self) -> None:
        """Refresh input documentation using the selected float presentation."""
        self.fields.clear()
        preview_spec = formatted_spec(
            self._spec,
            self.float_format.currentText() or ".6g",
        )
        for name, description, example in tuple(preview_spec.get("fields", ())):
            display = "{" + name + "}"
            item = QTreeWidgetItem((display, description, "Record", str(example)))
            item.setData(0, _INSERT_ROLE, display)
            item.setData(0, _FIELD_NAME_ROLE, name)
            self.fields.addTopLevelItem(item)

        for loop_spec in preview_spec.get("loops", ()):
            loop = loop_from_spec(loop_spec)
            syntax = f"{{for {loop.item} in {loop.collection}}} … {{endfor}}"
            parent = QTreeWidgetItem(
                (
                    syntax,
                    loop.description,
                    "Loop",
                    f"{len(loop.examples)} representative items",
                )
            )
            parent.setData(0, _INSERT_ROLE, loop_skeleton(loop))
            for name, description, example in loop.fields:
                qualified = f"{loop.item}.{name}"
                display = "{" + qualified + "}"
                child = QTreeWidgetItem(
                    (
                        display,
                        description,
                        f"{loop.item} in {loop.collection}",
                        str(example),
                    )
                )
                child.setData(0, _INSERT_ROLE, display)
                child.setData(0, _FIELD_NAME_ROLE, qualified)
                parent.addChild(child)
            self.fields.addTopLevelItem(parent)
            parent.setExpanded(True)

        if self.fields.topLevelItemCount():
            self.fields.setCurrentItem(self.fields.topLevelItem(0))

    def _template_changed(self, *_args) -> None:
        """Refresh the preview and mark the current session record dirty."""
        self._update_preview()
        self.changed.emit()

    def _float_format_changed(self, *_args) -> None:
        """Apply float formatting to both helper examples and the live preview."""
        self._populate_fields()
        self._update_preview()
        self.changed.emit()

    def _update_preview(self) -> None:
        """Render a sample block without invoking a solver exporter."""
        text = render_preview(
            self.template.toPlainText(),
            self._spec,
            float_format=self.float_format.currentText() or ".6g",
        )
        if self._key.startswith("materials.") and self._key != "materials.header":
            text = "*MATERIAL, NAME=STEEL\n" + text
        self.preview.setPlainText(
            text if self.enabled.isChecked() else "<record disabled>"
        )
