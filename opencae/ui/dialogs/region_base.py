from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique
from opencae.ui.core.widgets import SelectionMembersWidget


class RegionDialog(QDialog):
    committed = pyqtSignal(object)

    def __init__(self, title, default_name, region=None, selection_provider=None, modes=(), existing_names=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._existing_names = tuple(existing_names)
        self._current_name = getattr(region, "name", "")
        self.setMinimumWidth(620)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("PanelTitle")
        root.addWidget(heading)
        form = QFormLayout()
        self.name = QLineEdit(getattr(region, "name", default_name))
        form.addRow("Name", self.name)
        self.selection_mode = QComboBox()
        self.selection_mode.addItems([label for label, _mode in modes])
        form.addRow("Selection", self.selection_mode)
        root.addLayout(form)
        root.addWidget(QLabel("Referenced geometry or mesh entities"))
        initial = getattr(region, "members", ())
        if region is None and selection_provider is not None:
            initial = selection_provider() or ()
        self.members_widget = SelectionMembersWidget(initial, selection_provider)
        root.addWidget(self.members_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        apply_button.setObjectName("PrimaryButton")
        apply_button.clicked.connect(self._commit)
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)
        self._modes = dict(modes)

    def mode(self):
        return self._modes.get(self.selection_mode.currentText(), "auto")

    def update_selection(self):
        self.members_widget.capture()

    def _commit(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Invalid region", "Enter a name.")
            return
        if not is_unique(self.name.text(), self._existing_names, self._current_name):
            QMessageBox.warning(self, "Duplicate name", f"A region named '{self.name.text().strip()}' already exists in this scope.")
            return
        if not self.members_widget.members():
            QMessageBox.warning(self, "Empty region", "Select at least one geometry or mesh entity.")
            return
        self.committed.emit(self.values())

    def values(self):
        return {"name": self.name.text().strip(), "members": self.members_widget.members()}
