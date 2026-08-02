from PyQt6.QtGui import QAction, QKeySequence

class ActionRegistry:
    def __init__(self,parent): self.parent=parent; self._actions={}
    def add(self,spec):
        action=QAction(spec.text,self.parent); action.setIcon(__import__('opencae.ui.core.icon_factory',fromlist=['make_icon']).make_icon(spec.icon)); action.triggered.connect(spec.handler)
        if spec.shortcut: action.setShortcut(QKeySequence(spec.shortcut))
        action.setStatusTip(spec.status_tip); self._actions[spec.id]=action; return action
    def get(self,action_id): return self._actions[action_id]
    def __contains__(self,action_id): return action_id in self._actions
