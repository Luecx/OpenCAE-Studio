from __future__ import annotations


class UnitManager:
    """Resolve all displayed project units from the active project unit system.

    The manager deliberately does not cache the UnitSystem. Project settings can
    change at runtime, so every lookup resolves the system currently selected by
    the project through AppSettings.
    """

    def __init__(self, store, settings):
        self.store = store
        self.settings = settings

    @property
    def system(self):
        return self.settings.unit_system(self.store.project.unit_system)

    def symbol(self, quantity: str) -> str:
        return self.system.symbol(quantity)

    def suffix(self, quantity: str) -> str:
        symbol = self.symbol(quantity)
        return f" {symbol}" if symbol else ""

    def label(self, text: str, quantity: str) -> str:
        symbol = self.symbol(quantity)
        return f"{text} [{symbol}]" if symbol else text
