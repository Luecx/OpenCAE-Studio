"""Thread-safety regressions for the centralized Gmsh session lifecycle."""

from __future__ import annotations

import signal
import sys
from threading import Thread
from types import SimpleNamespace

from opencae.geometry.gmsh_session import gmsh_model


def test_gmsh_initialization_avoids_python_signals_in_worker_thread(monkeypatch):
    """A fresh Gmsh session must initialize successfully outside the main thread."""
    state = {"initialized": False, "interruptible": []}

    def initialize(*, interruptible=True):
        state["interruptible"].append(interruptible)
        if interruptible:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        state["initialized"] = True

    def finalize():
        state["initialized"] = False

    gmsh = SimpleNamespace(
        isInitialized=lambda: state["initialized"],
        initialize=initialize,
        finalize=finalize,
        clear=lambda: None,
        model=SimpleNamespace(add=lambda _name: None),
        option=SimpleNamespace(setNumber=lambda _name, _value: None),
    )
    monkeypatch.setitem(sys.modules, "gmsh", gmsh)
    errors = []

    def open_session():
        try:
            with gmsh_model("worker-model"):
                pass
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    worker = Thread(target=open_session)
    worker.start()
    worker.join(timeout=2.0)

    assert not worker.is_alive()
    assert errors == []
    assert state["interruptible"] == [False]
    assert state["initialized"] is False
