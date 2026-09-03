from PyQt6.QtGui import QAction, QKeySequence


class ActionRegistry:
    def __init__(self, parent):
        self.parent = parent
        self._actions = {}
        self._icon_kinds = {}

    def add(self, spec):
        make_icon = __import__(
            "opencae.ui.core.icon_factory",
            fromlist=["make_icon"],
        ).make_icon
        action = QAction(spec.text, self.parent)
        action.setIcon(make_icon(spec.icon))
        action.triggered.connect(spec.handler)
        if spec.shortcut:
            action.setShortcut(QKeySequence(spec.shortcut))
        action.setStatusTip(spec.status_tip)
        self._actions[spec.id] = action
        self._icon_kinds[spec.id] = spec.icon
        return action

    def get(self, action_id):
        return self._actions[action_id]

    def items(self):
        """Return stable action-id/QAction pairs for documentation-style UI."""
        return tuple(self._actions.items())

    def refresh_icons(self) -> None:
        """Regenerate theme-colored action icons without recreating actions."""
        make_icon = __import__(
            "opencae.ui.core.icon_factory",
            fromlist=["make_icon"],
        ).make_icon
        for action_id, action in self._actions.items():
            icon_kind = self._icon_kinds.get(action_id)
            if icon_kind is not None:
                action.setIcon(make_icon(icon_kind))

    def __contains__(self, action_id):
        return action_id in self._actions
