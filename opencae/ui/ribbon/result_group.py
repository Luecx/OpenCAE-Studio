from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from opencae.ui.composites.collapsed_widget_group import CollapsedWidgetGroupButton
from opencae.ui.core.metrics import RIBBON_BUTTON_WIDTH
from opencae.ui.core.theme import PALETTE


_GROUP_LEFT_MARGIN = 8
_GROUP_RIGHT_MARGIN = 9
_GROUP_SPACING = 2


class ResultRibbonGroup(QFrame):
    """Responsive Results group that preserves existing child widget instances."""

    def __init__(self, title, widgets=(), parent=None):
        super().__init__(parent)
        self.title = title
        self.widgets = tuple(widgets)
        for widget in self.widgets:
            if isinstance(widget, QToolButton):
                widget.setProperty("resultsRibbonButton", True)
        self._collapsed = False
        self.setObjectName("RibbonGroup")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(_GROUP_LEFT_MARGIN, 4, _GROUP_RIGHT_MARGIN, 2)
        self._layout.setSpacing(1)
        self._build_expanded()
        self.refresh_theme()

    def refresh_theme(self):
        self.setStyleSheet(
            "QFrame#RibbonGroup { background: transparent; "
            f"border-right: 1px solid {PALETTE['ribbon_separator']}; }}"
        )
        for label in self.findChildren(QLabel, "ResultRibbonGroupTitle"):
            label.setStyleSheet(
                f"color:{PALETTE['accent']};font-size:8pt;font-weight:600;"
                "letter-spacing:1px;border:none;background:transparent;"
            )

    @staticmethod
    def _widget_width(widget):
        return max(0, widget.minimumWidth(), widget.minimumSizeHint().width(), widget.sizeHint().width())

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
        self.refresh_theme()

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
        label.setObjectName("ResultRibbonGroupTitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(label)

    def _build_collapsed(self):
        icon = self.widgets[0].icon() if self.widgets and hasattr(self.widgets[0], "icon") else None
        button = CollapsedWidgetGroupButton(
            self.title.title(),
            self.widgets,
            icon=icon,
            spacing=_GROUP_SPACING,
            property_name="resultsRibbonButton",
            parent=self,
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(button)
        self._layout.addLayout(row)
        self._layout.addSpacing(14)
