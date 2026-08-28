import importlib.util
import sys
from pathlib import Path
from types import ModuleType


class _Base:
    def __init__(self, *_args, **kwargs):
        self.kwargs = kwargs
        self.render_count = 0

    def render(self):
        self.render_count += 1


def _load():
    fake = ModuleType("pyvistaqt")
    fake.QtInteractor = _Base
    previous = sys.modules.get("pyvistaqt")
    sys.modules["pyvistaqt"] = fake
    try:
        path = Path(__file__).parents[1] / "opencae/ui/viewport/safe_qt_interactor.py"
        spec = importlib.util.spec_from_file_location("safe_qt_interactor_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.SafeQtInteractor
    finally:
        if previous is None:
            sys.modules.pop("pyvistaqt", None)
        else:
            sys.modules["pyvistaqt"] = previous


def test_safe_interactor_disables_timer_and_keeps_upstream_qt_render_dispatch():
    cls = _load()
    interactor = cls(auto_update=10)
    assert interactor.kwargs["auto_update"] is False
    interactor.render()
    assert interactor.render_count == 1
    # The old workaround overrode render/_render and called VTK directly. The
    # QOpenGLWidget bridge must retain PyVistaQt's Qt-thread render dispatch.
    assert "render" not in cls.__dict__
    assert "_render" not in cls.__dict__
