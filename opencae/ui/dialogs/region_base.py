from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout

from opencae.model.naming import is_unique, next_name_from_names
from opencae.model.selection import RegionDefinition
from opencae.ui.core.widgets import RegionSelectionWidget


class RegionDialog(QDialog):
    committed = pyqtSignal(object)

    def __init__(
        self,
        title,
        default_name,
        region=None,
        *,
        project,
        options=(),
        pick_callback=None,
        existing_names=(),
        validator=None,
        requirement=None,
        allow_part_local=False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._existing_names = tuple(existing_names)
        self._current_name = getattr(region, "name", "")
        self._is_edit = region is not None
        self._default_prefix = _prefix(default_name)
        self._validator = validator
        self.setMinimumWidth(760)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        heading = QLabel(title); heading.setObjectName("PanelTitle"); root.addWidget(heading)
        form = QFormLayout()
        self.name = QLineEdit(getattr(region, "name", default_name)); form.addRow("Name", self.name)
        root.addLayout(form)
        root.addWidget(QLabel("Region operands"))
        self.region = RegionSelectionWidget(
            project,
            getattr(region, "definition", RegionDefinition()),
            options,
            pick_callback=pick_callback,
            parent=self,
            requirement=requirement,
            allow_part_local=allow_part_local,
        )
        root.addWidget(self.region)
        self.finished.connect(lambda _code: self.region.finish_selection())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(lambda: self._commit(True))
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(lambda: self._commit(False))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)


    def begin_selection(self):
        self.region.begin_selection()

    def values(self):
        return {"name": self.name.text().strip(), "definition": self.region.definition()}

    def _commit(self, close_after):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid region", "Enter a name."); return
        if not is_unique(name, self._existing_names, self._current_name):
            QMessageBox.warning(self, "Duplicate name", f"A region named '{name}' already exists in this scope."); return
        definition = self.region.definition()
        if definition.empty:
            QMessageBox.warning(self, "Empty region", "Add at least one geometry, mesh, reference-point, or named-region operand."); return
        if self._validator:
            error = self._validator(definition)
            if error:
                QMessageBox.warning(self, "Invalid region", error); return
        self.committed.emit(self.values())
        if close_after:
            self.accept(); return
        if not self._is_edit:
            self._existing_names = (*self._existing_names, name)
            self.name.setText(next_name_from_names(self._default_prefix, self._existing_names))
            self.region.clear()


def _prefix(default_name):
    text = str(default_name or "REGION").strip()
    head, sep, tail = text.rpartition("-")
    return head if sep and tail.isdigit() and head else text
