"""Styles reusable editor headings, separators, and read-only value fields."""


def css(p):
    """Return QSS for semantic editor presentation components."""
    return f"""
    QLabel#EditorSectionHeading {{
        color: {p['text']};
        font-weight: 600;
        font-size: 10.5pt;
        border-left: 3px solid {p['accent']};
        padding-left: 8px;
        min-height: 20px;
    }}

    QFrame#EditorVerticalSeparator {{
        color: {p['border']};
        background: {p['border']};
        border: none;
        min-width: 1px;
        max-width: 1px;
    }}

    QWidget#ReadOnlyValue {{
        background: transparent;
        border: none;
    }}
    QLabel#ReadOnlyValueText,
    QLabel#ReadOnlyValueTextWithUnit {{
        background: {p['panel_alt']};
        color: {p['text']};
        border: 1px solid {p['border_light']};
        border-radius: 3px;
        padding: 0px 10px;
    }}
    QLabel#ReadOnlyValueTextWithUnit {{
        border-top-right-radius: 0px;
        border-bottom-right-radius: 0px;
        border-right: 0px;
    }}
    QLabel#ReadOnlyValueUnit {{
        min-width: 54px;
        padding: 0px 10px;
        background: {p['panel_alt']};
        color: {p['muted']};
        border: 1px solid {p['border_light']};
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    """
