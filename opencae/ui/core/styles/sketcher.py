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
    QToolBar#SketchToolbar {{
        background: transparent;
        border: none;
        spacing: 2px;
    }}
    QToolBar#SketchToolbar QToolButton {{
        min-width: 54px;
        padding: 5px 7px;
        border-radius: 3px;
    }}
    QToolBar#SketchToolbar QToolButton:checked {{
        background: {p['accent_dim']};
        color: {p['text']};
        border-bottom: 2px solid {p['accent']};
    }}
    QDialog#SketchFeatureDialog QToolButton:checked {{
        background: {p['accent_dim']};
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
    QWidget#SketchFooter {{
        background: {p['panel']};
        border-top: 1px solid {p['border']};
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
