def css(p):
    return f"""
    QToolBar#RibbonHost {{
        background: {p['panel']};
        border: none;
        border-bottom: 1px solid {p['border']};
        spacing: 0;
        padding: 0;
    }}
    QToolBar#RibbonHost::separator {{ width: 0; }}
    QGroupBox {{
        border: 1px solid {p['border']};
        border-radius: 3px;
        margin-top: 10px;
        padding-top: 8px;
        background: {p['panel']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {p['muted']};
    }}
    QStatusBar {{ background: {p['panel']}; border-top: 1px solid {p['border']}; }}
    QStatusBar::item {{ border: none; }}
    QWidget#WorkspaceStatusTabs {{
        background: transparent;
        border: none;
    }}
    QToolButton[workspaceStatusTab="true"] {{
        min-height: 24px;
        padding: 4px 11px 3px 11px;
        margin: 0px;
        color: {p['muted']};
        background: transparent;
        border: none;
        border-top: 2px solid transparent;
        border-radius: 0px;
    }}
    QToolButton[workspaceStatusTab="true"]:hover {{
        color: {p['text']};
        background: {p['panel_hover']};
    }}
    QToolButton[workspaceStatusTab="true"]:checked {{
        color: {p['text']};
        background: {p['panel']};
        border-top: 2px solid {p['accent']};
    }}
    QLabel#WorkspaceFrameSummary {{
        padding: 0px 12px;
        color: {p['muted']};
        background: transparent;
        border: none;
    }}
    QToolButton#UnitSystemStatus {{
        border: none; border-left: 1px solid {p['border']}; border-radius: 0;
        padding: 3px 12px; color: {p['muted']}; background: transparent;
    }}
    QToolButton#UnitSystemStatus:hover {{ color: {p['text']}; background: {p['panel_hover']}; }}
    QListWidget#PreferencesNavigation {{
        background: {p['panel_alt']}; border: 1px solid {p['border']}; padding: 6px;
        outline: none;
    }}
    QListWidget#PreferencesNavigation::item {{
        min-height: 34px; padding: 4px 10px; color: {p['muted']}; border-left: 3px solid transparent;
    }}
    QListWidget#PreferencesNavigation::item:hover {{ background: {p['panel_hover']}; color: {p['text']}; }}
    QListWidget#PreferencesNavigation::item:selected {{
        background: {p['accent_dim']}; color: {p['text']}; border-left-color: {p['accent']};
    }}
    /* Native dock title bars now provide the grab target. Separators can stay
       visually slim, matching the divider beside the project browser. */
    QMainWindow::separator {{
        width: 3px;
        height: 3px;
        background: {p['border']};
    }}
    QMainWindow::separator:hover {{ background: {p['border_light']}; }}
    QSplitter::handle {{ background: {p['border']}; }}
    QLabel#MutedText {{ color: {p['muted']}; }}
    QDialogButtonBox {{ background: transparent; }}
    """
