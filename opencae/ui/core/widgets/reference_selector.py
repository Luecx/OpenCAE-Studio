"""Compatibility export for the canonical reference-selector composite.

The canonical control keeps the explicit callback protocol
``callback(self.window(), self._apply_created)``; this facade intentionally owns
no implementation of that behavior.
"""

from opencae.ui.composites.controls.control_reference_selector import ControlReferenceSelector

ReferenceSelector = ControlReferenceSelector

__all__ = ["ReferenceSelector"]
