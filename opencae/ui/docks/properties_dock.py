from PyQt6.QtWidgets import QDockWidget

from opencae.ui.core.metrics import PROPERTIES_MIN_WIDTH
from opencae.ui.core.property_view import PropertyView


class PropertiesDock(QDockWidget):
    def __init__(self, store, parent=None):
        super().__init__("Properties", parent)
        self.setObjectName("PropertiesDock")
        self.view = PropertyView()
        self.setWidget(self.view)
        self.setMinimumWidth(PROPERTIES_MIN_WIDTH)
        store.selection_changed.connect(self.view.show_object)
