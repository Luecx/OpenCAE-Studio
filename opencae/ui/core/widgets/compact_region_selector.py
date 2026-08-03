from __future__ import annotations

from PyQt6.QtCore import QSize, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
from .region_selection import RegionSelectionWidget


_PICK_STYLE = (
    "QPushButton:checked {"
    " background-color: #2f78b7; color: white;"
    " border: 2px solid #8bc8ff; font-weight: 600;"
    "}"
)


class CompactRegionSelector(QWidget):
    """Small region field with a primary viewport action and optional details.

    The compact selector owns the persistent dialog value and the pick session.
    It never resolves geometry to nodes/elements/facets while the user picks.
    The extended window is merely an editor for the same RegionDefinition.
    """

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

        # The region value behaves like every other form field: it is readable
        # at a glance but cannot be edited as free text.  Viewport and extended
        # selection remain explicit actions on the right-hand side.
        self.summary = QLineEdit()
        self.summary.setObjectName("CompositeFieldEdit")
        self.summary.setReadOnly(True)
        self.summary.setMinimumWidth(0)
        self.summary.setToolTip("No target region selected")
        root.addWidget(self.summary, 1)

        self.pick_button = QPushButton()
        self.pick_button.setIcon(make_icon(IconKind.PICK, 18, PALETTE["text"]))
        self.pick_button.setIconSize(QSize(18, 18))
        self.pick_button.setObjectName("InlinePickButton")
        self.pick_button.setAccessibleName("Select in View")
        self.pick_button.setCheckable(True)
        self.pick_button.setFixedSize(30, 30)
        self.pick_button.setToolTip("Select this region in the viewport")
        self.pick_button.toggled.connect(self._toggle_pick)
        root.addWidget(self.pick_button)

        self.extended_button = QPushButton("…")
        self.extended_button.setObjectName("InlineAddButton")
        self.extended_button.setAccessibleName("Extended region selection")
        self.extended_button.setFixedSize(30, 30)
        self.extended_button.setToolTip("Open extended region selection")
        self.extended_button.clicked.connect(self.open_extended)
        self.extended_button.setVisible(bool(show_extended))
        root.addWidget(self.extended_button)

        self.setMinimumWidth(316)
        self._refresh_summary()

    def definition(self) -> RegionDefinition:
        return self._definition

    def currentValue(self):
        return self.definition()

    def set_definition(self, value):
        definition = RegionDefinition.from_values(value)
        if definition == self._definition:
            return
        self._definition = definition
        self._refresh_summary()
        self._sync_extended()
        self.value_changed.emit(self._definition)

    def set_requirement(self, requirement, *, allow_part_local=None):
        self.requirement = requirement
        if allow_part_local is not None:
            self.allow_part_local = bool(allow_part_local)
        if self._extended_dialog is not None:
            self._extended_dialog.editor.set_requirement(
                requirement, allow_part_local=self.allow_part_local
            )

    def set_extended_visible(self, visible: bool):
        self.extended_button.setVisible(bool(visible))
        if not visible and self._extended_dialog is not None:
            self._extended_dialog.close()

    # Compatibility with the previous detailed widget API.
    def set_named_region_controls_visible(self, visible: bool):
        self.set_extended_visible(visible)

    def add_definition(self, value):
        incoming = RegionDefinition.from_values(value)
        self.set_definition(RegionDefinition((*self._definition.items, *incoming.items)))

    def add_item(self, value):
        item = value if isinstance(value, RegionSelectionItem) else RegionSelectionItem(value)
        self.add_definition(RegionDefinition((item,)))

    def apply_pick(self, value, operation=SelectionOperation.ADD):
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

    def clear(self):
        self.set_definition(RegionDefinition())

    def finish_pick(self):
        if self.pick_button.isChecked():
            self.pick_button.setChecked(False)

    def open_extended(self):
        if self._extended_dialog is not None:
            activate_dialog(self._extended_dialog)
            return
        dialog = ExtendedRegionDialog(self)
        self._extended_dialog = dialog
        dialog.finished.connect(lambda _code: self._extended_closed(dialog))
        show_modeless_dialog(dialog)
        dialog.begin_selection()

    def _toggle_pick(self, active):
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

    def _session_finished(self):
        self._cancel_pick = None
        if self._extended_dialog is not None:
            self._extended_dialog.close()
        if self.pick_button.isChecked():
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker
        self._set_picking_visual(False)

    def _set_picking_visual(self, active: bool):
        # Keep the compact action icon stable; the checked state is the visual
        # indication that this field currently owns the global viewport picker.
        self.pick_button.setToolTip(
            "Finish selecting this region"
            if active else
            "Select this region in the viewport"
        )
        self.picking_changed.emit(bool(active))
        if self._extended_dialog is not None:
            self._extended_dialog.set_picking(active)

    def _refresh_summary(self):
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

    def _sync_extended(self):
        if self._extended_dialog is None or self._syncing:
            return
        self._syncing = True
        try:
            self._extended_dialog.editor.set_definition(self._definition)
        finally:
            self._syncing = False

    def _extended_value_changed(self, definition):
        if self._syncing:
            return
        self._syncing = True
        try:
            self._definition = RegionDefinition.from_values(definition)
            self._refresh_summary()
            self.value_changed.emit(self._definition)
        finally:
            self._syncing = False

    def _extended_closed(self, dialog):
        if self._extended_dialog is dialog:
            self._extended_dialog = None
        self.pick_button.setEnabled(True)
        self.finish_pick()

    def _dispose(self):
        self.finish_pick()
        if self._extended_dialog is not None:
            self._extended_dialog.close()
            self._extended_dialog = None


class ExtendedRegionDialog(QDialog):
    """Detailed operand editor for one CompactRegionSelector."""

    def __init__(self, selector: CompactRegionSelector):
        super().__init__(selector.window())
        self.selector = selector
        self.setWindowTitle(selector.extended_title)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(720, 430)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(9)
        self.editor = RegionSelectionWidget(
            selector.project,
            selector.definition(),
            selector.options,
            pick_callback=None,
            save_callback=selector.save_callback,
            parent=self,
            requirement=selector.requirement,
            allow_part_local=selector.allow_part_local,
            show_named_regions=True,
        )
        self.editor.value_changed.connect(selector._extended_value_changed)
        root.addWidget(self.editor, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close)
        row.addWidget(close)
        root.addLayout(row)

    def begin_selection(self):
        """Keep viewport selection active for the complete dialog lifetime."""
        if self.selector.pick_callback and not self.selector.pick_button.isChecked():
            self.selector.pick_button.setChecked(True)
        if self.selector.pick_callback:
            self.selector.pick_button.setEnabled(False)

    def set_picking(self, active: bool):
        # The extended editor intentionally has no start/finish control.  Its
        # lifetime is the selection session; closing it ends the session.
        return None


def _safe_label(project, item):
    try:
        return selection_item_label(project, item)
    except (AttributeError, KeyError, TypeError, ValueError):
        return item.display_label or selection_item_kind(item)


def _position(value):
    if value is None:
        return ""
    return "(" + ", ".join(f"{component:.6g}" for component in value) + ")"
