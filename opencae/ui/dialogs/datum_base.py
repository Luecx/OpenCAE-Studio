from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
)

from opencae.model.naming import is_unique
from opencae.ui.core.widgets.pick_reference import PickReference


class DatumDialogBase(QDialog):
    apply_requested = pyqtSignal(object)
    preview_requested = pyqtSignal(object)
    reference_preview_requested = pyqtSignal(object)
    pick_requested = pyqtSignal(object, object, object)
    cancel_pick_requested = pyqtSignal()

    def __init__(self, title, methods, default_name, existing_names, parent=None):
        super().__init__(parent)
        self.existing_names = tuple(existing_names)
        self.setWindowTitle(title)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("PanelTitle")
        layout.addWidget(heading)
        form = QFormLayout()
        self.name = QLineEdit(default_name)
        self.method = QComboBox()
        self.method.addItems(methods)
        form.addRow("Name", self.name)
        form.addRow("Method", self.method)
        layout.addLayout(form)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.close)
        layout.addWidget(buttons)
        self.method.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.method.currentIndexChanged.connect(self._cancel_reference_picks)
        self.method.currentIndexChanged.connect(self.emit_preview)
        self.method.currentIndexChanged.connect(self.emit_reference_preview)
        self.name.textChanged.connect(self.emit_preview)

    def add_page(self, page):
        self.stack.addWidget(page)
        for child in page.findChildren(QComboBox):
            child.currentIndexChanged.connect(self.emit_preview)
        for child in page.findChildren(QLineEdit):
            child.textChanged.connect(self.emit_preview)
        for child in page.findChildren(QAbstractSpinBox):
            child.editingFinished.connect(self.emit_preview)
        for child in page.findChildren(PickReference):
            child.pick_requested.connect(self.pick_requested)
            child.cancel_requested.connect(self.cancel_pick_requested)
            child.changed.connect(self._reference_changed)

    def _reference_changed(self, *_):
        self.emit_preview()
        self.emit_reference_preview()

    def selected_references(self):
        page = self.stack.currentWidget()
        if page is None:
            return ()
        result = []
        for child in page.findChildren(PickReference):
            reference = child.reference()
            if reference:
                result.append(reference)
        return tuple(result)

    def emit_reference_preview(self, *_):
        self.reference_preview_requested.emit(self.selected_references())

    def _cancel_reference_picks(self, *_):
        for child in self.findChildren(PickReference):
            child._pick_finished()
        self.cancel_pick_requested.emit()

    def values(self):
        raise NotImplementedError

    def emit_preview(self, *_):
        try:
            self.preview_requested.emit(self.values())
        except (KeyError, TypeError, ValueError):
            return

    def _apply(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a datum name.")
            return
        if not is_unique(name, self.existing_names):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A datum named '{name}' already exists.",
            )
            return
        try:
            values = self.values()
        except Exception as exc:
            QMessageBox.warning(self, "Incomplete definition", str(exc))
            return
        self.apply_requested.emit(values)
