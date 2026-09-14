from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from opencae.ui.primitives.buttons import ButtonPresentation, MenuButton


class UnitSystemStatus(MenuButton):
    system_selected = pyqtSignal(str)
    edit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            presentation=ButtonPresentation.DEFAULT,
            object_name="UnitSystemStatus",
            parent=parent,
        )

    def refresh(self, systems, selected):
        self.setText(f"Units: {selected or 'None'}")
        menu = QMenu(self)
        for system in systems:
            action = QAction(system.name, menu)
            action.setCheckable(True)
            action.setChecked(system.name == selected)
            action.triggered.connect(
                lambda checked=False, name=system.name: self.system_selected.emit(name)
            )
            menu.addAction(action)
        menu.addSeparator()
        edit = menu.addAction("Edit Unit Systems…")
        edit.triggered.connect(self.edit_requested.emit)
        self.setMenu(menu)
