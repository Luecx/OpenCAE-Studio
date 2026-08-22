from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from opencae.ui.core.controls import action_button, action_group_button
from opencae.ui.core.theme import PALETTE


class RibbonGroup(QFrame):
    def __init__(self, spec, actions, parent=None):
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
        layout.setContentsMargins(8, 4, 9, 2)
        layout.setSpacing(1)

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
            layout.addSpacing(14)
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
