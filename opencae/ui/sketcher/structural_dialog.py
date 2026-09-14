"""Structurally composed public Sketcher dialog.

The behavior-heavy constraint dialog remains the owner of sketch/domain logic.
This final UI specialization replaces its construction hooks with canonical
primitives and composites while preserving the exact existing object names,
layout metrics, signals and public control attributes.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.composites.controls.control_sketch_commit_buttons import (
    ControlSketchCommitButtons,
)
from opencae.ui.composites.panels import PanelSketchInspector
from opencae.ui.core.metrics import VIEWPORT_TOOL_HEIGHT
from opencae.ui.primitives.buttons.button_viewport_action import ButtonViewportAction
from opencae.ui.primitives.buttons.button_viewport_toggle import ButtonViewportToggle
from opencae.ui.primitives.labels.label_sketch_hint import LabelSketchHint
from opencae.ui.primitives.labels.label_sketch_status import LabelSketchStatus
from opencae.ui.viewport.selection_toolbar import SelectionToolbar

from .constraint_dialog import SketchFeatureDialog as _BehaviorSketchFeatureDialog


_VIEWPORT_BAR_HEIGHT = VIEWPORT_TOOL_HEIGHT + 10


class SketchFeatureDialog(_BehaviorSketchFeatureDialog):
    """Public Sketcher assembled from the central primitive/composite library."""

    def _build_inspector(self, parent):
        panel = PanelSketchInspector(self.canvas.sketch, parent)
        panel.expose_on(self)
        self.sketch_inspector = panel
        return panel

    def _build_workspace(self, parent):
        """Build the existing canonical viewport bar from structural primitives."""
        host = QWidget(parent)
        host.setObjectName("SketchViewportHost")
        host.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.viewport_toolbar = SelectionToolbar(host)
        self.viewport_toolbar.setObjectName("ViewportToolbar")
        row = self.viewport_toolbar.layout()

        while row.count():
            item = row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)

        self.view_sketch = ButtonViewportToggle(
            "Sketch", checked=True, parent=self.viewport_toolbar
        )
        self.view_preview = ButtonViewportToggle(
            "3D Preview", parent=self.viewport_toolbar
        )
        self.view_group = QButtonGroup(self.viewport_toolbar)
        self.view_group.setExclusive(True)
        self.view_group.addButton(self.view_sketch)
        self.view_group.addButton(self.view_preview)
        row.addWidget(self.view_sketch)
        row.addWidget(self.view_preview)

        self.fit_button = ButtonViewportAction(
            "Fit",
            tooltip="Center and fit the sketch",
            parent=self.viewport_toolbar,
        )
        row.addWidget(self.fit_button)
        row.addSpacing(8)

        self.status_label = LabelSketchStatus("Ready", self.viewport_toolbar)
        self.hint_label = LabelSketchHint("", self.viewport_toolbar)
        row.addWidget(self.status_label)
        row.addWidget(self.hint_label)
        row.addStretch(1)

        self.buttons = ControlSketchCommitButtons(
            create_mode=self.windowTitle().startswith("Create"),
            parent=self.viewport_toolbar,
        )
        row.addWidget(self.buttons)

        self.viewport_toolbar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.viewport_toolbar.setFixedHeight(_VIEWPORT_BAR_HEIGHT)
        layout.addWidget(self.viewport_toolbar, 0)

        self.workspace = QStackedWidget(host)
        self.workspace.setObjectName("SketchViewportStack")
        self.workspace.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.workspace.addWidget(self.canvas)
        self.workspace.addWidget(self.preview)
        layout.addWidget(self.workspace, 1)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        return host
