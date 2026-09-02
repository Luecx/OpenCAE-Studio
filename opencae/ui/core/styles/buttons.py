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
    QToolButton#ProjectionToggle {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
        padding: 3px 8px;
    }}
    QToolButton#ProjectionToggle:hover,
    QToolButton#ProjectionToggle:pressed {{
        background: {p['panel_hover']};
        border-color: {p['border_light']};
    }}
    QToolButton#TimeManagerControl {{
        background: transparent;
        border: none;
        border-radius: 3px;
        padding: 0px;
    }}
    QToolButton#TimeManagerControl:hover {{
        background: {p['panel_hover']};
        border: none;
    }}
    QToolButton#TimeManagerControl:pressed,
    QToolButton#TimeManagerControl:checked {{
        background: {p['accent_dim']};
        border: none;
    }}
    QToolButton#TimeManagerControl:disabled {{
        background: transparent;
        border: none;
    }}
    QToolButton[ribbonButton="true"] {{
        background: transparent;
        border: 1px solid transparent;
        padding: 2px 3px 1px 3px;
        color: {p['text']};
    }}
    QToolButton[ribbonButton="true"]:hover {{
        background: {p['panel_hover']};
        border: 1px solid {p['border_light']};
    }}
    /* Persistent display toggles on Results need a readable but still flat
       active state.  A small lift from the ribbon surface is enough; keep the
       accent outline so Mesh Lines / Boundary remain immediately legible. */
    QToolButton[resultsRibbonButton="true"] {{
        background: transparent;
    }}
    QToolButton[resultsRibbonButton="true"]:checked {{
        background: {p['panel_active']};
        border-color: {p['accent']};
    }}
    QToolButton[resultsRibbonButton="true"]:hover {{
        background: {p['panel_hover']};
    }}
    QToolButton[resultsRibbonButton="true"]:checked:hover {{
        background: {p['panel_hover']};
        border-color: {p['accent_hover']};
    }}
    QToolButton[ribbonButton="true"]::menu-button {{
        width: 16px;
        background: transparent;
        border: none;
    }}
    QToolButton[ribbonButton="true"]::menu-indicator {{
        subcontrol-origin: padding;
        subcontrol-position: bottom right;
        right: 3px;
        bottom: 3px;
    }}
    """
