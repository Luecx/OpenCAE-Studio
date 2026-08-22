def css(p):
    return f"""
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {p['window']};
        border: 1px solid {p['border_light']};
        border-radius: 3px;
        padding: 5px 9px;
        min-height: 22px;
        min-width: 316px;
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
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: #53606d; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {p['accent']}; }}
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
        padding: 3px;
    }}
    QPushButton#InlineAddButton {{
        min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
        padding: 0; font-size: 15px; font-weight: 700;
        color: {p['accent']}; background: {p['panel_alt']};
        border: 1px solid {p['border_light']}; border-radius: 3px;
    }}
    QPushButton#InlineAddButton:hover {{ border-color: {p['accent']}; background: {p['accent_dim']}; }}
    QLabel#MatrixHeader {{ color: {p['muted']}; font-size: 8pt; min-width: 22px; }}
    QDoubleSpinBox#MatrixCell {{ min-width: 76px; max-width: 96px; padding: 4px 5px; }}
    QCheckBox {{ spacing: 7px; }}
    QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {p['border_light']}; background: {p['window']}; border-radius: 2px; }}
    QCheckBox::indicator:checked {{ background: {p['accent']}; border-color: {p['accent']}; }}
    """
