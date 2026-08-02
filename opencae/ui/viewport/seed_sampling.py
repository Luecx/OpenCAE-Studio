from __future__ import annotations

import numpy as np

from opencae.geometry.labels import parse_entity_label


def edge_overrides(seeds):
    values = {}
    for seed in seeds:
        if seed.seed_type != "Edge":
            continue
        for label in seed.targets:
            parsed = parse_entity_label(label)
            if parsed and parsed[0] == 1:
                values[parsed[1]] = seed
    return values


def divisions(patch, override, default):
    if override is not None:
        if override.method == "Number of divisions":
            return max(1, int(override.divisions))
        return max(1, round(polyline_length(patch) / max(override.size, 1e-12)))
    if default is not None:
        return max(1, round(polyline_length(patch) / max(default.size, 1e-12)))
    return None


def sample_polyline(patch, count):
    points = polyline(patch)
    if len(points) < 2:
        return [points[0]] if len(points) else []
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = cumulative[-1]
    if total <= 1e-14:
        return [points[0]]
    result = []
    for distance in np.linspace(0.0, total, count + 1):
        index = min(
            np.searchsorted(cumulative, distance, side="right") - 1,
            len(points) - 2,
        )
        span = cumulative[index + 1] - cumulative[index]
        factor = 0.0 if span <= 1e-14 else (
            distance - cumulative[index]
        ) / span
        result.append(
            points[index] * (1.0 - factor) + points[index + 1] * factor
        )
    return result


def polyline(patch):
    points = np.asarray(patch.points, dtype=float)
    lines = np.asarray(patch.lines).ravel()
    sequences = []
    index = 0
    while index < len(lines):
        count = int(lines[index])
        ids = lines[index + 1:index + 1 + count]
        if len(ids):
            sequences.append(points[ids])
        index += count + 1
    return np.vstack(sequences) if sequences else points


def polyline_length(patch):
    points = polyline(patch)
    if len(points) <= 1:
        return 0.0
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
