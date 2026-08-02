from PyQt6.QtCore import QSortFilterProxyModel, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QTreeView

from opencae.ui.core.theme import PALETTE
from .branch_style import TreeBranchStyle
from .context_menu import show_context_menu
from .stage_mapping import stage_for_kind
from .tree_builder import build_model
from .tree_roles import ENTITY_ROLE, KIND_ROLE, PART_ROLE

_FOCUS = {
    "MATERIALS": {"Materials"}, "SECTIONS": {"Sections"}, "PROFILES": {"Profiles"}, "FIELDS": {"Fields"},
    "PART": {"Parts"}, "ASSEMBLY": {"Assembly"}, "CONSTRAINTS": {"Constraints"},
    "BOUNDARY CONDITIONS": {"Boundary Conditions"}, "ANALYSIS": {"Steps"},
}


class ProjectTree(QTreeView):
    stage_requested = pyqtSignal(str)

    def __init__(self, store, actions, parent=None):
        super().__init__(parent); self.store = store; self.actions = actions; self.current_stage = "PART"
        self.proxy = QSortFilterProxyModel(self); self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive); self.proxy.setRecursiveFilteringEnabled(True); self.setModel(self.proxy)
        self._branch_style = TreeBranchStyle(self.style()); self.setStyle(self._branch_style); self.setHeaderHidden(True)
        self.setAlternatingRowColors(False); self.setUniformRowHeights(True); self.setAnimated(False); self.setIndentation(18); self.setIconSize(QSize(18, 18))
        self.setRootIsDecorated(True); self.setItemsExpandable(True); self.setExpandsOnDoubleClick(False); self.setAllColumnsShowFocus(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.customContextMenuRequested.connect(self._menu); self.doubleClicked.connect(self._edit_current)
        store.changed.connect(self.rebuild); store.active_part_changed.connect(lambda *_: self.set_stage_focus(self.current_stage, collapse=False)); self.rebuild()

    def rebuild(self, *_):
        self.proxy.setSourceModel(build_model(self.store.project)); self.selectionModel().selectionChanged.connect(self._selection)
        self.set_stage_focus(self.current_stage, collapse=False)

    def set_filter_text(self, text):
        self.proxy.setFilterFixedString(text)
        if text: self.expandAll()

    def set_stage_focus(self, stage, collapse=True):
        self.current_stage = stage; source = self.proxy.sourceModel()
        if source is None: return
        self.setUpdatesEnabled(False)
        try:
            active = _FOCUS.get(stage, set())
            for row in range(source.rowCount()):
                node = source.item(row); selected = node.text() in active
                self._style(node, selected)
                proxy_index = self.proxy.mapFromSource(node.index())
                if collapse: self.setExpanded(proxy_index, selected)
                elif selected: self.setExpanded(proxy_index, True)
                if node.text() == "Parts": self._style_parts(node, stage == "PART")
            self._expand_current_path()
        finally: self.setUpdatesEnabled(True)

    def _style_parts(self, parts, active):
        current = self.store.active_part_id
        for row in range(parts.rowCount()):
            node = parts.child(row); self._style(node, active and node.data(PART_ROLE) == current)
            for child_row in range(node.rowCount()): self._style(node.child(child_row), False)

    @staticmethod
    def _style(node, selected):
        font = QFont(node.font()); font.setBold(bool(selected)); node.setFont(font)
        node.setForeground(QBrush(QColor(PALETTE["text"] if selected else PALETTE["muted"])))

    def _expand_current_path(self):
        index = self.currentIndex().parent()
        while index.isValid(): self.setExpanded(index, True); index = index.parent()

    def _selection(self, *_):
        index = self.currentIndex(); entity = index.data(ENTITY_ROLE) if index.isValid() else None; part_id = index.data(PART_ROLE) if index.isValid() else None
        if part_id: self.store.set_active_part(part_id)
        self.store.select(entity); stage = stage_for_kind(index.data(KIND_ROLE) if index.isValid() else None)
        if stage: self.stage_requested.emit(stage)

    def _edit_current(self, index):
        if index.data(ENTITY_ROLE) is None: return
        from opencae.ui.actions.ids import A
        self.actions.get(A.EDIT_SELECTED).trigger()

    def _menu(self, pos):
        index = self.indexAt(pos)
        if index.isValid(): self.setCurrentIndex(index)
        show_context_menu(self, pos, index.data(KIND_ROLE) if index.isValid() else None, self.actions, self.store)
