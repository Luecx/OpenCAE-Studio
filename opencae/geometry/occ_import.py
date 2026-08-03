from __future__ import annotations

from pathlib import Path
import logging

from opencae.model.entities.geometry import ImportedStepFeature

from .errors import GeometryError

_LOG = logging.getLogger(__name__)


def source_feature(part):
    return next(
        (
            feature
            for feature in part.geometry
            if not feature.suppressed
            and isinstance(feature, ImportedStepFeature)
        ),
        None,
    )


def import_source(gmsh, part) -> list[tuple[int, int]]:
    feature = source_feature(part)
    if feature is None:
        raise GeometryError("The part has no imported STEP, IGES or BREP geometry")
    path = Path(feature.source_file).expanduser()
    if not path.is_file():
        raise GeometryError(f"Geometry file does not exist: {path}")
    suffix = path.suffix.lower().lstrip(".")
    fmt = {"stp": "step", "step": "step", "igs": "iges", "iges": "iges", "brep": "brep"}.get(suffix)
    if fmt is None:
        raise GeometryError(f"Unsupported OCC geometry format: {path.suffix}")
    entities = gmsh.model.occ.importShapes(str(path), highestDimOnly=False, format=fmt)
    gmsh.model.occ.synchronize()
    if part.geometry_settings.heal_on_import:
        entities = _heal(gmsh, part, entities)
    return list(entities)


def _heal(gmsh, part, entities):
    settings = part.geometry_settings
    try:
        healed = gmsh.model.occ.healShapes(
            entities,
            tolerance=settings.tolerance,
            fixDegenerated=settings.remove_degenerate,
            fixSmallEdges=True,
            fixSmallFaces=True,
            sewFaces=settings.sew_faces,
            makeSolids=settings.make_solids,
        )
        gmsh.model.occ.synchronize()
        return healed or entities
    except Exception as exc:
        _LOG.warning("OCC healing failed; using imported entities unchanged: %s", exc)
        return entities
