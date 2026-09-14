"""Provides the compact persistent region selector used by model entity dialogs."""

from __future__ import annotations

from PyQt6.QtCore import QSize, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.model.selection import (
    RegionDefinition,
    RegionSelectionItem,
    SelectionOperation,
    selection_item_kind,
    selection_item_label,
)
from opencae.ui.core.dialog_lifecycle import activate_dialog, show_modeless_dialog
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.core.theme import PALETTE
from opencae.ui.primitives.buttons import ButtonInlineAction, ButtonInlineToggle
from opencae.ui.primitives.inputs import InputFormText

from .extended_region_dialog import ExtendedRegionDialog


class CompactRegionSelector(QWidget):
    """Own one persistent region definition and its viewport-picking lifecycle."""

    value_changed = pyqtSignal(object)
    picking_changed = pyqtSignal(bool)

    def __init__(
        self,
        project,
        definition=None,
        options=(),
        pick_callback=None,
        save_callback=None,
        parent=None,
        *,
        requirement=None,
        allow_part_local=False,
        show_extended=True,
        extended_title="Extended region selection",
    ):
        """Build a compact read-only summary with same-height pick/detail actions."""
        super().__init__(parent)
        self.project = project
        self.options = tuple(options)
        self.pick_callback = pick_callback
        self.save_callback = save_callback
        self.requirement = requirement
        self.allow_part_local = bool(allow_part_local)
        self.extended_title = str(extended_title)
        self._definition = RegionDefinition.from_values(definition)
        self._cancel_pick = None
        self._extended_dialog: ExtendedRegionDialog | None = None
        self._syncing = False

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.summary = InputFormText(
            read_only=True,
            object_name="CompositeFieldEdit",
            parent=self,
        )
        self.summary.setToolTip("No target region selected")
        root.addWidget(self.summary, 1)

        self.pick_button = ButtonInlineToggle(
            icon=make_icon(IconKind.PICK, 18, PALETTE["text"]),
            tooltip="Select this region in the viewport",
            object_name="InlinePickButton",
            parent=self,
        )
        self.pick_button.setIconSize(QSize(18, 18))
        self.pick_button.setAccessibleName("Select in View")
        self.pick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_button.toggled.connect(self._toggle_pick)
        root.addWidget(self.pick_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.extended_button = ButtonInlineAction(
            "…",
            tooltip="Open extended region selection",
            object_name="InlineBrowseButton",
            parent=self,
        )
        self.extended_button.setAccessibleName("Extended region selection")
        self.extended_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.extended_button.clicked.connect(self.open_extended)
        self.extended_button.setVisible(bool(show_extended))
        root.addWidget(self.extended_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.setMinimumWidth(0)
        self._refresh_summary()

    def definition(self) -> RegionDefinition:
        """Return the currently selected unresolved region definition."""
        return self._definition

    def currentValue(self):
        """Compatibility alias returning the current region definition."""
        return self.definition()

    def set_definition(self, value) -> None:
        """Replace the region definition and synchronize all visible editors."""
        definition = RegionDefinition.from_values(value)
        if definition == self._definition:
            return
        self._definition = definition
        self._refresh_summary()
        self._sync_extended()
        self.value_changed.emit(self._definition)

    def set_requirement(self, requirement, *, allow_part_local=None) -> None:
        """Replace the semantic selection requirement for future viewport picks."""
        self.requirement = requirement
        if allow_part_local is not None:
            self.allow_part_local = bool(allow_part_local)
        if self._extended_dialog is not None:
            self._extended_dialog.editor.set_requirement(
                requirement,
                allow_part_local=self.allow_part_local,
            )

    def set_extended_visible(self, visible: bool) -> None:
        """Show or hide the detailed region-editor action."""
        self.extended_button.setVisible(bool(visible))
        if not visible and self._extended_dialog is not None:
            self._extended_dialog.close()

    def set_named_region_controls_visible(self, visible: bool) -> None:
        """Compatibility alias for controlling the detailed region editor."""
        self.set_extended_visible(visible)

    def add_definition(self, value) -> None:
        """Append incoming operands to the existing region definition."""
        incoming = RegionDefinition.from_values(value)
        self.set_definition(
            RegionDefinition((*self._definition.items, *incoming.items))
        )

    def add_item(self, value) -> None:
        """Append one selection operand to the current definition."""
        item = value if isinstance(value, RegionSelectionItem) else RegionSelectionItem(value)
        self.add_definition(RegionDefinition((item,)))

    def apply_pick(self, value, operation=SelectionOperation.ADD) -> None:
        """Apply a typed viewport selection operation to the persistent definition."""
        incoming = RegionDefinition.from_values(value)
        operation = SelectionOperation(operation)
        if operation == SelectionOperation.REPLACE:
            result = incoming
        elif operation == SelectionOperation.REMOVE:
            remove = {item.key for item in incoming.items}
            result = RegionDefinition(
                tuple(item for item in self._definition.items if item.key not in remove)
            )
        else:
            result = RegionDefinition((*self._definition.items, *incoming.items))
        self.set_definition(result)

    def clear(self) -> None:
        self.set_definition(RegionDefinition())

    def finish_pick(self) -> None:
        if self.pick_button.isChecked():
            self.pick_button.setChecked(False)

    def open_extended(self) -> None:
        if self._extended_dialog is not None:
            activate_dialog(self._extended_dialog)
            return
        dialog = ExtendedRegionDialog(self)
        self._extended_dialog = dialog
        dialog.finished.connect(lambda _code: self._extended_closed(dialog))
        show_modeless_dialog(dialog)
        dialog.begin_selection()

    def _toggle_pick(self, active) -> None:
        if not active:
            cancel = self._cancel_pick
            self._cancel_pick = None
            self._set_picking_visual(False)
            if cancel:
                cancel()
            return
        if not self.pick_callback:
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker
            self._set_picking_visual(False)
            return
        self._set_picking_visual(True)
        try:
            cancel = self.pick_callback(self, self.apply_pick, self._session_finished)
        except Exception:
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker
            self._set_picking_visual(False)
            raise
        self._cancel_pick = cancel if callable(cancel) else None

    def _session_finished(self) -> None:
        self._cancel_pick = None
        if self._extended_dialog is not None:
            self._extended_dialog.close()
        if self.pick_button.isChecked():
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker
        self._set_picking_visual(False)

    def _set_picking_visual(self, active: bool) -> None:
        self.pick_button.setToolTip(
            "Finish selecting this region" if active else "Select this region in the viewport"
        )
        self.picking_changed.emit(bool(active))
        if self._extended_dialog is not None:
            self._extended_dialog.set_picking(active)

    def _refresh_summary(self) -> None:
        count = len(self._definition.items)
        if count == 0:
            text = "Nothing selected"
            self.summary.setText(text)
            self.summary.setToolTip(text)
            return
        if count == 1:
            item = self._definition.items[0]
            label = _safe_label(self.project, item)
            kind = selection_item_kind(item)
            position = _position(item.picked_position)
            suffix = f" · {position}" if position else ""
            text = f"{kind}: {label}{suffix}"
            self.summary.setText(text)
            self.summary.setToolTip(text)
            self.summary.setCursorPosition(0)
            return
        text = f"{count} objects selected"
        self.summary.setText(text)
        self.summary.setToolTip(
            "; ".join(_safe_label(self.project, item) for item in self._definition.items)
        )
        self.summary.setCursorPosition(0)

    def _sync_extended(self) -> None:
        if self._extended_dialog is None or self._syncing:
            return
        self._syncing = True
        try:
            self._extended_dialog.editor.set_definition(self._definition)
        finally:
            self._syncing = False

    def _extended_value_changed(self, definition) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            self._definition = RegionDefinition.from_values(definition)
            self._refresh_summary()
            self.value_changed.emit(self._definition)
        finally:
            self._syncing = False

    def _extended_closed(self, dialog) -> None:
        if self._extended_dialog is dialog:
            self._extended_dialog = None
        self.pick_button.setEnabled(True)
        self.finish_pick()

    def _dispose(self) -> None:
        self.finish_pick()
        if self._extended_dialog is not None:
            self._extended_dialog.close()
            self._extended_dialog = None


def _safe_label(project, item) -> str:
    try:
        return selection_item_label(project, item)
    except (AttributeError, KeyError, TypeError, ValueError):
        return item.display_label or selection_item_kind(item)


def _position(value) -> str:
    if value is None:
        return ""
    return "(" + ", ".join(f"{component:.6g}" for component in value) + ")"
