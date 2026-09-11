"""Curated Settings-page exports."""

from .appearance_page import AppearancePage
from .files_page import FilesPage
from .general_page import GeneralPage
from .geometry_page import GeometryPage
from .input_decks_page import InputDecksPage
from .meshing_page import MeshingPage
from .navigation import PreferencesNavigation
from .results_page import ResultsPage
from .solvers_page import SolversPage
from .unit_systems_page import UnitSystemsPage
from .viewport_page import ViewportPage

__all__ = [
    "AppearancePage",
    "FilesPage",
    "GeneralPage",
    "GeometryPage",
    "InputDecksPage",
    "MeshingPage",
    "PreferencesNavigation",
    "ResultsPage",
    "SolversPage",
    "UnitSystemsPage",
    "ViewportPage",
]
