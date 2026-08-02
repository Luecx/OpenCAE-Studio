from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique, next_name_from_names
from opencae.ui.core.widgets import SelectionMembersWidget


class RegionDialog(QDialog):
    committed = pyqtSignal(object)

    def __init__(self, title, default_name, region=None, selection_provider=None, modes=(), existing_names=(), parent=None, member_formatter=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._existing_names = tuple(existing_names)
        self._current_name = getattr(region, "name", "")
        self._is_edit = region is not None
        self._default_prefix = _prefix(default_name)
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
        self.selection_mode = None
        if modes:
            self.selection_mode = QComboBox()
            self.selection_mode.addItems([label for label, _mode in modes])
            form.addRow("Selection", self.selection_mode)
        root.addLayout(form)
        root.addWidget(QLabel("Referenced geometry or mesh entities"))
        initial = getattr(region, "members", ())
        if region is None and selection_provider is not None:
            initial = selection_provider() or ()
        self.members_widget = SelectionMembersWidget(initial, selection_provider, member_formatter)
        root.addWidget(self.members_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setObjectName("PrimaryButton")
        ok_button.clicked.connect(lambda: self._commit(close_after=True))
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        apply_button.clicked.connect(lambda: self._commit(close_after=False))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)
        self._modes = dict(modes)

    def mode(self):
        if self.selection_mode is None:
            return "auto"
        return self._modes.get(self.selection_mode.currentText(), "auto")

    def update_selection(self):
        self.members_widget.capture()

    def _commit(self, close_after=False):
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
        if close_after:
            self.accept()
            return
        self._after_apply()

    def values(self):
        return {"name": self.name.text().strip(), "members": self.members_widget.members()}

    def _after_apply(self):
        if self._is_edit:
            return
        name = self.name.text().strip()
        self._existing_names = tuple((*self._existing_names, name))
        self.name.setText(next_name_from_names(self._default_prefix, self._existing_names))
        self.members_widget.set_members(())


def _prefix(default_name):
    text = str(default_name or "Region").strip()
    head, sep, tail = text.rpartition("-")
    return head if sep and tail.isdigit() and head else text
