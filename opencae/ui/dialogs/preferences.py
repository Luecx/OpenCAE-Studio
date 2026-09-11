"""Unified multi-page application Settings dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
)

from opencae.ui.preferences import (
    AppearancePage,
    FilesPage,
    GeneralPage,
    GeometryPage,
    InputDecksPage,
    MeshingPage,
    PreferencesNavigation,
    ResultsPage,
    SolversPage,
    UnitSystemsPage,
    ViewportPage,
)
from opencae.ui.templates import dialog_buttons, dialog_layout


class PreferencesDialog(QDialog):
    """Edit all application/workstation settings through one authoritative surface."""

    applied = pyqtSignal(dict)

    def __init__(self, settings, solvers=None, parent=None, initial_page="General"):
        super().__init__(parent)
        self.settings = settings
        self.solvers = dict(solvers or {})
        self.setWindowTitle("Settings")
        self.resize(1120, 760)
        self.setMinimumSize(900, 620)

        root = dialog_layout(self)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.navigation = PreferencesNavigation()
        body.addWidget(self.navigation)

        self.stack = QStackedWidget()
        self.stack.setObjectName("PreferencesPageStack")
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        manager_callback = None
        controllers = getattr(parent, "controllers", None)
        solver_controller = getattr(controllers, "solver", None)
        if solver_controller is not None:
            manager_callback = getattr(solver_controller, "format_manager", None)

        self.general = GeneralPage(settings)
        self.appearance = AppearancePage(settings)
        self.viewport = ViewportPage(settings)
        self.files = FilesPage(settings)
        self.geometry = GeometryPage(settings)
        self.meshing = MeshingPage(settings)
        self.solvers_page = SolversPage(settings)
        self.input_decks = InputDecksPage(
            settings,
            self.solvers,
            manager_callback,
        )
        self.results = ResultsPage(settings)
        self.units = UnitSystemsPage(
            settings.unit_systems,
            settings.selected_unit_system,
        )

        self._pages = {
            "General": self.general,
            "Appearance": self.appearance,
            "Viewport": self.viewport,
            "Files & Projects": self.files,
            "Geometry": self.geometry,
            "Meshing": self.meshing,
            "Solvers": self.solvers_page,
            "Input Decks": self.input_decks,
            "Results": self.results,
            "Unit Systems": self.units,
        }
        search_terms = {
            "General": ("icon", "delete", "destructive", "layout", "restore"),
            "Appearance": ("font", "scale", "interface", "density"),
            "Viewport": ("camera", "projection", "perspective", "parallel", "fit", "viewcube"),
            "Files & Projects": ("directory", "file", "open", "save", "history"),
            "Geometry": ("heal", "sew", "solid", "degenerate", "tolerance", "datum", "reference"),
            "Meshing": ("gmsh", "algorithm", "order", "optimization", "recombine", "threads"),
            "Solvers": ("femaster", "abaqus", "calculix", "executable", "arguments", "backend"),
            "Input Decks": ("profile", "generator", "deck", "format", "keyword"),
            "Results": ("mesh lines", "boundary", "undeformed", "postprocessing"),
            "Unit Systems": ("units", "length", "force", "mass", "temperature"),
        }
        self._hosts = {}
        groups = (
            ("GENERAL", ("General", "Appearance")),
            ("WORKSPACE", ("Viewport", "Files & Projects", "Results")),
            ("MODELING", ("Geometry", "Meshing")),
            ("EXECUTION", ("Solvers", "Input Decks")),
            ("SYSTEM", ("Unit Systems",)),
        )
        for group, titles in groups:
            for title in titles:
                self.navigation.add_page(group, title, search_terms.get(title, ()))
                host = self._scroll_host(self._pages[title])
                self._hosts[title] = host
                self.stack.addWidget(host)

        self.navigation.page_changed.connect(self._show_page)
        self.navigation.select_page(str(initial_page or "General"))

        buttons = dialog_buttons(include_apply=True)
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(lambda: self._apply(close=False))
        buttons.accepted.connect(lambda: self._apply(close=True))
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _scroll_host(page):
        """Wrap one page in a frameless scroll area for smaller displays."""
        host = QScrollArea()
        host.setObjectName("PreferencesPageScroll")
        host.setFrameShape(QFrame.Shape.NoFrame)
        host.setWidgetResizable(True)
        host.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host.setWidget(page)
        return host

    def _show_page(self, title: str) -> None:
        host = self._hosts.get(str(title))
        if host is not None:
            self.stack.setCurrentWidget(host)

    def _apply(self, *, close: bool) -> None:
        """Validate dependent pages and emit one complete settings snapshot."""
        error = self.units.validate()
        if error:
            QMessageBox.warning(self, "Invalid unit systems", error)
            return
        self.applied.emit(self.values())
        if close:
            self.accept()

    def values(self) -> dict[str, object]:
        """Return all application settings without mixing project-owned values in."""
        preference_values: dict[str, object] = {}
        for page in (
            self.general,
            self.appearance,
            self.viewport,
            self.files,
            self.geometry,
            self.meshing,
            self.results,
        ):
            preference_values.update(page.values())
        preference_values.update(self.input_decks.values())

        solver_values = self.solvers_page.values()
        systems, selected_unit = self.units.values()
        return {
            "preferences": preference_values,
            "solver_configs": solver_values["solver_configs"],
            "selected_solver": solver_values["selected_solver"],
            "unit_systems": systems,
            "selected_unit_system": selected_unit,
        }
