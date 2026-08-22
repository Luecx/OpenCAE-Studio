from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
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
        self.options.setMinimumWidth(250)
        self._reload_options()
        self.add_button = QPushButton("Add region")
        self.add_button.clicked.connect(self._add_option)
        row.addWidget(self.options, 1)
        row.addWidget(self.add_button)
        self.save_button = None
        if save_callback:
            self.save_button = QPushButton("Save as region")
            self.save_button.clicked.connect(lambda: save_callback(self, self.definition()))
            row.addWidget(self.save_button)
        row.addSpacing(18)
        row.addStretch(1)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)
        row.addWidget(self.remove_button)
        row.addWidget(self.clear_button)
        root.addWidget(self.action_row)

        self.set_named_region_controls_visible(show_named_regions)
        self._refresh()
        # Do not call instance methods from QObject.destroyed.  At that point
        # the C++ QWidget has already been destroyed and emitting Qt signals
        # from finish_selection() raises "wrapped C/C++ object ... deleted".
        # Dialog owners end active selection sessions from their finished
        # signal, before their child widgets are destroyed.

    def definition(self) -> RegionDefinition:
        return self._definition

    def currentValue(self):
        return self.definition()

    def set_definition(self, value):
        self._definition = RegionDefinition.from_values(value)
        self._refresh()
        self.value_changed.emit(self._definition)

    def set_requirement(self, requirement, *, allow_part_local=None):
        self.requirement = requirement
        if allow_part_local is not None:
            self.allow_part_local = bool(allow_part_local)
        self._reload_options()
        self._refresh()

    def set_named_region_controls_visible(self, visible: bool):
        self.options.setVisible(bool(visible))
        self.add_button.setVisible(bool(visible))
        if self.save_button is not None:
            self.save_button.setVisible(bool(visible))

    def begin_selection(self):
        if self._cancel_pick is not None or self.pick_callback is None:
            return
        cancel = self.pick_callback(self, self.apply_pick, self._session_finished)
        self._cancel_pick = cancel if callable(cancel) else None
        self.picking_changed.emit(True)

    def finish_selection(self):
        cancel = self._cancel_pick
        self._cancel_pick = None
        if cancel:
            cancel()
        self.picking_changed.emit(False)

    def _session_finished(self):
        self._cancel_pick = None
        self.picking_changed.emit(False)

    def _reload_options(self):
        self.options.clear()
        for label, value in self._all_options:
            if _option_matches_requirement(self.project, value, self.requirement):
                self.options.addItem(str(label), value)
        available = self.options.count() > 0
        self.options.setEnabled(available)
        if hasattr(self, "add_button"):
            self.add_button.setEnabled(available)

    def add_definition(self, value):
        definition = RegionDefinition.from_values(value)
        self._definition = RegionDefinition((*self._definition.items, *definition.items))
        self._refresh()
        self.value_changed.emit(self._definition)

    def add_item(self, value):
        item = value if isinstance(value, RegionSelectionItem) else RegionSelectionItem(value)
        self.add_definition(RegionDefinition((item,)))

    def apply_pick(self, value, operation=SelectionOperation.ADD):
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
        self._definition = RegionDefinition()
        self._refresh()
        self.value_changed.emit(self._definition)

    def _add_option(self):
        value = self.options.currentData()
        if value is not None:
            self.add_definition(value)

    def _remove_selected(self):
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        if not rows:
            return
        self._definition = RegionDefinition(
            tuple(item for index, item in enumerate(self._definition.items) if index not in rows)
        )
        self._refresh()
        self.value_changed.emit(self._definition)

    def _refresh(self):
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
    if value is None:
        return "—"
    return "(" + ", ".join(f"{component:.6g}" for component in value) + ")"


def _option_matches_requirement(project, value, requirement):
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
