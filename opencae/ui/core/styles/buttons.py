"""Return application button stylesheet fragments."""


def css(p):
    """Build shared QPushButton and QToolButton rules from the active palette."""
    return f"""
    QPushButton {{
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        padding: 6px 10px;
        border-radius: 3px;
    }}
    QPushButton:hover {{ background: {p['panel_hover']}; border-color: {p['accent']}; }}
    QPushButton:pressed {{ background: {p['accent_dim']}; }}
    QPushButton#PrimaryButton {{
        background: {p['accent']};
        border-color: {p['accent']};
        color: white;
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{ background: {p['accent_hover']}; }}
    QPushButton#InlinePickButton:checked, QPushButton#ContextPickButton:checked {{
        background: {p['accent_dim']};
        border-color: {p['accent']};
        color: {p['text']};
        font-weight: 600;
    }}
    QPushButton#XYZPickButton {{
        min-width: 34px; max-width: 34px;
        min-height: 34px; max-height: 34px;
        padding: 0px;
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        border-left: 0px;
        border-radius: 0px;
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    QPushButton#XYZPickButton:hover {{
        background: {p['panel_hover']};
        border-color: {p['accent']};
    }}
    QPushButton#XYZPickButton:checked {{
        background: {p['accent_dim']};
        border-color: {p['accent']};
    }}
    QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
    }}
    QToolButton:hover {{ background: {p['panel_hover']}; border-color: {p['border_light']}; }}
    QToolButton:pressed, QToolButton:checked {{
        background: {p['accent_dim']};
        border-color: {p['accent']};
    }}
    QToolButton[ribbonButton="true"] {{
        padding: 2px 3px 1px 3px;
        color: {p['text']};
    }}
    QToolButton[ribbonButton="true"]:hover {{
        background: {p['panel_hover']};
        border: 1px solid {p['border_light']};
    }}
    """
