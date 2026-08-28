"""Styles editable fields and the shared primary-control geometry contract."""

from opencae.ui.templates.control_metrics import (
    COMBO_POPUP_ROW_HEIGHT,
    PRIMARY_CONTROL_HEIGHT,
)


def css(p):
    """Return QSS for text, numeric, combo and compact composite controls."""
    return f"""
    QWidget#PrimaryFieldBlock,
    QWidget#PrimaryFieldStack,
    QWidget#PrimaryFieldRow {{
        background: transparent;
        border: none;
    }}
    QLabel#PrimaryFieldLabel {{
        color: {p['muted']};
        font-size: 9pt;
    }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {p['window']};
        border: 1px solid {p['border_light']};
        border-radius: 3px;
        padding: 5px 9px;
        min-height: 22px;
    }}
    QSpinBox, QDoubleSpinBox {{
        padding-right: 9px;
    }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        width: 0px;
        height: 0px;
        border: none;
        background: transparent;
    }}
    QSpinBox::up-arrow, QSpinBox::down-arrow,
    QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {{
        width: 0px;
        height: 0px;
        image: none;
    }}

    /* Primary controls have one painted height regardless of their Qt class. */
    QLineEdit[primaryControl="true"],
    QComboBox[primaryControl="true"],
    QSpinBox[primaryControl="true"],
    QDoubleSpinBox[primaryControl="true"] {{
        min-height: {PRIMARY_CONTROL_HEIGHT - 2}px;
        max-height: {PRIMARY_CONTROL_HEIGHT - 2}px;
        padding-top: 0px;
        padding-bottom: 0px;
    }}

    QComboBox#ReferenceCombo, QLineEdit#CompositeFieldEdit {{
        min-width: 0px;
    }}
    QDoubleSpinBox#XYZFirst,
    QDoubleSpinBox#XYZMiddle,
    QDoubleSpinBox#XYZLast,
    QDoubleSpinBox#XYZLastWithUnit {{
        min-width: 0px;
        padding: 0px 7px;
        border-radius: 0px;
    }}
    QDoubleSpinBox#XYZFirst {{
        border-top-left-radius: 3px;
        border-bottom-left-radius: 3px;
    }}
    QDoubleSpinBox#XYZMiddle,
    QDoubleSpinBox#XYZLast,
    QDoubleSpinBox#XYZLastWithUnit {{
        border-left: 0px;
    }}
    QDoubleSpinBox#XYZLast {{
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    QDoubleSpinBox#XYZLastWithUnit {{
        border-right: 0px;
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: #53606d;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {p['accent']};
    }}
    QComboBox {{ padding-right: 30px; }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border-left: 1px solid {p['border_light']};
        background: {p['panel_alt']};
    }}
    QComboBox::down-arrow {{ image: none; }}
    QComboBox QAbstractItemView {{
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        selection-background-color: {p['accent_dim']};
        padding: 2px;
        outline: 0px;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: {COMBO_POPUP_ROW_HEIGHT}px;
        padding-left: 10px;
        padding-right: 10px;
        border: none;
    }}

    QWidget#NumericUnitInput {{
        background: transparent;
        border: none;
    }}
    QDoubleSpinBox#PrimaryNumeric,
    QDoubleSpinBox#PrimaryNumericWithUnit {{
        min-width: 0px;
    }}
    QDoubleSpinBox#PrimaryNumericWithUnit {{
        border-top-right-radius: 0px;
        border-bottom-right-radius: 0px;
        border-right: 0px;
    }}
    QLabel#PrimaryUnitLabel {{
        min-width: 54px;
        padding: 0px 10px;
        background: {p['panel_alt']};
        color: {p['text']};
        border: 1px solid {p['border_light']};
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    /* Geometry comes exclusively from setFixedSize() in control_metrics.
       Repeating dimensions in QSS can clip a one-pixel rounded border. */
    QToolButton[inlineAction="true"] {{
        padding: 0px;
        margin: 0px;
        color: {p['accent']};
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        border-radius: 3px;
    }}
    QToolButton#InlineAddButton {{
        font-size: 15px;
        font-weight: 600;
    }}
    QToolButton[inlineAction="true"]:hover,
    QToolButton#InlinePickButton:checked {{
        border-color: {p['accent']};
        background: {p['accent_dim']};
    }}

    QLabel#MatrixHeader {{ color: {p['muted']}; font-size: 8pt; min-width: 22px; }}
    QDoubleSpinBox#MatrixCell {{ min-width: 76px; max-width: 96px; padding: 4px 5px; }}

    QCheckBox {{ spacing: 7px; }}
    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
        border: 1px solid {p['border_light']};
        background: {p['window']};
        border-radius: 2px;
    }}
    QCheckBox::indicator:checked {{
        background: {p['accent']};
        border-color: {p['accent']};
    }}

    /* Radios use a real circular ring and center dot instead of the platform
       default indicator, which otherwise clashes with the flat dark theme. */
    QRadioButton {{
        spacing: 8px;
        color: {p['text']};
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {p['border_light']};
        border-radius: 9px;
        background: {p['window']};
    }}
    QRadioButton::indicator:hover {{
        border-color: {p['accent_hover']};
        background: {p['panel_alt']};
    }}
    QRadioButton::indicator:checked {{
        border-color: {p['accent']};
        background: qradialgradient(
            cx: 0.5, cy: 0.5, radius: 0.5,
            fx: 0.5, fy: 0.5,
            stop: 0 {p['accent']},
            stop: 0.33 {p['accent']},
            stop: 0.35 {p['window']},
            stop: 1 {p['window']}
        );
    }}
    QRadioButton::indicator:checked:hover {{
        border-color: {p['accent_hover']};
    }}
    QRadioButton:disabled {{ color: {p['muted']}; }}
    QRadioButton::indicator:disabled {{
        border-color: {p['border']};
        background: {p['panel']};
    }}
    """
