from dataclasses import replace

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.core.metrics import RIBBON_BUTTON_WIDTH
from .ribbon_group import RibbonGroup


_PAGE_LEFT_MARGIN = 5
_GROUP_LEFT_MARGIN = 8
_GROUP_RIGHT_MARGIN = 9
_GROUP_SPACING = 2


class ResponsiveRibbonPage(QWidget):
    """Ribbon page that collapses its widest groups only when space is tight."""

    def __init__(self, groups, actions, leading_widgets=(), parent=None):
        super().__init__(parent)
        self.actions = actions
        self._specs = tuple(groups)
        self._leading_widgets = tuple(leading_widgets)
        self._collapsed_titles = frozenset()
        self._group_widgets = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(_PAGE_LEFT_MARGIN, 0, 0, 0)
        layout.setSpacing(0)
        self._page_layout = layout

        for widget in self._leading_widgets:
            layout.addWidget(widget)

        self._groups_host = QWidget(self)
        self._groups_host.setMinimumWidth(0)
        self._groups_layout = QHBoxLayout(self._groups_host)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(0)
        layout.addWidget(self._groups_host, 1)

        self._render_groups(self._collapsed_titles)
        QTimer.singleShot(0, self._refresh_responsive_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_responsive_layout(event.size().width())

    @staticmethod
    def _group_width(spec, collapsed=False):
        button_count = 1 if collapsed else len(spec.action_ids)
        return (
            _GROUP_LEFT_MARGIN
            + _GROUP_RIGHT_MARGIN
            + button_count * RIBBON_BUTTON_WIDTH
            + max(0, button_count - 1) * _GROUP_SPACING
        )

    @staticmethod
    def _widget_width(widget):
        return max(
            0,
            widget.minimumWidth(),
            widget.minimumSizeHint().width(),
            widget.sizeHint().width(),
        )

    def _required_width(self, collapsed_titles):
        width = _PAGE_LEFT_MARGIN
        width += sum(self._widget_width(widget) for widget in self._leading_widgets)
        for spec in self._specs:
            width += self._group_width(
                spec,
                collapsed=spec.title in collapsed_titles,
            )
        return width

    def _collapse_candidates(self):
        candidates = [
            (index, spec)
            for index, spec in enumerate(self._specs)
            if self._group_width(spec, True) < self._group_width(spec, False)
        ]
        candidates.sort(
            key=lambda item: (-self._group_width(item[1], False), item[0])
        )
        return tuple(spec for _, spec in candidates)

    def _target_collapsed_groups(self, available_width):
        collapsed = set()
        if self._required_width(collapsed) <= available_width:
            return frozenset()

        for spec in self._collapse_candidates():
            collapsed.add(spec.title)
            if self._required_width(collapsed) <= available_width:
                break
        return frozenset(collapsed)

    def _refresh_responsive_layout(self, available_width=None):
        width = self.width() if available_width is None else available_width
        target = self._target_collapsed_groups(width)
        if target == self._collapsed_titles:
            return
        self._collapsed_titles = target
        self._render_groups(target)

    def _render_groups(self, collapsed_titles):
        while self._groups_layout.count():
            item = self._groups_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._group_widgets.clear()
        for spec in self._specs:
            rendered_spec = replace(
                spec,
                collapsed=spec.title in collapsed_titles,
            )
            group = RibbonGroup(rendered_spec, self.actions, self._groups_host)
            self._groups_layout.addWidget(group)
            self._group_widgets.append(group)
        self._groups_layout.addStretch(1)


class RibbonPage(ResponsiveRibbonPage):
    def __init__(self, groups, actions, parent=None):
        super().__init__(groups, actions, parent=parent)
