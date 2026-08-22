from dataclasses import replace

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.actions.ids import A
from opencae.ui.core.metrics import RIBBON_BUTTON_WIDTH
from .part_selector import PartSelector
from .ribbon_group import RibbonGroup
from .specs import RibbonGroupSpec


_PAGE_LEFT_MARGIN = 5
_GROUP_LEFT_MARGIN = 8
_GROUP_RIGHT_MARGIN = 9
_GROUP_SPACING = 2
_COLLAPSE_ORDER = ("GEOMETRY", "MESH", "REGIONS")


class PartPage(QWidget):
    """Part ribbon that collapses wide groups only when horizontal space is tight."""

    def __init__(self, actions, store, parent=None):
        super().__init__(parent)
        self.actions = actions
        self._collapsed_titles = frozenset()
        self._group_widgets = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(_PAGE_LEFT_MARGIN, 0, 0, 0)
        layout.setSpacing(0)

        self.part_selector = PartSelector(store)
        layout.addWidget(self.part_selector)

        self._groups_host = QWidget(self)
        self._groups_host.setMinimumWidth(0)
        self._groups_layout = QHBoxLayout(self._groups_host)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(0)
        layout.addWidget(self._groups_host, 1)

        self._specs = (
            RibbonGroupSpec(
                "GEOMETRY",
                (
                    A.NEW_PART,
                    A.DUPLICATE_PART,
                    A.IMPORT_GEOMETRY,
                    A.IMPORT_MESH,
                    A.PARTITION,
                    A.REBUILD_GEOMETRY,
                    A.SUPPRESS_FEATURE,
                ),
                icon_action_id=A.NEW_PART,
            ),
            RibbonGroupSpec("DISPLAY", (A.VISIBILITY,)),
            RibbonGroupSpec(
                "DATUM",
                (A.DATUM_POINT, A.DATUM_VECTOR, A.DATUM_PLANE),
            ),
            RibbonGroupSpec(
                "MESH",
                (
                    A.DEFAULT_SEED,
                    A.EDGE_SEED,
                    A.ELEMENT_CONTROLS,
                    A.MESH_SETTINGS,
                    A.GENERATE_MESH,
                    A.CLEAR_MESH,
                ),
                icon_action_id=A.GENERATE_MESH,
            ),
            RibbonGroupSpec(
                "REGIONS",
                (
                    A.NODE_SET,
                    A.ELEMENT_SET,
                    A.SURFACE,
                    A.PART_RP,
                    A.PART_CSYS,
                ),
                icon_action_id=A.NODE_SET,
            ),
            RibbonGroupSpec("PROPERTIES", (A.SECTION_ASSIGNMENT,)),
        )

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

    def _required_width(self, collapsed_titles):
        width = _PAGE_LEFT_MARGIN + self.part_selector.sizeHint().width()
        for spec in self._specs:
            width += self._group_width(
                spec,
                collapsed=spec.title in collapsed_titles,
            )
        return width

    def _target_collapsed_groups(self, available_width):
        collapsed = set()
        if self._required_width(collapsed) <= available_width:
            return frozenset()

        for title in _COLLAPSE_ORDER:
            collapsed.add(title)
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


def create(actions, store):
    return PartPage(actions, store)
