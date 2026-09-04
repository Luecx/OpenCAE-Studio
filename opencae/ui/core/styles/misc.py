"""Miscellaneous application stylesheet rules."""

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
    QWidget#WorkspaceStatusTabs {{ background: transparent; border: none; }}
    QToolButton[workspaceStatusTab="true"] {{
        min-height: 24px; padding: 4px 11px 3px 11px; margin: 0px;
        color: {p['muted']}; background: transparent; border: none;
        border-top: 2px solid transparent; border-radius: 0px;
    }}
    QToolButton[workspaceStatusTab="true"]:hover {{ color: {p['text']}; background: {p['panel_hover']}; }}
    QToolButton[workspaceStatusTab="true"]:checked {{
        color: {p['text']}; background: {p['panel']}; border-top: 2px solid {p['accent']};
    }}
    QLabel#WorkspaceFrameSummary {{ padding: 0px 12px; color: {p['muted']}; background: transparent; border: none; }}
    QToolButton#UnitSystemStatus {{
        border: none; border-left: 1px solid {p['border']}; border-radius: 0;
        padding: 3px 12px; color: {p['muted']}; background: transparent;
    }}
    QToolButton#UnitSystemStatus:hover {{ color: {p['text']}; background: {p['panel_hover']}; }}

    QWidget#PreferencesSidebar {{
        background: {p['panel_alt']}; border: none; border-right: 1px solid {p['border']};
    }}
    QLineEdit#PreferencesSearch {{
        min-height: 30px; padding: 0 9px; background: {p['search']}; color: {p['text']};
        border: 1px solid {p['border']}; border-radius: 5px;
    }}
    QLineEdit#PreferencesSearch:focus {{ border-color: {p['border_hover']}; }}
    QListWidget#PreferencesNavigationList {{
        background: transparent; border: none; outline: none; padding: 0px;
    }}
    QListWidget#PreferencesNavigationList::item {{
        padding: 0px 10px; margin: 0px; color: {p['muted']};
        background: transparent; border: none; border-radius: 5px;
    }}
    QListWidget#PreferencesNavigationList::item:hover {{ color: {p['text']}; background: {p['panel_hover']}; }}
    QListWidget#PreferencesNavigationList::item:selected {{
        color: {p['selection_text']}; background: {p['selection']}; border: none;
    }}
    QLabel[preferencesGroupHeader="true"] {{
        color: {p['disabled']}; background: transparent; border: none;
        padding: 8px 8px 2px 8px; font-size: 10px; font-weight: 600;
    }}
    QStackedWidget#PreferencesPageStack {{ background: {p['panel']}; border: none; padding: 0px; }}
    QLabel#PreferencesPageTitle {{
        color: {p['text']}; background: transparent; font-size: 19px; font-weight: 600;
    }}
    QLabel#PreferencesPageDescription {{ color: {p['muted']}; background: transparent; }}

    QMainWindow::separator {{ width: 3px; height: 3px; background: {p['border']}; }}
    QMainWindow::separator:hover {{ background: {p['border_light']}; }}
    QSplitter::handle {{ background: {p['border']}; }}
    QLabel#MutedText {{ color: {p['muted']}; }}
    QDialogButtonBox {{ background: transparent; }}
    """
