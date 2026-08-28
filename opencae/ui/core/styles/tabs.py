def css(p):
    return f"""
    QTabWidget::pane {{
        border: none;
        background: {p['panel']};
    }}
    QTabWidget QTabBar {{
        background: {p['panel']};
        border: none;
    }}
    QTabWidget QTabBar::tab {{
        background: {p['panel']};
        padding: 8px 14px;
        border: none;
        border-bottom: 2px solid transparent;
        color: {p['muted']};
    }}
    QTabWidget QTabBar::tab:selected {{
        color: {p['text']};
        background: {p['panel']};
        border-bottom: 2px solid {p['accent']};
    }}
    QTabWidget QTabBar::tab:hover:!selected {{
        color: {p['text']};
        background: {p['panel_hover']};
    }}

    /* QMainWindow creates a standalone QTabBar for tabified docks.  Give the
       lower workspace the same flat navigation language as the ribbon: one
       continuous surface, no native base line, and only an accent underline. */
    QTabBar#WorkspaceTabBar {{
        background: {p['panel']};
        border: none;
        qproperty-drawBase: false;
    }}
    QTabBar#WorkspaceTabBar::tab {{
        background: {p['panel']};
        color: {p['muted']};
        padding: 7px 12px;
        margin: 0px;
        border: none;
        border-bottom: 2px solid transparent;
    }}
    QTabBar#WorkspaceTabBar::tab:selected {{
        background: {p['panel']};
        color: {p['text']};
        border-bottom: 2px solid {p['accent']};
    }}
    QTabBar#WorkspaceTabBar::tab:hover:!selected {{
        background: {p['panel']};
        color: {p['text']};
    }}
    """
