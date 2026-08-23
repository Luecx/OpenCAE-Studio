"""Styles the inline Material dialog cards without affecting other dialogs."""


def css(p):
    """Return QSS for the redesigned material editor."""
    return f"""
    QLabel#MaterialSectionTitle {{
        color: {p['text']};
        font-weight: 600;
        font-size: 10.5pt;
        border-left: 3px solid {p['accent']};
        padding-left: 8px;
        min-height: 20px;
    }}

    QLabel#MaterialTopLabel,
    QLabel#MaterialFieldLabel {{
        color: {p['muted']};
        font-size: 9pt;
    }}

    QFrame#MaterialBehaviorCard {{
        background: {p['panel']};
        border: 1px solid {p['border']};
        border-radius: 6px;
    }}
    QFrame#MaterialBehaviorCard:hover {{
        border-color: {p['border_light']};
    }}
    QFrame#MaterialBehaviorCard[defined="true"] {{
        border-color: {p['accent']};
    }}

    QWidget#MaterialBehaviorHeader {{
        background: transparent;
        border: none;
    }}
    QWidget#MaterialBehaviorBody {{
        background: {p['panel_alt']};
        border-top: 1px solid {p['border']};
        border-bottom-left-radius: 6px;
        border-bottom-right-radius: 6px;
    }}

    QLabel#MaterialBehaviorIcon {{
        min-width: 30px;
        max-width: 30px;
        min-height: 30px;
        max-height: 30px;
        border-radius: 6px;
        background: {p['accent_dim']};
        color: {p['accent_hover']};
        font-weight: 700;
        font-size: 11pt;
    }}
    QLabel#MaterialBehaviorTitle {{
        color: {p['text']};
        font-weight: 600;
        font-size: 10pt;
    }}

    QLabel#MaterialBehaviorStatus {{
        color: {p['muted']};
        background: {p['panel_alt']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 3px 9px;
    }}
    QLabel#MaterialBehaviorStatus[defined="true"] {{
        color: {p['success']};
        background: #173526;
        border-color: #254d38;
    }}

    QToolButton#MaterialBehaviorAction,
    QToolButton#MaterialBehaviorChevron {{
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border: 1px solid {p['border']};
        border-radius: 4px;
        background: {p['panel_alt']};
        color: {p['muted']};
        font-size: 13px;
        font-weight: 600;
    }}
    QToolButton#MaterialBehaviorAction {{
        color: {p['accent']};
    }}
    QToolButton#MaterialBehaviorAction:hover,
    QToolButton#MaterialBehaviorChevron:hover {{
        border-color: {p['accent']};
        background: {p['accent_dim']};
        color: {p['text']};
    }}
    QToolButton#MaterialBehaviorChevron:disabled {{
        color: {p['border_light']};
        background: transparent;
        border-color: transparent;
    }}

    QComboBox#MaterialModelCombo,
    QDoubleSpinBox#MaterialPropertySpin {{
        min-width: 0px;
        min-height: 28px;
    }}
    QComboBox#MaterialModelCombo {{
        max-width: 360px;
    }}
    """
