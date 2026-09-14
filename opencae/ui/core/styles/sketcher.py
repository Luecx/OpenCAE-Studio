"""Theme rules for the parametric Sketcher workspace."""


def css(p):
    return f"""
    QDialog#SketchFeatureDialog {{
        background: {p['window']};
    }}
    QWidget#SketchRibbonHost {{
        background: {p['panel']};
        border-bottom: 1px solid {p['border']};
    }}
    QWidget#SketchViewportHost {{
        background: {p['viewport']};
    }}
    QFrame#SketchInspector {{
        background: {p['panel']};
        border-left: 1px solid {p['border']};
    }}
    QLabel#SketchInspectorHeading {{
        color: {p['muted']};
        font-weight: 600;
        padding-top: 3px;
    }}
    QLabel#SketchAxisNote {{
        color: {p['muted']};
        background: {p['panel_alt']};
        border: 1px solid {p['border']};
        border-radius: 3px;
        padding: 7px;
    }}
    QLabel#SketchStatus {{
        color: {p['muted']};
        font-weight: 600;
    }}
    QLabel#SketchStatus[state="ok"] {{
        color: {p['success']};
    }}
    QLabel#SketchStatus[state="error"] {{
        color: {p['danger']};
    }}
    QLabel#SketchHint {{
        color: {p['muted']};
    }}
    QLabel#SketchPreviewNotice {{
        color: {p['warning']};
        background: {p['warning_dim']};
        border-bottom: 1px solid {p['border']};
        padding: 8px;
    }}
    QListWidget#SketchConstraintList {{
        background: {p['input']};
        border: 1px solid {p['border']};
    }}
    QListWidget#SketchConstraintList::item:selected {{
        background: {p['selection']};
        color: {p['selection_text']};
    }}
    """
