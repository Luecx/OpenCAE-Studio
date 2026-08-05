"""Adapts persisted topology iterations to the generic Results frame model."""

from pathlib import Path

import numpy as np

from opencae.model.entities.jobs import ResultField


def is_topology_result(result) -> bool:
    return bool(
        result is not None
        and getattr(result, "metadata", {}).get("result_kind")
        == "topology_density"
    )


def topology_fields(result) -> list[ResultField]:
    """Create one generic elemental field descriptor for every saved iteration."""

    if not is_topology_result(result):
        return []
    values = []
    for frame in result.metadata.get("frames", ()):
        number = int(frame.get("number", len(values) + 1))
        values.append(
            ResultField(
                name="Topology Density",
                location="Elemental",
                components=1,
                metadata={
                    "step_id": 1,
                    "frame_id": number,
                    "frame_value": float(number),
                    "components": ("Density",),
                    "derived": (),
                    "density_file": str(frame.get("density_file", "")),
                    "objective": float(frame.get("objective", 0.0)),
                    "constraints": dict(frame.get("constraints", {})),
                    "maximum_density_change": float(
                        frame.get("maximum_density_change", 0.0)
                    ),
                    "converged": bool(frame.get("converged", False)),
                },
            )
        )
    return values


def topology_density(field) -> np.ndarray:
    path = Path(str(getattr(field, "metadata", {}).get("density_file", "")))
    if not path.is_file():
        raise FileNotFoundError(f"Topology density frame is unavailable: {path}")
    with np.load(path, allow_pickle=False) as values:
        key = "physical" if "physical" in values else "density"
        return np.asarray(values[key], dtype=float).ravel().copy()


def topology_scalar_range(field) -> tuple[float, float]:
    values = topology_density(field)
    finite = values[np.isfinite(values)]
    if not len(finite):
        return 0.0, 1.0
    minimum = float(finite.min())
    maximum = float(finite.max())
    if minimum == maximum:
        maximum = minimum + max(abs(minimum), 1.0) * 1.0e-12
    return minimum, maximum
