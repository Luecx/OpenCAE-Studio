from __future__ import annotations

PALETTE = {
    'window': '#171a1f',
    'panel': '#1d2127',
    'panel_alt': '#22272e',
    'panel_hover': '#29313a',
    'border': '#303741',
    'border_light': '#3a424d',
    'text': '#e5e9ef',
    'muted': '#98a2ad',
    'accent': '#3296e6',
    'accent_hover': '#43a6f5',
    'accent_dim': '#173d5b',
    'success': '#49b675',
    'warning': '#d5a442',
    'danger': '#df6262',
    'viewport': '#101319',
}


def stylesheet() -> str:
    p = PALETTE
    return f"""
    * {{
        font-family: 'Segoe UI', 'Inter', sans-serif;
        font-size: 10pt;
        color: {p['text']};
    }}
    QMainWindow, QDialog {{ background: {p['window']}; }}
    QMenuBar {{ background: {p['panel']}; border-bottom: 1px solid {p['border']}; padding: 2px; }}
    QMenuBar::item {{ padding: 6px 10px; background: transparent; }}
    QMenuBar::item:selected {{ background: {p['panel_hover']}; }}
    QMenu {{ background: {p['panel_alt']}; border: 1px solid {p['border_light']}; padding: 5px; }}
    QMenu::item {{ padding: 7px 30px 7px 26px; border-radius: 3px; }}
    QMenu::item:selected {{ background: {p['accent_dim']}; }}
    QMenu::separator {{ height: 1px; background: {p['border']}; margin: 5px 8px; }}
    QToolTip {{ background: {p['panel_alt']}; border: 1px solid {p['border_light']}; padding: 5px; }}
    QDockWidget {{ color: {p['text']}; titlebar-close-icon: none; titlebar-normal-icon: none; }}
    QDockWidget::title {{ background: {p['panel_alt']}; padding: 8px; border-bottom: 1px solid {p['border']}; }}
    QTreeWidget, QTableWidget, QListWidget, QTextEdit, QPlainTextEdit {{
        background: {p['panel']}; border: none; alternate-background-color: {p['panel_alt']}; selection-background-color: {p['accent_dim']};
    }}
    QTreeWidget::item {{ height: 26px; padding-left: 2px; }}
    QTreeWidget::item:hover {{ background: {p['panel_hover']}; }}
    QHeaderView::section {{ background: {p['panel_alt']}; border: none; border-right: 1px solid {p['border']}; padding: 6px; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {p['window']}; border: 1px solid {p['border_light']}; border-radius: 3px; padding: 5px 7px; min-height: 22px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {p['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QTabWidget::pane {{ border: none; border-top: 1px solid {p['border']}; background: {p['panel']}; }}
    QTabBar::tab {{ background: {p['panel']}; padding: 8px 14px; border-right: 1px solid {p['border']}; color: {p['muted']}; }}
    QTabBar::tab:selected {{ color: {p['text']}; background: {p['panel_alt']}; border-top: 2px solid {p['accent']}; }}
    QTabBar::tab:hover {{ background: {p['panel_hover']}; }}
    QScrollBar:vertical {{ background: {p['panel']}; width: 11px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {p['border_light']}; min-height: 24px; border-radius: 5px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: {p['panel']}; height: 11px; }}
    QScrollBar::handle:horizontal {{ background: {p['border_light']}; min-width: 24px; border-radius: 5px; }}
    QStatusBar {{ background: {p['panel']}; border-top: 1px solid {p['border']}; }}
    QPushButton {{ background: {p['panel_alt']}; border: 1px solid {p['border_light']}; padding: 6px 10px; border-radius: 3px; }}
    QPushButton:hover {{ background: {p['panel_hover']}; border-color: {p['accent']}; }}
    QPushButton:pressed {{ background: {p['accent_dim']}; }}
    QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 3px; }}
    QToolButton:hover {{ background: {p['panel_hover']}; border-color: {p['border_light']}; }}
    QToolButton:pressed, QToolButton:checked {{ background: {p['accent_dim']}; border-color: {p['accent']}; }}
    QSplitter::handle {{ background: {p['border']}; }}
    """
