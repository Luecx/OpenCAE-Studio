"""Provides the persistent region-operand editor used across modelling dialogs."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.model.selection import (
    NamedRegionOperand,
    ReferencePointOperand,
    RegionDefinition,
    RegionProjection,
    RegionSelectionItem,
    SelectionOperation,
    selection_item_kind,
    selection_item_label,
)
from opencae.ui.templates import PRIMARY_CONTROL_HEIGHT, button

from .chevron_combo import ChevronComboBox


class RegionSelectionWidget(QWidget):
    """Persistent region operand editor with a lifetime-owned pick session."""

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
        show_named_regions=True,
    ):
        """Build the operand table and region-management actions."""
        super().__init__(parent)
        self.project = project
        self.pick_callback = pick_callback
        self.save_callback = save_callback
        self.requirement = requirement
        self.allow_part_local = bool(allow_part_local)
        self._definition = RegionDefinition.from_values(definition)
        self._cancel_pick = None
        self._all_options = tuple(options)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(("Type", "Reference", "Picked position"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(170)
        root.addWidget(self.table)

        self.action_row = QWidget(self)
        row = QHBoxLayout(self.action_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.options = ChevronComboBox()
        self.options.setMinimumWidth(0)
        self._reload_options()

        self.add_button = button("Add region", clicked=self._add_option)
        self.add_button.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        row.addWidget(self.options, 1)
        row.addWidget(self.add_button)

        self.save_button = None
        if save_callback:
            self.save_button = button(
                "Save as region",
                clicked=lambda: save_callback(self, self.definition()),
            )
            self.save_button.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
            row.addWidget(self.save_button)

        row.addSpacing(12)
        row.addStretch(1)
        self.remove_button = button("Remove", clicked=self._remove_selected)
        self.clear_button = button("Clear", clicked=self.clear)
        self.remove_button.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        self.clear_button.setFixedHeight(PRIMARY_CONTROL_HEIGHT)
        row.addWidget(self.remove_button)
        row.addWidget(self.clear_button)
        root.addWidget(self.action_row)

        self.set_named_region_controls_visible(show_named_regions)
        self._refresh()
        # Do not call instance methods from QObject.destroyed. At that point the
        # C++ widget is already gone; dialog owners end selection from finished.

    def definition(self) -> RegionDefinition:
        """Return the current immutable region definition."""
        return self._definition

    def currentValue(self):
        """Expose the definition through the value-style selector API."""
        return self.definition()

    def set_definition(self, value):
        """Replace the complete definition and notify dependent editors."""
        self._definition = RegionDefinition.from_values(value)
        self._refresh()
        self.value_changed.emit(self._definition)

    def set_requirement(self, requirement, *, allow_part_local=None):
        """Change target compatibility constraints and refresh named options."""
        self.requirement = requirement
        if allow_part_local is not None:
            self.allow_part_local = bool(allow_part_local)
        self._reload_options()
        self._refresh()

    def set_named_region_controls_visible(self, visible: bool):
        """Show or hide the named-region add/save controls as one group."""
        self.options.setVisible(bool(visible))
        self.add_button.setVisible(bool(visible))
        if self.save_button is not None:
            self.save_button.setVisible(bool(visible))

    def begin_selection(self):
        """Start one lifetime-owned viewport pick session if available."""
        if self._cancel_pick is not None or self.pick_callback is None:
            return
        cancel = self.pick_callback(self, self.apply_pick, self._session_finished)
        self._cancel_pick = cancel if callable(cancel) else None
        self.picking_changed.emit(True)

    def finish_selection(self):
        """End the active viewport session and restore non-picking state."""
        cancel = self._cancel_pick
        self._cancel_pick = None
        if cancel:
            cancel()
        self.picking_changed.emit(False)

    def _session_finished(self):
        """Handle completion initiated by the viewport selection controller."""
        self._cancel_pick = None
        self.picking_changed.emit(False)

    def _reload_options(self):
        """Rebuild named region options allowed by the active requirement."""
        self.options.clear()
        for label, value in self._all_options:
            if _option_matches_requirement(self.project, value, self.requirement):
                self.options.addItem(str(label), value)
        available = self.options.count() > 0
        self.options.setEnabled(available)
        if hasattr(self, "add_button"):
            self.add_button.setEnabled(available)

    def add_definition(self, value):
        """Append all operands from another region definition."""
        definition = RegionDefinition.from_values(value)
        self._definition = RegionDefinition((*self._definition.items, *definition.items))
        self._refresh()
        self.value_changed.emit(self._definition)

    def add_item(self, value):
        """Append one selection item or raw operand to the region."""
        item = value if isinstance(value, RegionSelectionItem) else RegionSelectionItem(value)
        self.add_definition(RegionDefinition((item,)))

    def apply_pick(self, value, operation=SelectionOperation.ADD):
        """Apply an add, remove or replacement pick result to the current definition."""
        definition = RegionDefinition.from_values(value)
        operation = SelectionOperation(operation)
        if operation == SelectionOperation.REPLACE:
            self._definition = definition
        elif operation == SelectionOperation.REMOVE:
            remove = {item.key for item in definition.items}
            self._definition = RegionDefinition(
                tuple(item for item in self._definition.items if item.key not in remove)
            )
        else:
            self._definition = RegionDefinition((*self._definition.items, *definition.items))
        self._refresh()
        self.value_changed.emit(self._definition)

    def clear(self):
        """Remove every operand from the current definition."""
        self._definition = RegionDefinition()
        self._refresh()
        self.value_changed.emit(self._definition)

    def _add_option(self):
        """Append the named-region option currently selected in the combo box."""
        value = self.options.currentData()
        if value is not None:
            self.add_definition(value)

    def _remove_selected(self):
        """Remove all operand rows selected in the table."""
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        if not rows:
            return
        self._definition = RegionDefinition(
            tuple(item for index, item in enumerate(self._definition.items) if index not in rows)
        )
        self._refresh()
        self.value_changed.emit(self._definition)

    def _refresh(self):
        """Render the current immutable definition into the read-only operand table."""
        self.table.setRowCount(len(self._definition.items))
        for row, item in enumerate(self._definition.items):
            values = (
                selection_item_kind(item),
                selection_item_label(self.project, item),
                _position(item.picked_position),
            )
            for column, text in enumerate(values):
                cell = QTableWidgetItem(text)
                cell.setData(Qt.ItemDataRole.UserRole, item.key)
                self.table.setItem(row, column, cell)


def _position(value):
    """Format an optional picked world position for the operand table."""
    if value is None:
        return "—"
    return "(" + ", ".join(f"{component:.6g}" for component in value) + ")"


def _option_matches_requirement(project, value, requirement):
    """Return whether a named-region option satisfies the requested projection."""
    if requirement is None:
        return True
    projection = requirement.projection
    for item in RegionDefinition.from_values(value).items:
        operand = item.operand
        if isinstance(operand, NamedRegionOperand):
            region = project.try_resolve(operand.region_ref)
            if region is None or region.preferred_projection != projection:
                return False
        elif isinstance(operand, ReferencePointOperand):
            if projection not in {
                RegionProjection.NODES,
                RegionProjection.SINGLE_CONTROL_NODE,
            }:
                return False
    return True
