from pyvistaqt import QtInteractor


class SafeQtInteractor(QtInteractor):
    """QtInteractor with explicit application-owned rendering cadence.

    The pinned PyVistaQt QOpenGLWidget bridge owns the GL context and marshals
    ``render()`` through its Qt signal into the GUI thread. OpenCAE therefore no
    longer bypasses that integration by calling ``vtkRenderWindow.Render()``
    directly. We only disable PyVistaQt's periodic auto-render timer; viewport
    refreshes remain driven by OpenCAE's own batching/update logic.
    """

    def __init__(self, *args, **kwargs):
        kwargs["auto_update"] = False
        super().__init__(*args, **kwargs)
