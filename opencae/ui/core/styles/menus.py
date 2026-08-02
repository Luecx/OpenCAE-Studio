def css(p):
    return f"""
    QMenuBar {{
        background: {p['panel']};
        border-bottom: 1px solid {p['border']};
        padding: 2px;
    }}
    QMenuBar::item {{ padding: 6px 10px; background: transparent; }}
    QMenuBar::item:selected {{ background: {p['panel_hover']}; }}
    QMenu {{
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        padding: 5px;
    }}
    QMenu::item {{ padding: 7px 30px 7px 26px; border-radius: 3px; }}
    QMenu::item:selected {{ background: {p['accent_dim']}; }}
    QMenu::item:disabled {{ color: #66717c; }}
    QMenu::separator {{ height: 1px; background: {p['border']}; margin: 5px 8px; }}
    """
