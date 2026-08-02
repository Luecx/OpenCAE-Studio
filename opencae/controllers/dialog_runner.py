from __future__ import annotations
from PyQt6.QtWidgets import QDialog

def get_values(dialog: QDialog):
    return dialog.values() if dialog.exec() == QDialog.DialogCode.Accepted else None
