from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QFrame, QToolButton

from opencae.ui.core.icon_factory import make_icon


def ribbon_button(text, icon, checked=False, width=76):
    button = QToolButton(); button.setText(text); button.setIcon(make_icon(icon, 28)); button.setIconSize(QSize(28, 28))
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); button.setCheckable(checked is not None)
    if checked is not None: button.setChecked(checked)
    button.setProperty("ribbonButton", True); button.setFixedSize(width, 70); return button


def action_button(action, width=76):
    button = QToolButton(); button.setDefaultAction(action); button.setIconSize(QSize(28, 28))
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); button.setProperty("ribbonButton", True)
    button.setFixedSize(width, 70); return button


def vertical_separator():
    line = QFrame(); line.setFrameShape(QFrame.Shape.VLine); line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setFixedWidth(10); line.setContentsMargins(4, 8, 4, 8); return line
