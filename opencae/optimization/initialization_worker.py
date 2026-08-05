"""Builds topology mesh and sparse operators outside the GUI thread."""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .validation import validate_topology_optimization


class TopologyInitializationWorker(QObject):
    """Worker that validates a topology setup and constructs immutable run data."""

    ready = pyqtSignal(object, object, object)
    failed = pyqtSignal(str)
    done = pyqtSignal()

    def __init__(self, project, optimization_id):
        super().__init__()
        self.project = project
        self.optimization_id = optimization_id

    @pyqtSlot()
    def run(self):
        try:
            optimization = self.project.try_resolve(self.optimization_id)
            if optimization is None:
                raise ValueError("The topology optimization no longer exists")
            errors, index, masks, operators = validate_topology_optimization(
                self.project,
                optimization,
                build_operators=True,
            )
            if errors:
                raise ValueError("\n".join(errors))
            self.ready.emit(index, masks, operators)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()
