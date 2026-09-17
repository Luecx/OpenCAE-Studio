"""Optional FreeSpacenav/libspnav bridge integrated with Qt's event loop."""

from __future__ import annotations

import ctypes
from ctypes.util import find_library

from PyQt6.QtCore import QObject, QSocketNotifier, pyqtSignal


SPNAV_EVENT_MOTION = 1
SPNAV_EVENT_BUTTON = 2


class _MotionEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("z", ctypes.c_int),
        ("rx", ctypes.c_int),
        ("ry", ctypes.c_int),
        ("rz", ctypes.c_int),
        ("period", ctypes.c_uint),
        ("data", ctypes.POINTER(ctypes.c_int)),
    ]


class _ButtonEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("press", ctypes.c_int),
        ("bnum", ctypes.c_int),
    ]


class _SpnavEvent(ctypes.Union):
    _fields_ = [
        ("type", ctypes.c_int),
        ("motion", _MotionEvent),
        ("button", _ButtonEvent),
    ]


class SpaceNavInput(QObject):
    """Read 6-DoF motion from a running spacenavd daemon when available."""

    motion = pyqtSignal(object)
    button = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._library = None
        self._notifier = None
        self._open = False
        self._connect()

    @property
    def available(self) -> bool:
        return self._open and self._notifier is not None

    def close(self) -> None:
        notifier = self._notifier
        self._notifier = None
        if notifier is not None:
            notifier.setEnabled(False)
            notifier.deleteLater()
        if self._library is not None and self._open:
            try:
                self._library.spnav_close()
            except (AttributeError, OSError):
                pass
        self._open = False

    def _connect(self) -> None:
        library = _load_library()
        if library is None:
            return
        try:
            _configure_api(library)
            if int(library.spnav_open()) == -1:
                return
            self._open = True
            self._library = library
            try:
                library.spnav_client_name(b"OpenCAE Studio")
            except (AttributeError, OSError):
                pass
            fd = int(library.spnav_fd())
            if fd < 0:
                self.close()
                return
            self._notifier = QSocketNotifier(fd, QSocketNotifier.Type.Read, self)
            self._notifier.activated.connect(self._poll)
        except (AttributeError, OSError, TypeError, ValueError):
            self._library = library
            self.close()

    def _poll(self, *_args) -> None:
        library = self._library
        if library is None:
            return
        event = _SpnavEvent()
        try:
            while int(library.spnav_poll_event(ctypes.byref(event))):
                if event.type == SPNAV_EVENT_MOTION:
                    motion = event.motion
                    # Match the conventional CAD coordinate mapping used by
                    # FreeCAD/libspnav: device Y/Z become view Z/Y respectively.
                    self.motion.emit(
                        (
                            -float(motion.x),
                            -float(motion.z),
                            -float(motion.y),
                            -float(motion.rx),
                            -float(motion.rz),
                            -float(motion.ry),
                            int(motion.period),
                        )
                    )
                elif event.type == SPNAV_EVENT_BUTTON:
                    self.button.emit(
                        int(event.button.bnum),
                        bool(event.button.press),
                    )
        except (OSError, TypeError, ValueError):
            self.close()


def _load_library():
    names = []
    discovered = find_library("spnav")
    if discovered:
        names.append(discovered)
    names.extend(("libspnav.so.0", "libspnav.so", "libspnav.dylib"))
    for name in names:
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    return None


def _configure_api(library) -> None:
    library.spnav_open.argtypes = []
    library.spnav_open.restype = ctypes.c_int
    library.spnav_close.argtypes = []
    library.spnav_close.restype = ctypes.c_int
    library.spnav_fd.argtypes = []
    library.spnav_fd.restype = ctypes.c_int
    library.spnav_poll_event.argtypes = [ctypes.POINTER(_SpnavEvent)]
    library.spnav_poll_event.restype = ctypes.c_int
    if hasattr(library, "spnav_client_name"):
        library.spnav_client_name.argtypes = [ctypes.c_char_p]
        library.spnav_client_name.restype = ctypes.c_int
