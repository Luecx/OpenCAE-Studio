"""Top-level workflow stage selector."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QToolButton, QWidget

from opencae.ui.core.metrics import STAGE_BAR_HEIGHT
from opencae.ui.core.theme import PALETTE

STAGES = (
    "MATERIALS",
    "SECTIONS",
    "PROFILES",
    "FIELDS",
    "PART",
    "ASSEMBLY",
    "CONSTRAINTS",
    "BOUNDARY CONDITIONS",
    "STEPS",
    "ANALYSIS",
    "STUDIES",
    "RESULTS",
)


class StageBar(QWidget):
    stage_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StageBar")
        self.setFixedHeight(STAGE_BAR_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(1)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for index, stage in enumerate(STAGES):
            button = self._button(stage)
            button.clicked.connect(
                lambda checked=False, name=stage: self.stage_changed.emit(name)
            )
            self.group.addButton(button, index)
            self.buttons[stage] = button
            layout.addWidget(button)
            if stage == "PART":
                button.setChecked(True)
        layout.addStretch(1)

    def set_stage(self, stage):
        button = self.buttons.get(stage)
        if button is not None:
            button.setChecked(True)

    @staticmethod
    def _button(stage):
        palette = PALETTE
        button = QToolButton()
        button.setText(stage)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        widths = {
            "BOUNDARY CONDITIONS": 158,
            "CONSTRAINTS": 108,
            "ANALYSIS": 96,
            "STUDIES": 92,
        }
        button.setMinimumWidth(widths.get(stage, 82))
        button.setFixedHeight(40)
        button.setStyleSheet(
            f"""
            QToolButton {{ border:none; border-bottom:3px solid transparent;
                padding:4px 10px; font-weight:600; color:{palette['muted']}; }}
            QToolButton:hover {{ background:{palette['panel_hover']}; color:{palette['text']}; }}
            QToolButton:checked {{ color:{palette['text']}; border-bottom-color:{palette['accent']};
                background:{palette['panel_alt']}; }}
            """
        )
        return button
