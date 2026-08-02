from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QSizePolicy, QStackedWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from .icons import IconKind, make_icon
from .theme import PALETTE


@dataclass(frozen=True)
class CommandSpec:
    text: str
    icon: IconKind
    shortcut: str | None = None
    checkable: bool = False


@dataclass(frozen=True)
class GroupSpec:
    title: str
    commands: tuple[CommandSpec, ...]


PART_GROUPS = (
    GroupSpec('GEOMETRY', (
        CommandSpec('Import', IconKind.IMPORT), CommandSpec('Sketch', IconKind.SKETCH),
        CommandSpec('Create', IconKind.CREATE), CommandSpec('Boolean', IconKind.BOOLEAN),
        CommandSpec('Split', IconKind.SPLIT), CommandSpec('Repair', IconKind.REPAIR),
    )),
    GroupSpec('MESH', (
        CommandSpec('Element\nType', IconKind.ELEMENT), CommandSpec('Global\nSize', IconKind.SIZE),
        CommandSpec('Local\nControl', IconKind.LOCAL), CommandSpec('Generate', IconKind.GENERATE),
        CommandSpec('Quality', IconKind.QUALITY),
    )),
    GroupSpec('REGIONS', (
        CommandSpec('Node Set', IconKind.NODE_SET), CommandSpec('Element Set', IconKind.ELEMENT_SET),
        CommandSpec('Surface', IconKind.SURFACE), CommandSpec('Reference\nPoint', IconKind.REFERENCE),
        CommandSpec('Coordinate\nSystem', IconKind.CSYS),
    )),
    GroupSpec('PROPERTIES', (
        CommandSpec('Material', IconKind.MATERIAL), CommandSpec('Section', IconKind.SECTION),
        CommandSpec('Orientation', IconKind.ORIENTATION), CommandSpec('Thickness', IconKind.THICKNESS),
        CommandSpec('Element\nFormulation', IconKind.FORMULATION),
    )),
)

ASSEMBLY_GROUPS = (
    GroupSpec('INSTANCES', (
        CommandSpec('Add Part', IconKind.INSTANCE), CommandSpec('Duplicate', IconKind.CREATE),
        CommandSpec('Suppress', IconKind.FIXED), CommandSpec('Replace', IconKind.IMPORT),
    )),
    GroupSpec('POSITION', (
        CommandSpec('Translate', IconKind.TRANSLATE), CommandSpec('Rotate', IconKind.ROTATE),
        CommandSpec('Align', IconKind.ALIGN), CommandSpec('Pattern', IconKind.PATTERN),
        CommandSpec('Interference', IconKind.INTERFERENCE),
    )),
    GroupSpec('REGIONS', (
        CommandSpec('Node Set', IconKind.NODE_SET), CommandSpec('Element Set', IconKind.ELEMENT_SET),
        CommandSpec('Surface', IconKind.SURFACE), CommandSpec('Reference\nPoint', IconKind.REFERENCE),
        CommandSpec('Coordinate\nSystem', IconKind.CSYS),
    )),
    GroupSpec('CONNECTIONS', (
        CommandSpec('Contact', IconKind.SURFACE), CommandSpec('Tie', IconKind.ALIGN),
        CommandSpec('Coupling', IconKind.REFERENCE), CommandSpec('Connector', IconKind.INSTANCE),
    )),
)

BC_GROUPS = (
    GroupSpec('BOUNDARY CONDITIONS', (
        CommandSpec('Fixed', IconKind.FIXED), CommandSpec('Displacement', IconKind.DISPLACEMENT),
        CommandSpec('Symmetry', IconKind.ALIGN), CommandSpec('Remote', IconKind.REFERENCE),
    )),
    GroupSpec('LOADS', (
        CommandSpec('Force', IconKind.FORCE), CommandSpec('Pressure', IconKind.PRESSURE),
        CommandSpec('Moment', IconKind.MOMENT), CommandSpec('Gravity', IconKind.GRAVITY),
    )),
    GroupSpec('STEP DATA', (
        CommandSpec('Amplitude', IconKind.OUTPUT), CommandSpec('Initial\nCondition', IconKind.STEP),
        CommandSpec('Preload', IconKind.FORCE), CommandSpec('Temperature', IconKind.CONTOUR),
    )),
)

