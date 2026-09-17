from PyQt6.QtCore import QEvent, Qt


def handle_seed_label_event(viewport, watched, event):
    if watched is not viewport.plotter.interactor:
        return False
    if event.type() != QEvent.Type.MouseButtonPress:
        return False
    label = viewport.scene.seed_overlay.nearest(
        viewport.plotter.renderer,
        int(event.position().x()), int(event.position().y()), watched.height(),
    )
    if not label or event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
        return False
    delta = 1 if event.button() == Qt.MouseButton.LeftButton else -1
    viewport.seed_adjust_requested.emit(label, delta)
    return True
