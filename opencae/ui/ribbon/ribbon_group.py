"""Build one ribbon action group with a compact shared group title."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from opencae.ui.core.controls import action_button, action_group_button
from opencae.ui.core.theme import PALETTE


class RibbonGroup(QFrame):
    """Arrange ribbon buttons above one compact semantic group caption."""

    def __init__(self, spec, actions, parent=None):
        """Build one expanded or collapsed ribbon action group."""
        super().__init__(parent)
        self.setObjectName("RibbonGroup")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "QFrame#RibbonGroup { "
            "background: rgba(255,255,255,0.012); "
            f"border-right: 1px solid {PALETTE['border_light']}; "
            "}"
        )

        layout = QVBoxLayout(self)
        # Keep the group caption close to the lower edge so two-line action
        # captions get the available vertical space instead of being clipped.
        layout.setContentsMargins(8, 2, 9, 0)
        layout.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)

        if spec.collapsed:
            icon_action_id = spec.icon_action_id or spec.action_ids[0]
            row.addWidget(
                action_group_button(
                    spec.title.title(),
                    actions.get(icon_action_id),
                    tuple(actions.get(action_id) for action_id in spec.action_ids),
                )
            )
        else:
            for action_id in spec.action_ids:
                row.addWidget(action_button(actions.get(action_id)))

        layout.addLayout(row)

        if spec.collapsed:
            # Keep the same vertical footprint as expanded groups without
            # repeating the group title below the group button.
            layout.addSpacing(13)
        else:
            title = QLabel(spec.title)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet(
                f"color:{PALETTE['accent']};"
                "font-size:8pt;"
                "font-weight:600;"
                "letter-spacing:1px;"
                "border:none;"
                "background:transparent;"
            )
            layout.addWidget(title)
