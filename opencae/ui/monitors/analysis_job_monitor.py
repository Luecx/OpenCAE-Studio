"""Progress and solver-output window for a running Analysis Job."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.widgets import MonospaceOutputView
from opencae.ui.templates import SectionHeading


_TERMINAL_LABELS = {"completed", "failed", "cancelled", "stopping"}
_DETAIL_ROWS = (
    ("step", "Step"),
    ("procedure", "Procedure"),
    ("frame", "Frame"),
    ("iteration", "Iteration"),
    ("time_frequency", "Time / Frequency"),
    ("state", "Solver State"),
)


class AnalysisJobMonitor(QDialog):
    """Show one Analysis Job's solver transcript and structured runtime state."""

    def __init__(self, store, job_id, parent=None, *, stop_callback=None):
        """Build a persistent monitor for one Job id."""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.job_id = str(job_id)
        self._stop_callback = stop_callback
        self._structured_runtime_seen = False
        job = store.project.try_resolve(self.job_id)
        self.setWindowTitle(
            f"Analysis Monitor - {getattr(job, 'name', 'Job')}"
        )
        self.resize(1180, 660)
        self.setMinimumSize(860, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        self.phase = QLabel(getattr(job, "progress_label", "Prepared"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        layout.addWidget(self.phase)
        layout.addWidget(self.progress)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_output_panel())
        splitter.addWidget(self._build_runtime_panel(store, job))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes((790, 370))
        layout.addWidget(splitter, 1)
        self.splitter = splitter

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addStretch(1)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Terminate this solver job")
        self.stop_button.clicked.connect(self._stop)
        actions.addWidget(self.stop_button)
        layout.addLayout(actions)

        self.set_progress(
            self.job_id,
            getattr(job, "progress", 0.0),
            getattr(job, "progress_label", "Prepared"),
        )

    def _build_output_panel(self) -> QWidget:
        """Create the large left-hand monospaced solver transcript surface."""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(8)
        layout.addWidget(SectionHeading("Solver Output"))
        self.output = MonospaceOutputView(panel)
        layout.addWidget(self.output, 1)
        return panel

    def _build_runtime_panel(self, store, job) -> QWidget:
        """Create the structured right-hand runtime and post-check summary."""
        panel = QWidget(self)
        panel.setMinimumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(SectionHeading("Runtime Details"))

        details = QGridLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setHorizontalSpacing(14)
        details.setVerticalSpacing(7)
        self.detail_values = {}
        for row, (key, title) in enumerate(_DETAIL_ROWS):
            name = QLabel(title)
            name.setObjectName("AnalysisMonitorDetailName")
            value = QLabel("—")
            value.setObjectName("AnalysisMonitorDetailValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            details.addWidget(name, row, 0, Qt.AlignmentFlag.AlignTop)
            details.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
            self.detail_values[key] = value
        details.setColumnStretch(1, 1)
        layout.addLayout(details)

        layout.addWidget(SectionHeading("Step / Post Checks"))
        self.post_checks = QTreeWidget(panel)
        self.post_checks.setObjectName("AnalysisMonitorPostChecks")
        self.post_checks.setColumnCount(3)
        self.post_checks.setHeaderLabels(("Step / Check", "Status", "Values"))
        self.post_checks.setRootIsDecorated(True)
        self.post_checks.setAlternatingRowColors(False)
        header = self.post_checks.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.post_checks, 1)
        self._seed_known_steps(store, job)

        note = QLabel(
            "FEMaster runtime details are parsed live from solver output; "
            "OpenCAE step names provide the stable loadcase identity."
        )
        note.setObjectName("AnalysisMonitorParserNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        return panel

    def _seed_known_steps(self, store, job) -> None:
        """List configured analysis steps without pretending one is already active."""
        project = store.project
        analysis = project.try_resolve(getattr(job, "source_ref", None))
        resolved = getattr(analysis, "resolved_steps", None)
        if not callable(resolved):
            return
        try:
            steps = tuple(resolved(project))
        except (AttributeError, KeyError, TypeError, ValueError):
            return
        for step in steps:
            title = str(getattr(step, "name", "Step") or "Step")
            procedure = str(getattr(step, "step_type", "") or "")
            item = QTreeWidgetItem((title, "Waiting", procedure))
            self.post_checks.addTopLevelItem(item)

    def set_runtime_state(self, job_id, details, steps):
        """Apply one complete structured FEMaster parser snapshot."""
        if str(job_id) != self.job_id:
            return
        self.set_runtime_details(job_id, details)
        self.set_post_checks(job_id, steps)

    def set_runtime_details(self, job_id, values):
        """Apply already-parsed FEMaster runtime fields to the right-hand summary."""
        if str(job_id) != self.job_id:
            return
        data = dict(values or {})
        if any(str(data.get(key, "")).strip() not in {"", "—", "Waiting"} for key in ("step", "procedure")):
            self._structured_runtime_seen = True
        for key, widget in self.detail_values.items():
            if key in data:
                widget.setText(str(data[key] if data[key] not in (None, "") else "—"))

    def set_post_checks(self, job_id, steps):
        """Replace the step/check tree with structured parser output."""
        if str(job_id) != self.job_id:
            return
        self.post_checks.clear()
        for step in tuple(steps or ()):
            data = dict(step or {})
            root = QTreeWidgetItem(
                (
                    str(data.get("name", "Step")),
                    str(data.get("status", "")),
                    str(data.get("procedure", "")),
                )
            )
            for check in tuple(data.get("checks", ()) or ()):
                check_data = dict(check or {})
                frame = str(check_data.get("frame", "") or "")
                check_name = str(check_data.get("name", "Check"))
                label = f"{frame} · {check_name}" if frame else check_name
                child = QTreeWidgetItem(
                    (
                        label,
                        str(check_data.get("status", "")),
                        str(check_data.get("detail", "")),
                    )
                )
                root.addChild(child)
            root.setExpanded(True)
            self.post_checks.addTopLevelItem(root)

    def set_progress(self, job_id, value, label):
        """Apply a progress event only when it belongs to this monitor's Job."""
        if str(job_id) != self.job_id:
            return
        label = str(label)
        self.phase.setText(label)
        if not self._structured_runtime_seen:
            self.detail_values["state"].setText(label or "—")
        self.progress.setValue(
            round(min(max(float(value), 0.0), 1.0) * 1000)
        )
        self.stop_button.setEnabled(
            callable(self._stop_callback)
            and label.strip().casefold() not in _TERMINAL_LABELS
        )

    def set_output(self, job_id, text):
        """Load the persisted solver transcript when this monitor is opened."""
        if str(job_id) != self.job_id:
            return
        self.output.set_output(text)

    def append_output(self, job_id, text):
        """Append a live solver-output chunk for this monitor's Job."""
        if str(job_id) != self.job_id:
            return
        self.output.append_output(text)

    def _stop(self):
        """Request cancellation for this monitor's Job only once per click."""
        callback = self._stop_callback
        if not callable(callback):
            return
        self.stop_button.setEnabled(False)
        callback()
