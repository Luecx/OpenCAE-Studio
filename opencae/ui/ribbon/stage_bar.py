from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QToolButton, QWidget

from opencae.ui.core.metrics import STAGE_BAR_HEIGHT
from opencae.ui.core.theme import PALETTE

STAGES = (
    "MATERIALS", "SECTIONS", "PROFILES", "FIELDS", "PART", "ASSEMBLY",
    "CONSTRAINTS", "BOUNDARY CONDITIONS", "ANALYSIS", "SOLVE", "RESULTS",
)


class StageBar(QWidget):
    stage_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("StageBar"); self.setFixedHeight(STAGE_BAR_HEIGHT)
        layout = QHBoxLayout(self); layout.setContentsMargins(8, 0, 8, 0); layout.setSpacing(1)
        self.group = QButtonGroup(self); self.group.setExclusive(True); self.buttons = {}
        for index, stage in enumerate(STAGES):
            button = self._button(stage); button.clicked.connect(lambda checked=False, name=stage: self.stage_changed.emit(name))
            self.group.addButton(button, index); self.buttons[stage] = button; layout.addWidget(button)
            if stage == "PART": button.setChecked(True)
        layout.addStretch(1)

    def set_stage(self, stage):
        button = self.buttons.get(stage)
        if button is not None: button.setChecked(True)

    @staticmethod
    def _button(stage):
        p = PALETTE; button = QToolButton(); button.setText(stage); button.setCheckable(True); button.setAutoExclusive(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        widths = {"BOUNDARY CONDITIONS": 158, "CONSTRAINTS": 108}
        button.setMinimumWidth(widths.get(stage, 82)); button.setFixedHeight(40)
        button.setStyleSheet(f"""
            QToolButton {{ border:none; border-bottom:3px solid transparent; padding:4px 10px;
                font-weight:600; color:{p['muted']}; }}
            QToolButton:hover {{ background:{p['panel_hover']}; color:{p['text']}; }}
            QToolButton:checked {{ color:{p['text']}; border-bottom-color:{p['accent']}; background:{p['panel_alt']}; }}
        """)
        return button
