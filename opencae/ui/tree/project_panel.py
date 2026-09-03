from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.theme import PALETTE
from opencae.ui.core.icon_factory import IconKind, make_icon
from .project_tree import ProjectTree
from .solution_tree import SolutionTree


class ProjectPanel(QWidget):
    browser_requested = pyqtSignal(str)

    def __init__(self, store, actions, parent=None, visibility=None):
        super().__init__(parent)
        self.setObjectName("ProjectPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Project/Solution is a standalone QTabBar rather than a QTabWidget.
        # Give it an explicit semantic name so the application stylesheet does
        # not fall back to the platform-native tab appearance.
        self.tabs = QTabBar()
        self.tabs.setObjectName("BrowserTabBar")
        self.tabs.setDrawBase(False)
        self.tabs.addTab("Project")
        self.tabs.addTab("Solution")
        self.tabs.setExpanding(True)
        self.tabs.currentChanged.connect(self._tab_changed)
        layout.addWidget(self.tabs)

        self.toolbar = QWidget()
        self.toolbar.setObjectName("BrowserToolbar")
        row = QHBoxLayout(self.toolbar)
        row.setContentsMargins(7, 6, 5, 6)
        row.setSpacing(4)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter…")
        self.filter.setClearButtonEnabled(True)
        row.addWidget(self.filter, 1)
        self.expand_button = self._small_button("+")
        self.collapse_button = self._small_button("−")
        row.addWidget(self.expand_button)
        row.addWidget(self.collapse_button)
        layout.addWidget(self.toolbar)

        self.stack = QStackedWidget()
        self.tree = ProjectTree(store, actions, parent=None, visibility=visibility)
        self.solution_tree = SolutionTree(store)
        self.stack.addWidget(self.tree)
        self.stack.addWidget(self.solution_tree)
        layout.addWidget(self.stack, 1)
        self.filter.textChanged.connect(self._filter)
        self.expand_button.clicked.connect(self._expand)
        self.collapse_button.clicked.connect(self._collapse)
        self.refresh_theme()

    def refresh_theme(self):
        self.toolbar.setStyleSheet(
            f"QWidget#BrowserToolbar {{ background:{PALETTE['panel']}; "
            f"border:none; border-bottom:1px solid {PALETTE['border']}; }}"
        )
        self.tabs.setTabIcon(0, make_icon(IconKind.PART, 16))
        self.tabs.setTabIcon(1, make_icon(IconKind.RESULTS, 16))

    def set_browser(self, name):
        self.tabs.setCurrentIndex(1 if name == "solution" else 0)

    def _tab_changed(self, index):
        self.stack.setCurrentIndex(index)
        self._filter(self.filter.text())
        self.browser_requested.emit("solution" if index == 1 else "project")

    def _filter(self, text):
        if self.stack.currentWidget() is self.tree:
            self.tree.set_filter_text(text)

    def _expand(self):
        self.stack.currentWidget().expandAll()

    def _collapse(self):
        self.stack.currentWidget().collapseAll()

    @staticmethod
    def _small_button(text):
        button = QToolButton()
        button.setText(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(28, 28)
        return button
