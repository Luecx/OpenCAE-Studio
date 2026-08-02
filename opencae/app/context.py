from dataclasses import dataclass
from opencae.solvers.registry import available_solvers
from opencae.store.app_settings import AppSettings
from opencae.store.project_store import ProjectStore

@dataclass
class AppContext:
    store: ProjectStore
    settings: AppSettings
    solvers: dict

    @classmethod
    def create(cls): return cls(ProjectStore(),AppSettings(),available_solvers())
