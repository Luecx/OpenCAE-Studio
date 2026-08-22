from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from opencae.model.selection import RegionDefinition
from opencae.ui.core.widgets import CompactRegionSelector


class EdgeSeedDialog(QDialog):
    apply_requested = pyqtSignal(object)

    def __init__(
        self,
        project,
        options=(),
        definition=None,
        pick_callback=None,
        seed=None,
        parent=None,
        units=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Seed Edges")
        self.setModal(False)
        self.setMinimumWidth(680)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        title = QLabel("Seed Edges")
        title.setObjectName("PanelTitle")
        root.addWidget(title)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.name = QLineEdit(seed.name if seed else "Edge Seed")
        self.target = CompactRegionSelector(
            project,
            definition or getattr(seed, "target", RegionDefinition()),
            options,
            pick_callback,
            parent=self,
        )
        self.method = QComboBox()
        self.method.addItems(("Size", "Number of divisions"))
        self.method.setCurrentText(seed.method if seed else "Number of divisions")

        self.size = QDoubleSpinBox()
        self.size.setRange(1e-12, 1e30)
        self.size.setDecimals(9)
        self.size.setSuffix(units.suffix("length") if units is not None else "")
        self.size.setValue(seed.size if seed else 1.0)

        self.divisions = QSpinBox()
        self.divisions.setRange(1, 1_000_000)
        self.divisions.setValue(seed.divisions if seed and seed.divisions else 10)

        self.size_label = QLabel("Approximate size")
        self.divisions_label = QLabel("Number of divisions")
        form.addRow("Name", self.name)
        form.addRow("Edges", self.target)
        form.addRow("Method", self.method)
        form.addRow(self.size_label, self.size)
        form.addRow(self.divisions_label, self.divisions)
        root.addLayout(form)

        self.method.currentTextChanged.connect(self._sync_method_fields)
        self._sync_method_fields(self.method.currentText())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            lambda: self.apply_requested.emit(self.values())
        )
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def _sync_method_fields(self, method):
        use_size = str(method) == "Size"
        self.size_label.setVisible(use_size)
        self.size.setVisible(use_size)
        self.divisions_label.setVisible(not use_size)
        self.divisions.setVisible(not use_size)

    def values(self):
        return {
            "name": self.name.text().strip(),
            "target": self.target.definition(),
            "method": self.method.currentText(),
            "size": self.size.value(),
            "divisions": self.divisions.value(),
        }

    def set_selected_definition(self, definition):
        self.target.set_definition(definition)

    def set_selected_edges(self, definition):
        self.set_selected_definition(definition)

    def set_divisions(self, value: int):
        self.method.setCurrentText("Number of divisions")
        self.divisions.setValue(max(1, int(value)))
