def css(p):
    return f"""
    QTabWidget::pane {{
        border: none;
        background: {p['panel']};
    }}
    QTabBar {{
        background: {p['panel']};
        border: none;
    }}
    QTabBar::tab {{
        background: {p['panel']};
        padding: 8px 14px;
        border: none;
        border-bottom: 2px solid transparent;
        color: {p['muted']};
    }}
    QTabBar::tab:selected {{
        color: {p['text']};
        background: {p['panel']};
        border-bottom: 2px solid {p['accent']};
    }}
    QTabBar::tab:hover:!selected {{
        color: {p['text']};
        background: {p['panel_hover']};
    }}
    """