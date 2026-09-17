"""Base application stylesheet rules that intentionally inherit the Qt system font."""


def css(p):
    """Return global colors without forcing a platform-specific font family or size."""
    return f"""
    * {{
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
