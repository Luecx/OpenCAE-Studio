from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from opencae.ui.core.theme import PALETTE
from opencae.ui.core.icon_factory import IconKind, make_icon
from opencae.ui.primitives.buttons import ActionButton, ButtonPresentation
from .project_tree import ProjectTree
from .solution_tree import SolutionTree


class ProjectPanel(QWidget):
    browser_requested = pyqtSignal(str)
    project_close_requested = pyqtSignal(int)

    def __init__(self, store, actions, parent=None, visibility=None):
        super().__init__(parent)
        self.store = store
        self.setObjectName("ProjectPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabBar()
        self.tabs.setObjectName("BrowserTabBar")
        self.tabs.setDrawBase(False)
        self.tabs.addTab("Project")
        self.tabs.addTab("Solution")
        self.tabs.setExpanding(True)
        self.tabs.currentChanged.connect(self._tab_changed)

        self.project_selector = ActionButton(
            text="▾",
            presentation=ButtonPresentation.DEFAULT,
            object_name="ProjectSelectorButton",
            parent=self.tabs,
        )
        self.project_selector.setAutoRaise(True)
        self.project_selector.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_selector.setFixedWidth(20)
        self.project_selector.clicked.connect(self._show_project_menu)
        self.tabs.setTabButton(
            0,
            QTabBar.ButtonPosition.RightSide,
            self.project_selector,
        )
        layout.addWidget(self.tabs)

        self.toolbar = QWidget()
        self.toolbar.setObjectName("BrowserToolbar")
        row = QHBoxLayout(self.toolbar)
        row.setContentsMargins(7, 6, 5, 6)
        row.setSpacing(4)
        self.filter = QLineEdit()
        self.filter.setObjectName("BrowserSearch")
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

        projects_changed = getattr(store, "projects_changed", None)
        if projects_changed is not None:
            projects_changed.connect(self._refresh_project_selector)
        active_project_changed = getattr(store, "active_project_changed", None)
        if active_project_changed is not None:
            active_project_changed.connect(self._active_project_changed)

        self.refresh_theme()
        self._refresh_project_selector()

    def refresh_theme(self):
        self.toolbar.setStyleSheet(
            f"QWidget#BrowserToolbar {{ background:{PALETTE['panel']}; "
            f"border:none; border-bottom:1px solid {PALETTE['border']}; }}"
        )
        self.filter.setStyleSheet(
            f"QLineEdit#BrowserSearch {{"
            f"background:{PALETTE['search']};"
            f"color:{PALETTE['text']};"
            f"border:1px solid {PALETTE['border_light']};"
            "border-radius:4px; padding:5px 9px;"
            "}"
            f"QLineEdit#BrowserSearch:hover {{border-color:{PALETTE['border_hover']};}}"
            f"QLineEdit#BrowserSearch:focus {{border-color:{PALETTE['accent']};}}"
        )
        self.tabs.setTabIcon(0, make_icon(IconKind.PART, 16))
        self.tabs.setTabIcon(1, make_icon(IconKind.RESULTS, 16))

    def set_browser(self, name):
        self.tabs.setCurrentIndex(1 if name == "solution" else 0)

    def _tab_changed(self, index):
        self.stack.setCurrentIndex(index)
        self._filter(self.filter.text())
        self.browser_requested.emit("solution" if index == 1 else "project")

    def _projects(self):
        projects = getattr(self.store, "projects", None)
        if projects is None:
            return (self.store.project,)
        return tuple(projects)

    def _active_project_index(self):
        return int(getattr(self.store, "active_project_index", 0))

    def _is_placeholder_project(self, index):
        checker = getattr(self.store, "is_placeholder_project", None)
        return bool(callable(checker) and checker(int(index)))

    def _refresh_project_selector(self, *_args):
        projects = self._projects()
        active_index = self._active_project_index()
        if not projects or not 0 <= active_index < len(projects):
            self.project_selector.setEnabled(False)
            self.tabs.setTabToolTip(0, "Project")
            return
        project = projects[active_index]
        name = str(getattr(project, "name", "Project") or "Project")
        can_open_menu = len(projects) > 1 or not self._is_placeholder_project(active_index)
        self.project_selector.setEnabled(can_open_menu)
        self.project_selector.setToolTip(
            f"Active project: {name}\nChoose or close an open project"
        )
        self.tabs.setTabToolTip(0, f"Active project: {name}")

    def _active_project_changed(self, _index):
        self._refresh_project_selector()
        self.tabs.setCurrentIndex(0)

    def _show_project_menu(self):
        projects = self._projects()
        if not projects:
            return
        self.tabs.setCurrentIndex(0)
        active_index = self._active_project_index()
        menu = QMenu(self.project_selector)
        menu.setObjectName("ProjectSelectorMenu")
        for index, project in enumerate(projects):
            action = QWidgetAction(menu)
            action.setDefaultWidget(
                self._project_menu_row(menu, index, project, index == active_index)
            )
            menu.addAction(action)
        menu.exec(
            self.project_selector.mapToGlobal(
                QPoint(0, self.project_selector.height())
            )
        )

    def _project_menu_row(self, menu, index, project, active):
        row_widget = QWidget(menu)
        row_widget.setObjectName("ProjectMenuRow")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(2)

        name = str(getattr(project, "name", "Project") or "Project")
        select_button = ActionButton(
            text=f"✓  {name}" if active else f"    {name}",
            presentation=ButtonPresentation.DEFAULT,
            object_name="ProjectMenuSelectButton",
            parent=row_widget,
        )
        select_button.setAutoRaise(True)
        select_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        select_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        select_button.setMinimumWidth(180)
        path = getattr(project, "path", None)
        select_button.setToolTip(str(path or name))
        select_button.clicked.connect(
            lambda _checked=False, target=index: self._choose_project(menu, target)
        )
        row.addWidget(select_button, 1)

        close_button = ActionButton(
            text="−",
            presentation=ButtonPresentation.DEFAULT,
            object_name="ProjectMenuCloseButton",
            parent=row_widget,
        )
        close_button.setAutoRaise(True)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setFixedSize(26, 26)
        close_button.setEnabled(not self._is_placeholder_project(index))
        close_button.setToolTip(f"Close {name}")
        close_button.clicked.connect(
            lambda _checked=False, target=index: self._request_project_close(
                menu,
                target,
            )
        )
        row.addWidget(close_button)
        return row_widget

    def _choose_project(self, menu, index):
        menu.close()
        self._select_project(index)

    def _request_project_close(self, menu, index):
        menu.close()
        self.project_close_requested.emit(int(index))

    def _select_project(self, index):
        setter = getattr(self.store, "set_active_project", None)
        if not callable(setter):
            return
        self.tabs.setCurrentIndex(0)
        setter(int(index))

    def _filter(self, text):
        if self.stack.currentWidget() is self.tree:
            self.tree.set_filter_text(text)

    def _expand(self):
        self.stack.currentWidget().expandAll()

    def _collapse(self):
        self.stack.currentWidget().collapseAll()

    @staticmethod
    def _small_button(text):
        button = ActionButton(text=text, presentation=ButtonPresentation.DEFAULT)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(28, 28)
        return button
