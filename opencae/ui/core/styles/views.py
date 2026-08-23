"""Styles tree, table, and list views used throughout the application."""


def css(p):
    """Return QSS for item views and table headers."""
    return f"""
    QTreeView, QTreeWidget, QTableView, QTableWidget, QListView,
    QListWidget, QTextEdit, QPlainTextEdit {{
        background: {p['panel']};
        border: none;
        alternate-background-color: {p['panel_alt']};
        selection-background-color: {p['accent_dim']};
        selection-color: {p['text']};
        outline: 0;
    }}
    QTableView, QTableWidget {{
        gridline-color: {p['border']};
    }}
    QTableView::item, QTableWidget::item {{
        padding: 4px 6px;
        border: none;
    }}
    QTreeView::item, QTreeWidget::item {{
        min-height: 27px;
        padding-left: 3px;
        border: none;
    }}
    QTreeView::item:hover, QTreeWidget::item:hover {{ background: {p['panel_hover']}; }}
    QTreeView::item:selected, QTreeWidget::item:selected {{ background: {p['accent_dim']}; }}

    QListWidget#EditorCheckList {{
        background: {p['window']};
        border: 1px solid {p['border_light']};
        border-radius: 3px;
        padding: 3px;
    }}
    QListWidget#EditorCheckList::item {{
        min-height: 32px;
        padding: 2px 7px;
        border: none;
    }}
    QListWidget#EditorCheckList::item:hover {{ background: {p['panel_hover']}; }}
    QListWidget#EditorCheckList::item:selected {{ background: {p['accent_dim']}; }}

    QHeaderView {{
        background: {p['panel_alt']};
    }}
    QHeaderView::section {{
        background: {p['panel_alt']};
        color: {p['text']};
        border: none;
        border-right: 1px solid {p['border']};
        border-bottom: 1px solid {p['border']};
        padding: 6px;
    }}
    QTableCornerButton::section {{
        background: {p['panel_alt']};
        border: none;
        border-right: 1px solid {p['border']};
        border-bottom: 1px solid {p['border']};
    }}
    """
