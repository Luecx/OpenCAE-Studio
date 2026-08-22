from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.metrics import (
    RIBBON_BUTTON_HEIGHT,
    RIBBON_BUTTON_WIDTH,
    RIBBON_ICON_SIZE,
)
from opencae.ui.core.theme import PALETTE


_GROUP_LEFT_MARGIN = 8
_GROUP_RIGHT_MARGIN = 9
_GROUP_SPACING = 2


class ResultRibbonGroup(QFrame):
    def __init__(self, title, widgets=(), parent=None):
        super().__init__(parent)
        self.title = title
        self.widgets = tuple(widgets)
        self._collapsed = False
        self.setObjectName("RibbonGroup")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            f"QFrame#RibbonGroup {{ background: rgba(255,255,255,0.012); "
            f"border-right: 1px solid {PALETTE['border_light']}; }}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(_GROUP_LEFT_MARGIN, 4, _GROUP_RIGHT_MARGIN, 2)
        self._layout.setSpacing(1)
        self._build_expanded()

    @staticmethod
    def _widget_width(widget):
        return max(
            0,
            widget.minimumWidth(),
            widget.minimumSizeHint().width(),
            widget.sizeHint().width(),
        )

    def expanded_width_hint(self):
        widths = [self._widget_width(widget) for widget in self.widgets]
        return (
            _GROUP_LEFT_MARGIN
            + _GROUP_RIGHT_MARGIN
            + sum(widths)
            + max(0, len(widths) - 1) * _GROUP_SPACING
        )

    def collapsed_width_hint(self):
        return _GROUP_LEFT_MARGIN + _GROUP_RIGHT_MARGIN + RIBBON_BUTTON_WIDTH

    def set_collapsed(self, collapsed):
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        for widget in self.widgets:
            widget.hide()
            widget.setParent(None)
        self._clear_layout(self._layout)
        if collapsed:
            self._build_collapsed()
        else:
            self._build_expanded()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            widget = item.widget()
            if child_layout is not None:
                self._clear_layout(child_layout)
                child_layout.deleteLater()
            elif widget is not None and widget not in self.widgets:
                widget.deleteLater()

    def _build_expanded(self):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(_GROUP_SPACING)
        for widget in self.widgets:
            row.addWidget(widget)
            widget.show()
        self._layout.addLayout(row)
        label = QLabel(self.title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color:{PALETTE['accent']};font-size:8pt;font-weight:600;"
            "letter-spacing:1px;border:none;background:transparent;"
        )
        self._layout.addWidget(label)

    def _build_collapsed(self):
        button = QToolButton(self)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        if self.widgets and hasattr(self.widgets[0], "icon"):
            button.setIcon(self.widgets[0].icon())
        button.setIconSize(QSize(RIBBON_ICON_SIZE, RIBBON_ICON_SIZE))
        button.setFixedSize(RIBBON_BUTTON_WIDTH, RIBBON_BUTTON_HEIGHT)
        button.setText(self.title.title())
        button.setProperty("ribbonButton", True)

        menu = QMenu(button)
        panel = QWidget(menu)
        row = QHBoxLayout(panel)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(_GROUP_SPACING)
        for widget in self.widgets:
            row.addWidget(widget)
            widget.show()

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(panel)
        menu.addAction(widget_action)
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(button)
        self._layout.addLayout(row_layout)
        self._layout.addSpacing(14)
