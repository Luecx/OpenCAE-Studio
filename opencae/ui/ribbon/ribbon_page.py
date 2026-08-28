from dataclasses import replace

from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLayout, QSizePolicy, QWidget

from opencae.ui.core.metrics import RIBBON_BUTTON_WIDTH
from opencae.ui.core.theme import PALETTE
from .ribbon_group import RibbonGroup


_PAGE_LEFT_MARGIN = 5
_GROUP_LEFT_MARGIN = 8
_GROUP_RIGHT_MARGIN = 9
_GROUP_SPACING = 2
_LEADING_SEPARATOR_WIDTH = 9


class ResponsiveRibbonPage(QWidget):
    """Ribbon page that collapses its widest groups only when space is tight."""

    def __init__(self, groups, actions, leading_widgets=(), parent=None):
        super().__init__(parent)
        self.actions = actions
        self._specs = tuple(groups)
        self._leading_widgets = tuple(leading_widgets)
        self._collapsed_titles = frozenset()
        self._group_widgets = []

        # The currently rendered expanded groups must never become a window
        # minimum-size constraint. Otherwise Qt allows only one collapse step
        # per separate resize gesture: after one group collapses the page gets
        # a smaller minimum size and only then permits the next resize.
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(_PAGE_LEFT_MARGIN, 0, 0, 0)
        layout.setSpacing(0)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self._page_layout = layout

        for widget in self._leading_widgets:
            layout.addWidget(widget)

        self._leading_separator = None
        if self._leading_widgets and self._specs:
            separator = QWidget(self)
            separator.setObjectName("RibbonLeadingSeparator")
            separator.setFixedWidth(_LEADING_SEPARATOR_WIDTH)
            separator.setStyleSheet(
                "QWidget#RibbonLeadingSeparator { "
                "background: transparent; "
                f"border-right: 1px solid {PALETTE['border_light']}; "
                "}"
            )
            layout.addWidget(separator)
            self._leading_separator = separator

        self._groups_host = QWidget(self)
        self._groups_host.setMinimumWidth(0)
        self._groups_host.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self._groups_layout = QHBoxLayout(self._groups_host)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(0)
        self._groups_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        layout.addWidget(self._groups_host, 1)

        self._render_groups(self._collapsed_titles)
        QTimer.singleShot(0, self._refresh_responsive_layout)

    def minimumSizeHint(self):
        """Do not let the current expansion state block further shrinking."""
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())

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
        if self._leading_widgets and self._specs:
            width += _LEADING_SEPARATOR_WIDTH
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

        # Deliberately continue in this one call until the page fits. This is
        # what allows Geometry -> Mesh -> Datum -> Regions to all collapse
        # during a single continuous window resize when necessary.
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
        self._groups_host.updateGeometry()
        self.updateGeometry()


class RibbonPage(ResponsiveRibbonPage):
    def __init__(self, groups, actions, parent=None):
        super().__init__(groups, actions, parent=parent)
