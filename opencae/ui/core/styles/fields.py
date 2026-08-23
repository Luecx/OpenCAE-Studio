"""Styles editable fields and the shared primary-control geometry contract."""

from opencae.ui.templates.control_metrics import (
    COMBO_POPUP_ROW_HEIGHT,
    INLINE_ACTION_SIZE,
    PRIMARY_CONTROL_HEIGHT,
)


def css(p):
    """Return QSS for text, numeric, combo and compact composite controls."""
    return f"""
    QWidget#PrimaryFieldBlock {{
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
        min-width: 316px;
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
    QDoubleSpinBox#XYZLast {{
        min-width: 0px;
        padding: 5px 7px;
        border-radius: 0px;
    }}
    QDoubleSpinBox#XYZFirst {{
        border-top-left-radius: 3px;
        border-bottom-left-radius: 3px;
    }}
    QDoubleSpinBox#XYZMiddle,
    QDoubleSpinBox#XYZLast {{
        border-left: 0px;
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

    QToolButton#InlineAddButton,
    QToolButton#InlinePickButton {{
        min-width: {INLINE_ACTION_SIZE}px;
        max-width: {INLINE_ACTION_SIZE}px;
        min-height: {INLINE_ACTION_SIZE}px;
        max-height: {INLINE_ACTION_SIZE}px;
        padding: 0px;
        color: {p['accent']};
        background: {p['panel_alt']};
        border: 1px solid {p['border_light']};
        border-radius: 3px;
    }}
    QToolButton#InlineAddButton {{
        font-size: 15px;
        font-weight: 600;
    }}
    QToolButton#InlineAddButton:hover,
    QToolButton#InlinePickButton:hover,
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
    """
