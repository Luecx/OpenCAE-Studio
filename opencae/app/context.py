from dataclasses import dataclass
from opencae.solvers.registry import available_solvers
from opencae.store.app_settings import AppSettings
from opencae.store.multi_project_store import MultiProjectStore


@dataclass
class AppContext:
    store: MultiProjectStore
    settings: AppSettings
    solvers: dict

    @classmethod
    def create(cls):
        return cls(MultiProjectStore(), AppSettings(), available_solvers())
