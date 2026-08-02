from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon


def icon_path() -> Path:
    suffix = ".ico" if sys.platform == "win32" else ".png"
    return Path(__file__).resolve().parents[1] / "ui" / "assets" / f"opencae_studio{suffix}"


def application_icon() -> QIcon:
    return QIcon(str(icon_path()))


def set_windows_app_id() -> None:
    if sys.platform != "win32": return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OpenCAE.Studio")
    except (AttributeError, OSError):
        pass
