"""Topology runner adapter for the central JobManager contract."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal

from .runner import TopologyOptimizationRunner as _TopologyOptimizationRunner


class TopologyOptimizationRunner(_TopologyOptimizationRunner):
    """Expose topology completion as ``(status, message)``.

    The original iterative runner persists its OptimizationRun internally. The
    central JobManager already captures the run ID when connecting the signal,
    so its public completion contract only needs the final status and message.
    """

    finished = pyqtSignal(str, str)

    def _finish(self, status, message):
        if self._finished_state:
            return
        self._finished_state = True
        if self._log_stream is not None:
            self._log_stream.close()
            self._log_stream = None
        self._update_run(status=status, message=str(message))
        self.progress.emit(str(message))
        self.finished.emit(str(status), str(message))
