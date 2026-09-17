from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ElementControlPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(3)
        self.summary = QLabel("Select a topology."); self.summary.setWordWrap(True); self.details = QLabel(); self.details.setObjectName("FieldHint"); self.details.setWordWrap(True)
        layout.addWidget(self.summary); layout.addWidget(self.details)

    def set_preview(self, preview, order):
        if preview is None: self.summary.setText("Select a topology."); self.details.clear(); return
        self.summary.setText(f"Selected elements: {len(preview.selected):,}\nAdditional neighboring elements: {preview.additional:,}\nTotal affected elements: {len(preview.affected):,}")
        groups = ", ".join(f"{count:,} × {name}" for name, count in preview.additional_by_topology.items())
        note = "Shared shell edges and solid faces must use one interpolation order."
        if order and str(order) == "Second": note += " Neighboring elements will be converted automatically on Apply."
        self.details.setText((groups + "\n" if groups else "") + note)
