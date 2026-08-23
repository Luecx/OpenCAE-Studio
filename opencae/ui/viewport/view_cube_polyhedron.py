"""Build and transform the closed beveled polyhedron drawn by the ViewCube."""

from __future__ import annotations

from itertools import combinations, product
from math import cos, radians, sin, sqrt

Point3D = tuple[float, float, float]
Matrix3D = tuple[Point3D, Point3D, Point3D]
CubeFace = tuple[str, str, Point3D, tuple[Point3D, ...]]


def beveled_cube_faces(bevel: float = 0.30) -> tuple[CubeFace, ...]:
    """Return six square main, twelve edge, and eight corner faces."""
    inset = 1.0 - min(max(float(bevel), 0.04), 0.32)
    return (*_main_faces(inset), *_edge_faces(inset), *_corner_faces(inset))


def camera_view_matrix(position, focal_point, view_up) -> Matrix3D:
    """Build a world-to-view rotation from VTK camera vectors."""
    direction = _normalized(_subtract(focal_point, position), (0.0, 0.0, -1.0))
    up = _normalized(tuple(float(value) for value in view_up), (0.0, 1.0, 0.0))
    right = _normalized(_cross(direction, up), _fallback_right(direction))
    true_up = _normalized(_cross(right, direction), (0.0, 1.0, 0.0))
    return right, true_up, tuple(-value for value in direction)


def view_rotation(yaw: float, pitch: float, roll: float = 0.0) -> Matrix3D:
    """Return an Euler view matrix used by the standalone manual test."""
    cy, sy = cos(radians(yaw)), sin(radians(yaw))
    cp, sp = cos(radians(pitch)), sin(radians(pitch))
    cr, sr = cos(radians(roll)), sin(radians(roll))
    yaw_matrix: Matrix3D = ((cy, 0.0, sy), (0.0, 1.0, 0.0), (-sy, 0.0, cy))
    pitch_matrix: Matrix3D = ((1.0, 0.0, 0.0), (0.0, cp, -sp), (0.0, sp, cp))
    roll_matrix: Matrix3D = ((cr, -sr, 0.0), (sr, cr, 0.0), (0.0, 0.0, 1.0))
    return multiply_matrices(roll_matrix, multiply_matrices(pitch_matrix, yaw_matrix))


def transform(matrix: Matrix3D, point: Point3D) -> Point3D:
    """Transform one vector or point with a three-by-three matrix."""
    return tuple(
        sum(matrix[row][column] * point[column] for column in range(3))
        for row in range(3)
    )


def multiply_matrices(left: Matrix3D, right: Matrix3D) -> Matrix3D:
    """Compose two three-by-three matrices without a NumPy dependency."""
    return tuple(
        tuple(
            sum(left[row][index] * right[index][column] for index in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def _main_faces(inset: float) -> tuple[CubeFace, ...]:
    """Build the six square primary faces with conventional CAE labels."""
    labels = {
        (0, 1): "RIGHT", (0, -1): "LEFT",
        (1, 1): "BACK", (1, -1): "FRONT",
        (2, 1): "TOP", (2, -1): "BOTTOM",
    }
    corners = (
        (-inset, -inset), (inset, -inset),
        (inset, inset), (-inset, inset),
    )
    result = []
    for axis in range(3):
        other = tuple(index for index in range(3) if index != axis)
        for sign in (-1, 1):
            vertices = []
            for first, second in corners:
                point = [0.0, 0.0, 0.0]
                point[axis] = float(sign)
                point[other[0]], point[other[1]] = first, second
                vertices.append(tuple(point))
            normal = [0.0, 0.0, 0.0]
            normal[axis] = float(sign)
            result.append(("main", labels[(axis, sign)], tuple(normal), tuple(vertices)))
    return tuple(result)


def _edge_faces(inset: float) -> tuple[CubeFace, ...]:
    """Build the twelve rectangular faces connecting primary faces."""
    result = []
    for first_axis, second_axis in combinations(range(3), 2):
        free_axis = next(
            axis for axis in range(3) if axis not in (first_axis, second_axis)
        )
        for first_sign, second_sign in product((-1, 1), repeat=2):
            vertices = []
            for free, first, second in (
                (-inset, 1.0, inset), (-inset, inset, 1.0),
                (inset, inset, 1.0), (inset, 1.0, inset),
            ):
                point = [0.0, 0.0, 0.0]
                point[free_axis] = free
                point[first_axis] = first * first_sign
                point[second_axis] = second * second_sign
                vertices.append(tuple(point))
            normal = [0.0, 0.0, 0.0]
            normal[first_axis] = first_sign / sqrt(2.0)
            normal[second_axis] = second_sign / sqrt(2.0)
            result.append(("edge", "", tuple(normal), tuple(vertices)))
    return tuple(result)


def _corner_faces(inset: float) -> tuple[CubeFace, ...]:
    """Build eight triangles connected to their three neighboring edge faces."""
    result = []
    for signs in product((-1, 1), repeat=3):
        vertices = []
        for full_axis in range(3):
            point = [float(sign) * inset for sign in signs]
            point[full_axis] = float(signs[full_axis])
            vertices.append(tuple(point))
        normal = tuple(sign / sqrt(3.0) for sign in signs)
        result.append(("corner", "", normal, tuple(vertices)))
    return tuple(result)


def _subtract(left, right) -> Point3D:
    """Return a three-component vector difference."""
    return tuple(float(left[index]) - float(right[index]) for index in range(3))


def _cross(left: Point3D, right: Point3D) -> Point3D:
    """Return the right-handed cross product of two vectors."""
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalized(vector, fallback: Point3D) -> Point3D:
    """Normalize a vector while keeping degenerate camera states safe."""
    values = tuple(float(value) for value in vector)
    length = sqrt(sum(value * value for value in values))
    return tuple(value / length for value in values) if length > 1.0e-12 else fallback


def _fallback_right(direction: Point3D) -> Point3D:
    """Choose a stable screen-right vector when view-up is parallel to view."""
    candidate = (0.0, 1.0, 0.0) if abs(direction[2]) > 0.9 else (0.0, 0.0, 1.0)
    return _normalized(_cross(direction, candidate), (1.0, 0.0, 0.0))
