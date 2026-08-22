from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from opencae.ui.core.theme import PALETTE

from .kinds import IconKind
from .legacy import IconKind as LegacyKind
from .legacy import make_icon as make_legacy_icon
from .modern_renderer import make_modern_icon

_ICON_MAP = {
    IconKind.FILE:LegacyKind.OUTPUT, IconKind.SAVE:LegacyKind.EXPORT, IconKind.IMPORT:LegacyKind.IMPORT,
    IconKind.PART:LegacyKind.CREATE, IconKind.PARTITION:LegacyKind.SPLIT, IconKind.MESH:LegacyKind.GENERATE,
    IconKind.SEED:LegacyKind.SIZE, IconKind.ELEMENT:LegacyKind.ELEMENT, IconKind.ELEMENT_CONTROLS:LegacyKind.FORMULATION, IconKind.NODE_SET:LegacyKind.NODE_SET,
    IconKind.ELEMENT_SET:LegacyKind.ELEMENT_SET, IconKind.SURFACE:LegacyKind.SURFACE, IconKind.CSYS:LegacyKind.CSYS,
    IconKind.RP:LegacyKind.REFERENCE, IconKind.MATERIAL:LegacyKind.MATERIAL, IconKind.PROFILE:LegacyKind.PROFILE,
    IconKind.SECTION:LegacyKind.SECTION, IconKind.ASSIGN:LegacyKind.ASSIGN_SECTION, IconKind.INSTANCE:LegacyKind.INSTANCE,
    IconKind.MOVE:LegacyKind.TRANSLATE, IconKind.ROTATE:LegacyKind.ROTATE, IconKind.PATTERN:LegacyKind.PATTERN,
    IconKind.CONSTRAINT:LegacyKind.ALIGN,
    IconKind.CONSTRAINT_KINEMATIC:LegacyKind.CONSTRAINT_KINEMATIC,
    IconKind.CONSTRAINT_DISTRIBUTING:LegacyKind.CONSTRAINT_DISTRIBUTING, IconKind.CONSTRAINT_TIE:LegacyKind.CONSTRAINT_TIE,
    IconKind.CONSTRAINT_RIGID:LegacyKind.CONSTRAINT_RIGID,
    IconKind.CONSTRAINT_MPC:LegacyKind.CONSTRAINT_MPC,
    IconKind.SUPPORT:LegacyKind.FIXED, IconKind.FIXED_SUPPORT:LegacyKind.FIXED,
    IconKind.DISPLACEMENT_SUPPORT:LegacyKind.DISPLACEMENT, IconKind.SYMMETRY_SUPPORT:LegacyKind.SYMMETRY,
    IconKind.LOAD:LegacyKind.FORCE, IconKind.CONCENTRATED_LOAD:LegacyKind.FORCE, IconKind.TRACTION_LOAD:LegacyKind.TRACTION,
    IconKind.PRESSURE_LOAD:LegacyKind.PRESSURE, IconKind.VOLUME_LOAD:LegacyKind.VOLUME, IconKind.INERTIA_LOAD:LegacyKind.INERTIA,
    IconKind.TEMPERATURE_LOAD:LegacyKind.TEMPERATURE, IconKind.ANALYSIS:LegacyKind.ANALYSIS, IconKind.SETTINGS:LegacyKind.CONTROLS,
    IconKind.VALIDATE:LegacyKind.VALIDATE, IconKind.DECK:LegacyKind.OUTPUT, IconKind.RUN:LegacyKind.RUN,
    IconKind.RESULTS:LegacyKind.CONTOUR, IconKind.EDIT:LegacyKind.REPAIR,
    IconKind.INFO:LegacyKind.OUTPUT, IconKind.ELASTICITY:LegacyKind.ELASTICITY,
    IconKind.DENSITY:LegacyKind.DENSITY, IconKind.PLASTICITY:LegacyKind.PLASTICITY, IconKind.THERMAL:LegacyKind.THERMAL,
    IconKind.FIELD:LegacyKind.FIELD, IconKind.SECTION_SOLID:LegacyKind.SECTION_SOLID, IconKind.SECTION_SHELL:LegacyKind.SECTION_SHELL,
    IconKind.SECTION_BEAM:LegacyKind.SECTION_BEAM, IconKind.SECTION_TRUSS:LegacyKind.SECTION_TRUSS,
    IconKind.PROFILE_RECTANGLE:LegacyKind.PROFILE_RECTANGLE, IconKind.PROFILE_BOX:LegacyKind.PROFILE_BOX,
    IconKind.PROFILE_PIPE:LegacyKind.PROFILE_PIPE, IconKind.PROFILE_I:LegacyKind.PROFILE_I,
    IconKind.PROFILE_CHANNEL:LegacyKind.PROFILE_CHANNEL, IconKind.PROFILE_U:LegacyKind.PROFILE_U,
    IconKind.PROFILE_H:LegacyKind.PROFILE_H, IconKind.PROFILE_CIRCLE:LegacyKind.PROFILE_CIRCLE, IconKind.PROFILE_GENERAL:LegacyKind.PROFILE_GENERAL,
    IconKind.PROFILE_GRAPH:LegacyKind.PROFILE_GRAPH, IconKind.STEP_LINEAR:LegacyKind.STEP_LINEAR,
    IconKind.STEP_NONLINEAR:LegacyKind.STEP_NONLINEAR, IconKind.STEP_MODAL:LegacyKind.STEP_MODAL,
    IconKind.STEP_BUCKLING:LegacyKind.STEP_BUCKLING, IconKind.STEP_TRANSIENT:LegacyKind.STEP_TRANSIENT,
    IconKind.REORDER:LegacyKind.REORDER, IconKind.MATRIX:LegacyKind.MATRIX, IconKind.CONTOUR:LegacyKind.CONTOUR,
    IconKind.RESULT_STEP:LegacyKind.RESULT_STEP, IconKind.RESULT_FRAME:LegacyKind.RESULT_FRAME, IconKind.RESULT_FIELD:LegacyKind.RESULT_FIELD,
    IconKind.PREVIOUS_FRAME:LegacyKind.PREVIOUS_FRAME, IconKind.NEXT_FRAME:LegacyKind.NEXT_FRAME,
    IconKind.MESH_LINES:LegacyKind.MESH_LINES, IconKind.BOUNDARY_LINES:LegacyKind.BOUNDARY_LINES, IconKind.DEFORMATION:LegacyKind.DEFORMATION, IconKind.SECTION_VIEW:LegacyKind.SECTION_VIEW,
    IconKind.PICK:LegacyKind.PICK,
}


def _x_icon(size: int, accent: str | None = None) -> QIcon:
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(accent or PALETTE["accent"])
    painter.setPen(
        QPen(
            color,
            max(2.2, size / 12.5),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    inset = size * .25
    painter.drawLine(QPointF(inset, inset), QPointF(size - inset, size - inset))
    painter.drawLine(QPointF(size - inset, inset), QPointF(inset, size - inset))
    painter.end()
    return QIcon(pixmap)


def make_icon(kind: IconKind, size: int = 40, accent: str | None = None) -> QIcon:
    if kind in {IconKind.DELETE, IconKind.SUPPRESS}:
        return _x_icon(size, accent)
    modern = make_modern_icon(kind, size, accent)
    if modern is not None:
        return modern
    return make_legacy_icon(_ICON_MAP[kind], size, accent)