ANALYSIS_GROUPS = (
    GroupSpec('ANALYSIS', (
        CommandSpec('New\nAnalysis', IconKind.ANALYSIS), CommandSpec('Linear\nStatic', IconKind.ANALYSIS),
        CommandSpec('Nonlinear\nStatic', IconKind.CONTROLS), CommandSpec('Modal', IconKind.OUTPUT),
        CommandSpec('Buckling', IconKind.DEFORM), CommandSpec('Transient', IconKind.STEP),
    )),
    GroupSpec('STEPS', (
        CommandSpec('New Step', IconKind.STEP), CommandSpec('Duplicate', IconKind.CREATE),
        CommandSpec('Controls', IconKind.CONTROLS), CommandSpec('Output', IconKind.OUTPUT),
    )),
    GroupSpec('SOLVER', (
        CommandSpec('Select\nSolver', IconKind.FORMULATION), CommandSpec('Deck\nPreview', IconKind.OUTPUT),
        CommandSpec('Working\nDirectory', IconKind.IMPORT),
    )),
)

SOLVE_GROUPS = (
    GroupSpec('VALIDATE', (
        CommandSpec('Check Model', IconKind.VALIDATE), CommandSpec('Check Mesh', IconKind.QUALITY),
        CommandSpec('Check Regions', IconKind.NODE_SET), CommandSpec('Check Units', IconKind.SIZE),
    )),
    GroupSpec('RUN', (
        CommandSpec('Write Deck', IconKind.EXPORT), CommandSpec('Run Active', IconKind.RUN),
        CommandSpec('Run All', IconKind.ANIMATE), CommandSpec('Cancel', IconKind.FIXED),
    )),
    GroupSpec('MONITOR', (
        CommandSpec('Jobs', IconKind.OUTPUT), CommandSpec('Convergence', IconKind.DEFORM),
        CommandSpec('Solver Log', IconKind.OUTPUT), CommandSpec('Performance', IconKind.CONTROLS),
    )),
)

RESULT_GROUPS = (
    GroupSpec('FIELD', (
        CommandSpec('Displacement', IconKind.DEFORM), CommandSpec('Stress', IconKind.CONTOUR),
        CommandSpec('Strain', IconKind.CONTOUR), CommandSpec('Contact', IconKind.SURFACE),
    )),
    GroupSpec('DISPLAY', (
        CommandSpec('Contour', IconKind.CONTOUR), CommandSpec('Deformed', IconKind.DEFORM),
        CommandSpec('Probe', IconKind.PROBE), CommandSpec('Animate', IconKind.ANIMATE),
    )),
    GroupSpec('EXPORT', (
        CommandSpec('Image', IconKind.EXPORT), CommandSpec('CSV', IconKind.EXPORT),
        CommandSpec('VTK', IconKind.EXPORT), CommandSpec('Report', IconKind.OUTPUT),
    )),
)

STAGES = {
    'PART': PART_GROUPS,
    'ASSEMBLY': ASSEMBLY_GROUPS,
    'BOUNDARY CONDITIONS': BC_GROUPS,
    'ANALYSIS': ANALYSIS_GROUPS,
    'SOLVE': SOLVE_GROUPS,
    'RESULTS': RESULT_GROUPS,
}


