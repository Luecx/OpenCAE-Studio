from PyQt6.QtWidgets import QPlainTextEdit
class LogPanel(QPlainTextEdit):
    def __init__(self,parent=None): super().__init__(parent); self.setReadOnly(True)
    def append_message(self,message): self.appendPlainText(message)
