"""Provides built-in user documentation and a live keyboard-shortcut reference."""

from __future__ import annotations

from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
)


_DOCUMENTATION_HTML = """
<h1>OpenCAE Studio</h1>
<p>OpenCAE Studio organizes a simulation project as a staged workflow. The ribbon
contains the operations relevant to the active stage; the project tree keeps the
persistent model entities, and the central viewport is used for geometry, mesh,
selection and result inspection.</p>

<h2>Typical workflow</h2>
<ol>
  <li><b>Geometry:</b> create a Part or import STEP, IGES or BREP geometry.</li>
  <li><b>Mesh:</b> define global/edge seeds, element controls and generate the mesh.</li>
  <li><b>Assembly:</b> create instances and assembly-level regions/reference points.</li>
  <li><b>Constraints &amp; loads:</b> define couplings, ties, connectors, supports and loads.</li>
  <li><b>Analysis:</b> create Steps and an Analysis, validate or preview the input deck,
      then run an enabled solver.</li>
  <li><b>Results:</b> open an FRD result set, choose a field/component, query nodes or
      elements, adjust contour limits and inspect deformed or sectioned views.</li>
</ol>

<h2>Viewport</h2>
<ul>
  <li>Use the ViewCube to select standard, edge and corner orientations.</li>
  <li><b>Fit View</b> frames all currently displayed geometry or result content.</li>
  <li>Geometry/Mesh display can be switched from the viewport controls or View menu.</li>
  <li>Selection behavior is contextual: dialogs constrain picking to valid entity types.</li>
</ul>

<h2>Results</h2>
<p>Selecting a result set without a field displays the result geometry without a contour.
Selecting a field adds the scalar contour. Node and element queries report identifiers,
coordinates/topology and available field values. Manual contour limits use outside-range
colors only for values genuinely outside the configured range.</p>

<h2>Project and interface</h2>
<p>The <b>View</b> menu contains both viewport presentation and workspace visibility/layout
commands. Use <b>Reset Layout</b> if docks have been moved or hidden. Application and solver
configuration is available through Preferences and Solver Settings.</p>

<h2>Keyboard shortcuts</h2>
<p>Choose <b>Help → Keyboard Shortcuts</b> for the current shortcut table. The table is
built from the registered application actions, so it stays synchronized with the actual
bindings.</p>
"""


class DocumentationDialog(QDialog):
    """Display a concise bundled manual without requiring an external browser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenCAE Documentation")
        self.setMinimumSize(900, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_DOCUMENTATION_HTML)
        layout.addWidget(browser, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)


class KeyboardShortcutsDialog(QDialog):
    """List shortcuts directly from the application's registered QAction objects."""

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(720, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(("Action", "Shortcut"))
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        entries = []
        for _action_id, action in actions.items():
            shortcut = action.shortcut()
            if shortcut.isEmpty():
                continue
            entries.append(
                (
                    action.text().replace("&", ""),
                    shortcut.toString(QKeySequence.SequenceFormat.NativeText),
                )
            )
        entries.sort(key=lambda item: item[0].casefold())
        table.setRowCount(len(entries))
        for row, (name, shortcut) in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(shortcut))
        layout.addWidget(table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