class RibbonButton(QToolButton):
    def __init__(self, spec: CommandSpec, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(spec.text)
        self.setIcon(make_icon(spec.icon, 42))
        self.setIconSize(QSize(42, 42))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setCheckable(spec.checkable)
        self.setFixedSize(78, 76)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QToolButton {{ padding: 4px 3px 3px 3px; color: {PALETTE['text']}; }}
            QToolButton:hover {{ background: {PALETTE['panel_hover']}; border: 1px solid {PALETTE['border_light']}; }}
        """)


class RibbonGroup(QFrame):
    commandTriggered = pyqtSignal(str)

    def __init__(self, spec: GroupSpec, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName('RibbonGroup')
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"QFrame#RibbonGroup {{ border-right: 1px solid {PALETTE['border']}; }}")
        outer = QVBoxLayout(self); outer.setContentsMargins(7, 4, 7, 2); outer.setSpacing(1)
        buttons = QHBoxLayout(); buttons.setContentsMargins(0,0,0,0); buttons.setSpacing(2)
        for command in spec.commands:
            button = RibbonButton(command)
            button.clicked.connect(lambda checked=False, name=command.text.replace('\n',' '): self.commandTriggered.emit(name))
            buttons.addWidget(button)
        outer.addLayout(buttons)
        title = QLabel(spec.title); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{PALETTE['accent']}; font-size:8pt; font-weight:600; letter-spacing:1px;")
        outer.addWidget(title)


class RibbonPage(QWidget):
    commandTriggered = pyqtSignal(str)

    def __init__(self, groups: tuple[GroupSpec, ...], parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self); layout.setContentsMargins(5, 0, 0, 0); layout.setSpacing(0)
        for spec in groups:
            group = RibbonGroup(spec); group.commandTriggered.connect(self.commandTriggered)
            layout.addWidget(group)
        layout.addStretch(1)


class StageBar(QWidget):
    stageChanged = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(43)
        layout = QHBoxLayout(self); layout.setContentsMargins(12,0,12,0); layout.setSpacing(1)
        self.group = QButtonGroup(self); self.group.setExclusive(True)
        for index, stage in enumerate(STAGES):
            button = QToolButton(); button.setText(stage); button.setCheckable(True); button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor); button.setMinimumWidth(92); button.setFixedHeight(40)
            button.setStyleSheet(f"""
                QToolButton {{ border:none; border-bottom:3px solid transparent; padding:4px 14px; font-weight:600; color:{PALETTE['muted']}; }}
                QToolButton:hover {{ background:{PALETTE['panel_hover']}; color:{PALETTE['text']}; }}
                QToolButton:checked {{ color:{PALETTE['text']}; border-bottom-color:{PALETTE['accent']}; background:{PALETTE['panel_alt']}; }}
            """)
            self.group.addButton(button, index); layout.addWidget(button)
            button.clicked.connect(lambda checked=False, s=stage: self.stageChanged.emit(s))
            if index == 0: button.setChecked(True)
        layout.addStretch(1)


class Ribbon(QWidget):
    stageChanged = pyqtSignal(str)
    commandTriggered = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_stage = 'PART'
        self.setStyleSheet(f"background:{PALETTE['panel']}; border-bottom:1px solid {PALETTE['border']};")
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.stage_bar = StageBar(); self.stage_bar.stageChanged.connect(self._change_stage); layout.addWidget(self.stage_bar)
        self.context = QLabel('  Active Part:  Bracket     Used by:  Bracket-1')
        self.context.setFixedHeight(28); self.context.setStyleSheet(f"background:{PALETTE['panel_alt']}; color:{PALETTE['muted']}; border-top:1px solid {PALETTE['border']}; border-bottom:1px solid {PALETTE['border']}; padding-left:8px;")
        layout.addWidget(self.context)
        self.stack = QStackedWidget(); self.stack.setFixedHeight(104)
        for stage, groups in STAGES.items():
            page = RibbonPage(groups); page.commandTriggered.connect(lambda command, s=stage: self.commandTriggered.emit(s, command)); self.stack.addWidget(page)
        layout.addWidget(self.stack)

    def _change_stage(self, stage: str) -> None:
        self.current_stage = stage
        self.stack.setCurrentIndex(list(STAGES).index(stage))
        contexts = {
            'PART': '  Active Part:  Bracket     Used by:  Bracket-1',
            'ASSEMBLY': '  Assembly:  Main Assembly     3 instances · 3 unique parts',
            'BOUNDARY CONDITIONS': '  Analysis:  Static-1     Step:  Step-1',
            'ANALYSIS': '  Active Analysis:  Static-1     Solver:  FEMaster',
            'SOLVE': '  Active Analysis:  Static-1     Status:  Ready',
            'RESULTS': '  Result Set:  Static-1     Increment:  1',
        }
        self.context.setText(contexts[stage]); self.stageChanged.emit(stage)
