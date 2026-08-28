def css(p):
    return f"""
    QDockWidget {{
        color: {p['text']};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {p['panel_alt']};
        padding: 8px;
        border-bottom: 1px solid {p['border']};
        text-align: left;
    }}
    QWidget#WorkspaceSurface,
    QWidget[workspaceSurface="true"] {{
        background: {p['panel']};
        border: none;
    }}
    QWidget#WorkspaceSurface > QWidget,
    QWidget#WorkspaceSurface > QFrame {{
        background: transparent;
    }}
    QFrame#TimeManagerSidebar {{
        background: transparent;
        border: none;
    }}
    QLabel#PanelTitle {{
        font-size: 13pt;
        font-weight: 600;
        color: {p['text']};
        padding: 4px 2px 8px 2px;
    }}
    QLabel#SectionTitle {{
        color: {p['accent']};
        font-size: 8pt;
        font-weight: 600;
        letter-spacing: 1px;
        padding-top: 7px;
    }}
    QLabel#MutedLabel {{ color: {p['muted']}; }}
    """
