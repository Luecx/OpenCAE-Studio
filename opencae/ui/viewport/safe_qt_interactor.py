from pyvistaqt import QtInteractor


class SafeQtInteractor(QtInteractor):
    """QtInteractor that renders through VTK without PyVista's render hook."""

    def __init__(self, *args, **kwargs):
        kwargs["auto_update"] = False
        super().__init__(*args, **kwargs)

    def _render(self, *_args, **_kwargs):
        self._native_render()

    def render(self):
        self._native_render()

    def _native_render(self):
        if self.__dict__.get("_closed", False):
            return
        self.__dict__["_rendered"] = True
        window = self.__dict__.get("ren_win")
        if window is None:
            try:
                window = self.GetRenderWindow()
            except (AttributeError, RuntimeError, RecursionError):
                return
        try:
            window.Render()
        except (AttributeError, RuntimeError, RecursionError):
            return
