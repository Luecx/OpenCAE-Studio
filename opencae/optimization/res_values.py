"""Maps parsed FEMaster result fields onto explicit solver entity ids."""

import numpy as np

from .res_field import ResField
from .res_format_error import ResFormatError


def dense_values(field: ResField, solver_ids: np.ndarray) -> np.ndarray:
    """Return field rows ordered by the supplied FEMaster solver ids."""

    if field.indices is not None:
        lookup = {int(row[0]): index for index, row in enumerate(field.indices)}
        try:
            rows = [lookup[int(value)] for value in solver_ids]
        except KeyError as exc:
            raise ResFormatError(
                f"Result field {field.name!r} has no row for solver id {exc.args[0]}"
            ) from exc
        return np.asarray(field.values[rows], dtype=float)

    ids = np.asarray(solver_ids, dtype=np.int64)
    if ids.size and (ids.min() < 0 or ids.max() >= len(field.values)):
        raise ResFormatError(
            f"Result field {field.name!r} has {len(field.values)} rows but "
            f"solver id range is {ids.min()}..{ids.max()}"
        )
    return np.asarray(field.values[ids], dtype=float)
