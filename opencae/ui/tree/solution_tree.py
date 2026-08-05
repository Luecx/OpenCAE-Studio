"""Displays job-bound solver fields and topology iteration frames."""

import logging

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QMenu, QTreeView

from opencae.results import FrdLoader
from opencae.results.navigation import (
    display_field,
    fields_for,
    frame_keys,
    frame_label,
    step_ids,
    step_label,
)
from opencae.ui.core.icon_factory import IconKind, make_icon
from .branch_style import TreeBranchStyle

_LOG = logging.getLogger(__name__)


class SolutionTree(QTreeView):
    solution_requested = pyqtSignal(object, object)
    delete_requested = pyqtSignal(object)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setHeaderHidden(True)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setIndentation(18)
        self.setIconSize(QSize(18, 18))
        self.setStyle(TreeBranchStyle(self.style()))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self.clicked.connect(self._clicked)
        self.expanded.connect(self._exclusive_expand)
        store.changed.connect(self.rebuild)
        self.rebuild()

    def rebuild(self, *_):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Solutions"])
        root = model.invisibleRootItem()
        loader = FrdLoader()
        for result in self.store.project.results:
            metadata = dict(result.metadata or {})
            result_item = self._item(
                result.name,
                result,
                None,
                IconKind.RESULTS,
            )
            root.appendRow(result_item)
            if metadata.get("result_kind") == "topology_density":
                self._append_topology_frames(result_item, result, metadata)
                continue
            if result.source_file:
                try:
                    result.fields = loader.fields(result.source_file)
                except (OSError, RuntimeError, TypeError, ValueError) as exc:
                    _LOG.warning(
                        "Could not load result tree from %s: %s",
                        result.source_file,
                        exc,
                    )
                    self.store.message.emit(
                        f"Could not load results '{result.name}': {exc}"
                    )
            for step_index, step_id in enumerate(step_ids(result.fields)):
                step = self._item(
                    step_label(result, step_id, step_index),
                    result,
                    None,
                    IconKind.RESULT_STEP,
                )
                result_item.appendRow(step)
                for frame_id, value in frame_keys(result.fields, step_id):
                    frame = self._item(
                        frame_label(frame_id, value),
                        result,
                        None,
                        IconKind.RESULT_FRAME,
                    )
                    step.appendRow(frame)
                    for field in fields_for(result.fields, step_id, frame_id):
                        block = self._item(
                            field.name,
                            result,
                            display_field(field, "Magnitude"),
                            IconKind.FIELD,
                        )
                        frame.appendRow(block)
                        for component in (
                            *field.metadata.get("components", ()),
                            *field.metadata.get("derived", ()),
                        ):
                            block.appendRow(
                                self._item(
                                    component,
                                    result,
                                    display_field(field, component),
                                    IconKind.CONTOUR,
                                )
                            )
        self.setModel(model)
        self.collapseAll()
        self._expand_first_chain()

    def _append_topology_frames(self, parent, result, metadata):
        group = self._item(
            "Topology Density",
            result,
            None,
            IconKind.RESULT_STEP,
        )
        parent.appendRow(group)
        for index, frame in enumerate(metadata.get("frames", ())):
            number = int(frame.get("number", index + 1))
            objective = float(frame.get("objective", 0.0))
            change = float(frame.get("maximum_density_change", 0.0))
            label = (
                f"Iteration {number}   f={objective:.6g}   Δρ={change:.3g}"
            )
            group.appendRow(
                self._item(
                    label,
                    result,
                    {"topology_frame_index": index},
                    IconKind.RESULT_FRAME,
                )
            )

    def _expand_first_chain(self):
        index = self.model().index(0, 0)
        while index.isValid():
            self.expand(index)
            index = self.model().index(0, 0, index)

    def _exclusive_expand(self, index):
        parent = index.parent()
        rows = self.model().rowCount(parent)
        for row in range(rows):
            sibling = self.model().index(row, 0, parent)
            if sibling != index:
                self.collapse(sibling)

    @staticmethod
    def _item(text, result, field, icon):
        item = QStandardItem(make_icon(icon, 18), text)
        item.setEditable(False)
        item.setData(result, Qt.ItemDataRole.UserRole)
        item.setData(field, Qt.ItemDataRole.UserRole + 1)
        return item

    def _clicked(self, index):
        result = index.data(Qt.ItemDataRole.UserRole)
        field = index.data(Qt.ItemDataRole.UserRole + 1)
        if result is not None:
            self.solution_requested.emit(result, field)

    def _context_menu(self, position):
        index = self.indexAt(position)
        result = (
            index.data(Qt.ItemDataRole.UserRole)
            if index.isValid()
            else None
        )
        if result is None:
            return
        self.setCurrentIndex(index)
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Result")
        selected = menu.exec(self.viewport().mapToGlobal(position))
        if selected is delete_action:
            self.delete_requested.emit(result)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            index = self.currentIndex()
            result = (
                index.data(Qt.ItemDataRole.UserRole)
                if index.isValid()
                else None
            )
            if result is not None:
                self.delete_requested.emit(result)
                event.accept()
                return
        super().keyPressEvent(event)
