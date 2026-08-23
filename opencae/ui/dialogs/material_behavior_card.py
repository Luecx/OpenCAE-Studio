"""Provides one collapsible inline editor card for a material behavior category."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .material_behavior_specs import (
    CATEGORY_ICONS,
    CATEGORY_TYPES,
    PROPERTY_SPECS,
    TYPE_LABELS,
    behavior_type,
    behavior_values,
    create_behavior,
    default_values,
)


class MaterialBehaviorCard(QFrame):
    """Edit one optional material behavior directly inside MaterialDialog.

    Undefined categories stay compact. Defining a category expands the card and
    exposes its model plus property fields, keeping closely related values on the
    same horizontal row.
    """

    def __init__(self, category: str, behavior=None, units=None, parent=None):
        super().__init__(parent)
        self.category = category
        self.units = units
        self._defined = False
        self._expanded = False
        self._current_kind = CATEGORY_TYPES[category][0]
        self._values_by_kind: dict[str, dict[str, float]] = {}
        self._editors: dict[str, QDoubleSpinBox] = {}

        self.setObjectName("MaterialBehaviorCard")
        self.setProperty("defined", False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        self.body = QWidget()
        self.body.setObjectName("MaterialBehaviorBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(18, 10, 18, 18)
        self.body_layout.setSpacing(14)
        root.addWidget(self.body)

        self.set_behavior(behavior)

    def _build_header(self) -> QWidget:
        """Build the card header with category, state and compact actions."""
        header = QWidget()
        header.setObjectName("MaterialBehaviorHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(10)

        icon = QLabel(CATEGORY_ICONS[self.category])
        icon.setObjectName("MaterialBehaviorIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel(self.category)
        title.setObjectName("MaterialBehaviorTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self.status = QLabel("Not defined")
        self.status.setObjectName("MaterialBehaviorStatus")
        self.status.setProperty("defined", False)
        layout.addWidget(self.status)

        self.action = QToolButton()
        self.action.setObjectName("MaterialBehaviorAction")
        self.action.clicked.connect(self._toggle_defined)
        layout.addWidget(self.action)

        self.chevron = QToolButton()
        self.chevron.setObjectName("MaterialBehaviorChevron")
        self.chevron.clicked.connect(self._toggle_expanded)
        layout.addWidget(self.chevron)
        return header

    def set_behavior(self, behavior) -> None:
        """Load an existing behavior or reset this category to undefined."""
        self._values_by_kind.clear()
        kind = behavior_type(behavior)
        if kind in CATEGORY_TYPES[self.category]:
            self._current_kind = kind
            self._values_by_kind[kind] = behavior_values(behavior)
            self._defined = True
            self._expanded = True
        else:
            self._current_kind = CATEGORY_TYPES[self.category][0]
            self._values_by_kind[self._current_kind] = default_values(self._current_kind)
            self._defined = False
            self._expanded = False
        self._rebuild_body()
        self._sync_state()

    def behavior_value(self):
        """Return the edited domain behavior, or None when the category is absent."""
        if not self._defined:
            return None
        self._capture_values()
        return create_behavior(self._current_kind, self._values_by_kind[self._current_kind])

    def _toggle_defined(self) -> None:
        """Define an absent category or remove the currently defined behavior."""
        if self._defined:
            self._capture_values()
            self._defined = False
            self._expanded = False
        else:
            self._defined = True
            self._expanded = True
            self._values_by_kind.setdefault(
                self._current_kind,
                default_values(self._current_kind),
            )
        self._sync_state()

    def _toggle_expanded(self) -> None:
        """Expand or collapse a defined card without changing its material data."""
        if not self._defined:
            return
        self._expanded = not self._expanded
        self._sync_state()

    def _rebuild_body(self) -> None:
        """Rebuild model/property controls for the active behavior type."""
        self._clear_body()

        model_block = QWidget()
        model_layout = QVBoxLayout(model_block)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(5)
        model_label = QLabel("Model")
        model_label.setObjectName("MaterialFieldLabel")
        model_layout.addWidget(model_label)

        self.kind = QComboBox()
        self.kind.setObjectName("MaterialModelCombo")
        for kind in CATEGORY_TYPES[self.category]:
            self.kind.addItem(TYPE_LABELS[kind], kind)
        index = self.kind.findData(self._current_kind)
        self.kind.setCurrentIndex(max(index, 0))
        self.kind.currentIndexChanged.connect(self._kind_changed)
        model_layout.addWidget(self.kind)
        self.body_layout.addWidget(model_block)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        self._editors = {}

        specs = PROPERTY_SPECS[self._current_kind]
        values = self._values_by_kind.setdefault(
            self._current_kind,
            default_values(self._current_kind),
        )
        for position, (key, label_text, default, quantity) in enumerate(specs):
            field = QWidget()
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(5)

            label = QLabel(label_text)
            label.setObjectName("MaterialFieldLabel")
            field_layout.addWidget(label)

            editor = QDoubleSpinBox()
            editor.setObjectName("MaterialPropertySpin")
            editor.setRange(-1e30, 1e30)
            editor.setDecimals(8)
            editor.setValue(values.get(key, default))
            if quantity and self.units is not None:
                editor.setSuffix(self.units.suffix(quantity))
            field_layout.addWidget(editor)
            self._editors[key] = editor

            # Two related properties share a row; a single property gets the
            # full card width rather than leaving a visually empty half-column.
            if len(specs) == 1:
                grid.addWidget(field, 0, 0, 1, 2)
            else:
                grid.addWidget(field, position // 2, position % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.body_layout.addLayout(grid)

    def _kind_changed(self) -> None:
        """Preserve per-model values while switching the behavior model."""
        self._capture_values()
        kind = self.kind.currentData()
        if not kind or kind == self._current_kind:
            return
        self._current_kind = str(kind)
        self._values_by_kind.setdefault(
            self._current_kind,
            default_values(self._current_kind),
        )
        self._rebuild_body()

    def _capture_values(self) -> None:
        """Store current editor values before rebuilding or returning the model."""
        if not self._editors:
            return
        self._values_by_kind[self._current_kind] = {
            key: editor.value() for key, editor in self._editors.items()
        }

    def _clear_body(self) -> None:
        """Delete the current body controls before changing the behavior model."""
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._delete_layout(item.layout())

    def _delete_layout(self, layout) -> None:
        """Recursively dispose widgets owned by a temporary child layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                self._delete_layout(item.layout())

    def _sync_state(self) -> None:
        """Synchronize visibility, labels and stylesheet properties with state."""
        self.setProperty("defined", self._defined)
        self.status.setProperty("defined", self._defined)
        self.status.setText("Defined" if self._defined else "Not defined")
        self.action.setText("−" if self._defined else "+")
        self.action.setToolTip(
            f"Remove {self.category}" if self._defined else f"Define {self.category}"
        )
        self.chevron.setEnabled(self._defined)
        self.chevron.setText("⌃" if self._expanded else "⌄")
        self.body.setVisible(self._defined and self._expanded)

        # Dynamic Qt properties affect QSS selectors only after repolishing.
        for widget in (self, self.status):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
