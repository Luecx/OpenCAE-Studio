from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from opencae.ui.core.controls import action_button
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

        items = spec.layout_items or spec.action_ids
        for item in items:
            if isinstance(item, tuple):
                column = QVBoxLayout()
                column.setContentsMargins(0, 0, 0, 0)
                column.setSpacing(2)
                for action_id in item:
                    column.addWidget(
                        action_button(actions.get(action_id), large=False)
                    )
                row.addLayout(column)
            else:
                row.addWidget(action_button(actions.get(item)))

        layout.addLayout(row)

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
