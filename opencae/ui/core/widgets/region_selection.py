from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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
from .chevron_combo import ChevronComboBox


class RegionSelectionWidget(QWidget):
    """Edit a region definition without resolving it while the user picks.

    The table is the persistent dialog value.  Viewport picks are immutable
    operands, duplicate occurrences are removed by ``RegionDefinition``, and
    node/element/facet projection is deliberately deferred to deck generation.
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
        show_named_regions=True,
        show_pick_controls=True,
    ):
        super().__init__(parent)
        self.project = project
        self.pick_callback = pick_callback
        self.save_callback = save_callback
        self.requirement = requirement
        self.allow_part_local = bool(allow_part_local)
        self._definition = RegionDefinition.from_values(definition)
        self._cancel_pick = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
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
        self.table.setMinimumHeight(150)
        root.addWidget(self.table)

        self.add_row_widget = QWidget(self)
        add_row = QHBoxLayout(self.add_row_widget)
        add_row.setContentsMargins(0, 0, 0, 0)
        self.options = ChevronComboBox()
        self.options.setMinimumWidth(260)
        for label, value in options:
            self.options.addItem(str(label), value)
        self.add_button = QPushButton("Add region")
        self.add_button.clicked.connect(self._add_option)
        add_row.addWidget(self.options, 1)
        add_row.addWidget(self.add_button)
        root.addWidget(self.add_row_widget)

        buttons = QHBoxLayout()
        self.pick_button = QPushButton("Pick in View")
        self.pick_button.setCheckable(True)
        self.pick_button.setStyleSheet(
            "QPushButton:checked {"
            " background-color: #2f78b7; color: white;"
            " border: 2px solid #8bc8ff; font-weight: 600;"
            "}"
        )
        self.pick_button.toggled.connect(self._toggle_pick)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)
        buttons.addWidget(self.pick_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.clear_button)
        self.save_button = None
        if save_callback:
            self.save_button = QPushButton("Save as Region")
            self.save_button.clicked.connect(lambda: save_callback(self, self.definition()))
            buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self.summary = QLabel()
        root.addWidget(self.summary)
        self.set_named_region_controls_visible(show_named_regions)
        self.set_pick_controls_visible(show_pick_controls)
        self._refresh()

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
        self._refresh()

    def set_named_region_controls_visible(self, visible: bool):
        """Show reusable-region controls only where named regions are valid."""
        self.add_row_widget.setVisible(bool(visible))
        if self.save_button is not None:
            self.save_button.setVisible(bool(visible))

    def set_pick_controls_visible(self, visible: bool):
        """Show the detailed editor's viewport-pick button.

        Compact selectors own the primary pick button and use this editor only
        for operand inspection and named-region management.
        """
        self.pick_button.setVisible(bool(visible))

    def add_definition(self, value):
        definition = RegionDefinition.from_values(value)
        self._definition = RegionDefinition((*self._definition.items, *definition.items))
        self._refresh()
        self.value_changed.emit(self._definition)

    def add_item(self, value):
        item = value if isinstance(value, RegionSelectionItem) else RegionSelectionItem(value)
        self.add_definition(RegionDefinition((item,)))

    def apply_pick(self, value, operation=SelectionOperation.ADD):
        """Apply one viewport gesture; semantic projection remains deferred."""
        definition = RegionDefinition.from_values(value)
        operation = SelectionOperation(operation)
        if operation == SelectionOperation.REPLACE:
            self._definition = definition
        elif operation == SelectionOperation.REMOVE:
            remove = {item.key for item in definition.items}
            self._definition = RegionDefinition(tuple(item for item in self._definition.items if item.key not in remove))
        else:
            self._definition = RegionDefinition((*self._definition.items, *definition.items))
        self._refresh()
        self.value_changed.emit(self._definition)

    def clear(self):
        self._definition = RegionDefinition()
        self._refresh()
        self.value_changed.emit(self._definition)

    def finish_pick(self):
        if self.pick_button.isChecked():
            self.pick_button.setChecked(False)

    def _add_option(self):
        value = self.options.currentData()
        if value is not None:
            self.add_definition(value)

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
        cancel = self.pick_callback(self, self.apply_pick, self._session_finished)
        self._cancel_pick = cancel if callable(cancel) else None

    def _session_finished(self):
        """Synchronize the button when the global picker ends elsewhere."""
        self._cancel_pick = None
        if self.pick_button.isChecked():
            blocker = QSignalBlocker(self.pick_button)
            self.pick_button.setChecked(False)
            del blocker
        self._set_picking_visual(False)

    def _set_picking_visual(self, active: bool):
        self.pick_button.setText("Finish Picking" if active else "Pick in View")
        self.pick_button.setToolTip(
            "Click to finish the active viewport selection"
            if active else
            "Select this field in the viewport"
        )
        self.picking_changed.emit(bool(active))

    def _remove_selected(self):
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        if not rows:
            return
        self._definition = RegionDefinition(tuple(item for index, item in enumerate(self._definition.items) if index not in rows))
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
        count = len(self._definition.items)
        self.summary.setText(
            f"{count} region operand{'s' if count != 1 else ''}. "
            "Projection to nodes, elements or facets occurs during deck generation."
        )


def _position(value):
    if value is None:
        return "—"
    return "(" + ", ".join(f"{component:.6g}" for component in value) + ")"
