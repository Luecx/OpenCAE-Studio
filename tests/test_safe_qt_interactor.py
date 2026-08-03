import importlib.util
import sys
from pathlib import Path
from types import ModuleType


class _Window:
    def __init__(self): self.count = 0
    def Render(self): self.count += 1


class _Base:
    def __init__(self, *_args, **kwargs): self.kwargs = kwargs; self.ren_win = _Window(); self._closed = False
    def GetRenderWindow(self): return self.ren_win


def _load():
    fake = ModuleType("pyvistaqt"); fake.QtInteractor = _Base
    previous = sys.modules.get("pyvistaqt"); sys.modules["pyvistaqt"] = fake
    try:
        path = Path(__file__).parents[1] / "opencae/ui/viewport/safe_qt_interactor.py"
        spec = importlib.util.spec_from_file_location("safe_qt_interactor_test", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module.SafeQtInteractor
    finally:
        if previous is None: sys.modules.pop("pyvistaqt", None)
        else: sys.modules["pyvistaqt"] = previous


def test_safe_interactor_disables_timer_and_uses_native_vtk_render():
    cls = _load(); interactor = cls(auto_update=10)
    assert interactor.kwargs["auto_update"] is False
    interactor.render(); interactor._render()
    assert interactor.ren_win.count == 2
