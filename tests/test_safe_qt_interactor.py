import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from PyQt6.QtCore import QPointF, Qt


class _Base:
    def __init__(self, *_args, **kwargs):
        self.kwargs = kwargs
        self.render_count = 0
        self.mouse_presses = []
        self.mouse_moves = []
        self.mouse_releases = []

    def render(self):
        self.render_count += 1

    def mousePressEvent(self, event):
        self.mouse_presses.append(event)

    def mouseMoveEvent(self, event):
        self.mouse_moves.append(event)

    def mouseReleaseEvent(self, event):
        self.mouse_releases.append(event)


class _MouseEvent:
    def __init__(
        self,
        x,
        y,
        *,
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.NoButton,
    ):
        self._position = QPointF(float(x), float(y))
        self._button = button
        self._buttons = buttons
        self.accepted = False

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def position(self):
        return self._position

    def globalPosition(self):
        return self._position

    def modifiers(self):
        return Qt.KeyboardModifier.NoModifier

    def accept(self):
        self.accepted = True


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


def test_left_rotation_starts_only_after_click_drag_threshold():
    cls = _load()
    interactor = cls()

    press = _MouseEvent(
        10,
        10,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    interactor.mousePressEvent(press)
    assert press.accepted
    assert interactor.mouse_presses == []

    jitter = _MouseEvent(13, 10, buttons=Qt.MouseButton.LeftButton)
    interactor.mouseMoveEvent(jitter)
    assert jitter.accepted
    assert interactor.mouse_presses == []
    assert interactor.mouse_moves == []

    drag = _MouseEvent(15, 10, buttons=Qt.MouseButton.LeftButton)
    interactor.mouseMoveEvent(drag)
    assert len(interactor.mouse_presses) == 1
    assert interactor.mouse_presses[0].button() == Qt.MouseButton.LeftButton
    assert len(interactor.mouse_moves) == 1

    release = _MouseEvent(15, 10, button=Qt.MouseButton.LeftButton)
    interactor.mouseReleaseEvent(release)
    assert len(interactor.mouse_releases) == 1


def test_stationary_left_click_never_enters_vtk_rotation_state():
    cls = _load()
    interactor = cls()

    interactor.mousePressEvent(
        _MouseEvent(
            20,
            20,
            button=Qt.MouseButton.LeftButton,
            buttons=Qt.MouseButton.LeftButton,
        )
    )
    release = _MouseEvent(22, 20, button=Qt.MouseButton.LeftButton)
    interactor.mouseReleaseEvent(release)

    assert release.accepted
    assert interactor.mouse_presses == []
    assert interactor.mouse_moves == []
    assert interactor.mouse_releases == []
