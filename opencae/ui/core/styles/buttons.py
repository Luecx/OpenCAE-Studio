def css(p):
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
        padding: 4px 3px 3px 3px;
        color: {p['text']};
    }}
    QToolButton[ribbonButton="true"]:hover {{
        background: {p['panel_hover']};
        border: 1px solid {p['border_light']};
    }}
    """
