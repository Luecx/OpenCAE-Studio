"""Build one ribbon action group with a compact shared group title."""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from opencae.ui.composites import CollapsedActionGroupButton
from opencae.ui.core.theme import PALETTE
from opencae.ui.primitives.buttons.ribbon_action_factory import ribbon_button_for_action
from opencae.ui.primitives.labels import LabelRibbonGroup


class RibbonGroup(QFrame):
    """Arrange ribbon buttons above one compact semantic group caption."""

    def __init__(self, spec, actions, parent=None):
        """Build one expanded or collapsed ribbon action group."""
        super().__init__(parent)
        self.setObjectName("RibbonGroup")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._title = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 9, 0)
        layout.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)

        if spec.collapsed:
            icon_action_id = spec.icon_action_id or spec.action_ids[0]
            row.addWidget(
                CollapsedActionGroupButton(
                    spec.title.title(),
                    actions.get(icon_action_id),
                    tuple(actions.get(action_id) for action_id in spec.action_ids),
                    parent=self,
                )
            )
        else:
            for action_id in spec.action_ids:
                row.addWidget(
                    ribbon_button_for_action(actions.get(action_id), parent=self)
                )

        layout.addLayout(row)

        if spec.collapsed:
            layout.addSpacing(13)
        else:
            self._title = LabelRibbonGroup(spec.title, self)
            layout.addWidget(self._title)
        self.refresh_theme()

    def refresh_theme(self):
        self.setStyleSheet(
            "QFrame#RibbonGroup { "
            "background: transparent; "
            f"border-right: 1px solid {PALETTE['ribbon_separator']}; "
            "}"
        )
        if self._title is not None:
            self._title.refresh_theme()
