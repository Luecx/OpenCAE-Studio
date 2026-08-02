def css(p):
    return f"""
    * {{
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 10pt;
        color: {p['text']};
    }}
    QMainWindow, QDialog {{ background: {p['window']}; }}
    QWidget#CentralSurface, QWidget#DockSurface, QWidget#ProjectPanel,
    QWidget#PropertiesPanel, QWidget#OutputPanel {{ background: {p['panel']}; }}
    QToolTip {{
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        padding: 5px;
    }}
    """
