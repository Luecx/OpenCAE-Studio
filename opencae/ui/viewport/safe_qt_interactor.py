from pyvistaqt import QtInteractor

from opencae.ui.core.theme import PALETTE


class SafeQtInteractor(QtInteractor):
    """QtInteractor that renders through VTK without PyVista's render hook."""

    def __init__(self, *args, **kwargs):
        kwargs["auto_update"] = False
        super().__init__(*args, **kwargs)

    def set_background(self, color=None, top=None, all_renderers=True):
        """Apply the application viewport token as a subtle two-tone gradient."""
        if top is None and color == PALETTE["viewport"]:
            color = PALETTE["viewport_bottom"]
            top = PALETTE["viewport_top"]
        return super().set_background(
            color=color,
            top=top,
            all_renderers=all_renderers,
        )

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
