def css(p):
    return f"""
    QTabWidget::pane {{
        border: none;
        border-top: 1px solid {p['border']};
        background: {p['panel']};
    }}
    QTabBar::tab {{
        background: {p['panel']};
        padding: 8px 14px;
        border: none;
        border-right: 1px solid {p['border']};
        color: {p['muted']};
    }}
    QTabBar::tab:selected {{
        color: {p['text']};
        background: {p['panel_alt']};
        border-top: 2px solid {p['accent']};
    }}
    QTabBar::tab:hover {{ background: {p['panel_hover']}; }}
    """
