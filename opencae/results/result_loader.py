"""Dispatch stored-result operations by source format without cross-format merging."""

from pathlib import Path

from .frd_loader import FrdLoader
from .res_loader import ResLoader


class ResultLoader:
    """Load either FRD or standalone FEMaster RES results."""

    def __init__(self):
        self._frd = FrdLoader()
        self._res = ResLoader()

    def loader_for(self, path):
        suffix = Path(path).suffix.lower()
        if suffix == ".frd":
            return self._frd
        if suffix == ".res":
            return self._res
        raise ValueError(
            f"Unsupported result format '{Path(path).suffix or '<none>'}'. "
            "Open an .frd or .res file."
        )

    def read(self, path):
        return self.loader_for(path).read(path)

    def fields(self, path):
        return self.loader_for(path).fields(path)

    def scalar_range(self, path, field):
        return self.loader_for(path).scalar_range(path, field)

    def pyvista_grid(self, path, step_id=None, frame_id=None):
        return self.loader_for(path).pyvista_grid(path, step_id, frame_id)

    def model_path(self, path):
        method = getattr(self.loader_for(path), "model_path", None)
        return method(path) if callable(method) else None

    def model_project(self, path):
        method = getattr(self.loader_for(path), "project", None)
        return method(path) if callable(method) else None

    def element_id_map(self, path):
        method = getattr(self.loader_for(path), "element_id_map", None)
        return dict(method(path)) if callable(method) else {}
