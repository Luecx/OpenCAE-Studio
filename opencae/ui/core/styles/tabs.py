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

    /* Browser Project/Solution is a standalone tab bar. */
    QTabBar#BrowserTabBar {{
        background: {p['panel']};
        border: none;
        qproperty-drawBase: false;
    }}
    QTabBar#BrowserTabBar::tab {{
        background: {p['panel']};
        color: {p['muted']};
        padding: 7px 12px;
        margin: 0px;
        border: none;
        border-bottom: 2px solid transparent;
    }}
    QTabBar#BrowserTabBar::tab:selected {{
        background: {p['panel']};
        color: {p['text']};
        border-bottom: 2px solid {p['accent']};
    }}
    QTabBar#BrowserTabBar::tab:hover:!selected {{
        background: {p['panel_hover']};
        color: {p['text']};
    }}
    QToolButton#ProjectSelectorButton {{
        background: transparent;
        color: {p['muted']};
        border: none;
        padding: 0px;
        margin: 0px;
    }}
    QToolButton#ProjectSelectorButton:hover {{
        background: {p['panel_hover']};
        color: {p['text']};
    }}
    QMenu#ProjectSelectorMenu {{
        background: {p['panel']};
        color: {p['text']};
        border: 1px solid {p['border']};
        padding: 3px;
    }}
    QWidget#ProjectMenuRow {{
        background: transparent;
    }}
    QToolButton#ProjectMenuSelectButton {{
        background: transparent;
        color: {p['text']};
        border: none;
        text-align: left;
        padding: 5px 8px;
    }}
    QToolButton#ProjectMenuSelectButton:hover {{
        background: {p['panel_hover']};
    }}
    QToolButton#ProjectMenuCloseButton {{
        background: transparent;
        color: {p['muted']};
        border: none;
        padding: 0px;
    }}
    QToolButton#ProjectMenuCloseButton:hover {{
        background: {p['panel_hover']};
        color: {p['text']};
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
