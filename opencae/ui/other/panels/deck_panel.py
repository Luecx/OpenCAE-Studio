from PyQt6.QtWidgets import QPlainTextEdit
class DeckPanel(QPlainTextEdit):
    def __init__(self,parent=None): super().__init__(parent); self.setReadOnly(True); self.setPlainText('Input deck preview will appear here.')
