"""Run CPU or file-I/O work outside the Qt GUI thread."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PyQt6.QtCore import QThread, Qt, pyqtSignal, pyqtSlot


_LOG = logging.getLogger(__name__)


class BackgroundTask(QThread):
    """Execute one callable on a worker thread and marshal callbacks to Qt's GUI thread."""

    result_ready = pyqtSignal(object)
    error_ready = pyqtSignal(object)
    settled = pyqtSignal()

    def __init__(
        self,
        operation: Callable[[], object],
        *,
        on_result: Callable[[object], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._operation = operation
        self._on_result = on_result
        self._on_error = on_error
        self._delivered = False
        self._thread_finished = False

        queued = Qt.ConnectionType.QueuedConnection
        self.result_ready.connect(self._deliver_result, queued)
        self.error_ready.connect(self._deliver_error, queued)
        self.finished.connect(self._mark_thread_finished, queued)

    def run(self) -> None:
        """Perform the expensive callable on this QThread's worker context."""
        try:
            result = self._operation()
        except Exception as exc:
            self.error_ready.emit(exc)
        else:
            self.result_ready.emit(result)

    @pyqtSlot(object)
    def _deliver_result(self, result) -> None:
        """Invoke the success callback on the object's owning Qt thread."""
        try:
            if self._on_result is not None:
                self._on_result(result)
        except Exception:
            _LOG.exception("Background task result callback failed")
        finally:
            self._delivered = True
            self.settled.emit()
            self._cleanup_if_done()

    @pyqtSlot(object)
    def _deliver_error(self, error) -> None:
        """Invoke the failure callback on the object's owning Qt thread."""
        try:
            if self._on_error is not None:
                self._on_error(error)
            else:
                _LOG.error("Background task failed: %s", error)
        except Exception:
            _LOG.exception("Background task error callback failed")
        finally:
            self._delivered = True
            self.settled.emit()
            self._cleanup_if_done()

    @pyqtSlot()
    def _mark_thread_finished(self) -> None:
        self._thread_finished = True
        self._cleanup_if_done()

    def _cleanup_if_done(self) -> None:
        if self._delivered and self._thread_finished:
            self.deleteLater()
