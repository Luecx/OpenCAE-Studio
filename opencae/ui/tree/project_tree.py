import re

from PyQt6.QtCore import QModelIndex, QSignalBlocker, QSortFilterProxyModel, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import QTreeView

from opencae.ui.core.theme import PALETTE
from .branch_style import TreeBranchStyle
from .context_menu import VISIBILITY_KINDS, show_context_menu
from .stage_mapping import stage_for_kind
from .tree_builder import build_model
from .tree_roles import ENTITY_ROLE, KIND_ROLE, PART_ROLE

_FOCUS = {
    "MATERIALS": {"materials"}, "SECTIONS": {"sections"}, "PROFILES": {"profiles"}, "FIELDS": {"fields"},
    "PART": {"parts"}, "ASSEMBLY": {"assembly"}, "CONSTRAINTS": {"constraints"},
    "BOUNDARY CONDITIONS": {"boundary_conditions"}, "ANALYSIS": {"steps"},
}
_HIDDEN_COLOR = "#59616b"


class ProjectTree(QTreeView):
    stage_requested = pyqtSignal(str)

    def __init__(self, store, actions, visibility=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.actions = actions
        self.visibility = visibility
        self.current_stage = "PART"
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setRecursiveFilteringEnabled(True)
        self.setModel(self.proxy)
        self.selectionModel().selectionChanged.connect(self._selection)
        self._branch_style = TreeBranchStyle(self.style())
        self.setStyle(self._branch_style)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.setIndentation(18)
        self.setIconSize(QSize(18, 18))
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setExpandsOnDoubleClick(False)
        self.setAllColumnsShowFocus(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.doubleClicked.connect(self._edit_current)
        store.changed.connect(self.rebuild)
        store.active_part_changed.connect(
            lambda *_: self.set_stage_focus(self.current_stage, collapse=False)
        )
        if self.visibility is not None:
            self.visibility.changed.connect(self._visibility_changed)
        self.rebuild()

    def rebuild(self, *_):
        expanded = self._expanded_paths()
        current = self._index_path(self.currentIndex())
        # A proxy source-model reset otherwise emits a transient empty tree
        # selection. That used to clear the selected model entity and, with it,
        # persistent coupling/region highlighting while the tree was rebuilding.
        blocker = QSignalBlocker(self.selectionModel())
        try:
            self.proxy.setSourceModel(build_model(self.store.project))
            self.set_stage_focus(self.current_stage, collapse=False)
            self._apply_visibility_styles()
            self._restore_expanded(expanded)
            restored = self._find_path(current) if current else QModelIndex()
            if restored.isValid():
                self.setCurrentIndex(restored)
                self._expand_path(restored)
        finally:
            del blocker

    def _expanded_paths(self):
        return {
            self._index_path(index)
            for index in self._walk_indexes()
            if self.isExpanded(index)
        }

    def _restore_expanded(self, paths):
        for index in self._walk_indexes():
            if self._index_path(index) in paths:
                self.setExpanded(index, True)

    def _walk_indexes(self, parent=QModelIndex()):
        model = self.model()
        if model is None:
            return
        for row in range(model.rowCount(parent)):
            index = model.index(row, 0, parent)
            yield index
            yield from self._walk_indexes(index)

    def _index_path(self, index):
        if not index.isValid():
            return ()
        values = []
        current = index
        while current.isValid():
            entity = current.data(ENTITY_ROLE)
            entity_id = str(getattr(entity, "id", "") or "")
            kind = str(current.data(KIND_ROLE) or "")
            part_id = str(current.data(PART_ROLE) or "")
            if entity_id:
                token = (kind, entity_id)
            else:
                token = (kind, part_id, _stable_label(current.data(Qt.ItemDataRole.DisplayRole)))
            values.append(token)
            current = current.parent()
        return tuple(reversed(values))

    def _find_path(self, path):
        if not path:
            return QModelIndex()
        parent = QModelIndex()
        for token in path:
            match = QModelIndex()
            for row in range(self.model().rowCount(parent)):
                candidate = self.model().index(row, 0, parent)
                entity = candidate.data(ENTITY_ROLE)
                entity_id = str(getattr(entity, "id", "") or "")
                kind = str(candidate.data(KIND_ROLE) or "")
                part_id = str(candidate.data(PART_ROLE) or "")
                candidate_token = (
                    (kind, entity_id)
                    if entity_id else
                    (kind, part_id, _stable_label(candidate.data(Qt.ItemDataRole.DisplayRole)))
                )
                if candidate_token == token:
                    match = candidate
                    break
            if not match.isValid():
                return QModelIndex()
            parent = match
        return parent

    def _expand_path(self, index):
        current = index.parent()
        while current.isValid():
            self.setExpanded(current, True)
            current = current.parent()

    def set_filter_text(self, text):
        self.proxy.setFilterFixedString(text)
        if text:
            self.expandAll()

    def set_stage_focus(self, stage, collapse=True):
        self.current_stage = stage
        source = self.proxy.sourceModel()
        if source is None:
            return
        self.setUpdatesEnabled(False)
        try:
            active = _FOCUS.get(stage, set())
            for row in range(source.rowCount()):
                node = source.item(row)
                kind = node.data(KIND_ROLE)
                selected = kind in active
                self._style(node, selected)
                proxy_index = self.proxy.mapFromSource(node.index())
                if collapse:
                    self.setExpanded(proxy_index, selected)
                elif selected:
                    self.setExpanded(proxy_index, True)
                if kind == "parts":
                    self._style_parts(node, stage == "PART")
            self._apply_visibility_styles()
            self._expand_current_path()
        finally:
            self.setUpdatesEnabled(True)

    def _style_parts(self, parts, active):
        current = self.store.active_part_id
        for row in range(parts.rowCount()):
            node = parts.child(row)
            self._style(node, active and node.data(PART_ROLE) == current)
            for child_row in range(node.rowCount()):
                self._style(node.child(child_row), False)

    def _style(self, node, selected):
        hidden = self._item_hidden(node)
        font = QFont(node.font())
        font.setBold(bool(selected and not hidden))
        font.setItalic(hidden)
        node.setFont(font)
        color = _HIDDEN_COLOR if hidden else PALETTE["text"] if selected else PALETTE["muted"]
        node.setForeground(QBrush(QColor(color)))

    def _visibility_changed(self, *_):
        self._apply_visibility_styles()
        self.viewport().update()

    def _apply_visibility_styles(self):
        source = self.proxy.sourceModel()
        if source is None or self.visibility is None:
            return
        for node in self._walk_source_items(source.invisibleRootItem()):
            kind = str(node.data(KIND_ROLE) or "")
            if kind not in VISIBILITY_KINDS:
                continue
            hidden = self._item_hidden(node)
            font = QFont(node.font())
            font.setItalic(hidden)
            font.setBold(False)
            node.setFont(font)
            node.setForeground(
                QBrush(QColor(_HIDDEN_COLOR if hidden else PALETTE["text"]))
            )

    def _item_hidden(self, node):
        if self.visibility is None:
            return False
        kind = str(node.data(KIND_ROLE) or "")
        entity = node.data(ENTITY_ROLE)
        return bool(
            kind in VISIBILITY_KINDS
            and entity is not None
            and not self.visibility.is_entity_visible(entity)
        )

    def _walk_source_items(self, parent):
        for row in range(parent.rowCount()):
            node = parent.child(row)
            yield node
            yield from self._walk_source_items(node)

    def _expand_current_path(self):
        index = self.currentIndex().parent()
        while index.isValid():
            self.setExpanded(index, True)
            index = index.parent()

    def _selection(self, *_):
        index = self.currentIndex()
        entity = index.data(ENTITY_ROLE) if index.isValid() else None
        part_id = index.data(PART_ROLE) if index.isValid() else None
        if part_id:
            self.store.set_active_part(part_id)
        self.store.select(entity)
        stage = stage_for_kind(index.data(KIND_ROLE) if index.isValid() else None)
        if stage:
            self.stage_requested.emit(stage)

    def _edit_current(self, index):
        if index.data(ENTITY_ROLE) is None:
            return
        from opencae.ui.actions.ids import A
        self.actions.get(A.EDIT_SELECTED).trigger()

    def _menu(self, pos):
        index = self.indexAt(pos)
        if index.isValid():
            self.setCurrentIndex(index)
        show_context_menu(
            self,
            pos,
            index,
            self.actions,
            self.store,
            self.visibility,
        )


def _stable_label(value):
    return re.sub(r"\s+\([0-9,]+\)$", "", str(value or ""))
