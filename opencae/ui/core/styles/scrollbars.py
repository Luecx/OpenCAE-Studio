def css(p):
    return f"""
    QScrollBar:vertical {{ background: {p['panel']}; width: 11px; margin: 0; }}
    QScrollBar::handle:vertical {{
        background: {p['border_light']};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: {p['panel']}; height: 11px; }}
    QScrollBar::handle:horizontal {{
        background: {p['border_light']};
        min-width: 24px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """
