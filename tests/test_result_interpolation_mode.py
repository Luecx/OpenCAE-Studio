"""Contour interpolation selects the entire result rendering pipeline."""

from types import SimpleNamespace

import pytest

from opencae.ui.viewport import result_visualization as visualization


@pytest.mark.parametrize(
    ("setting", "enabled"),
    [
        ("classic", False),
        ("shape_functions", True),
        ("unknown", False),
    ],
)
def test_contour_interpolation_mode(setting, enabled):
    assert visualization._use_shape_functions(
        {"range": {"interpolation": setting}}
    ) is enabled


def test_default_result_interpolation_preserves_shape_function_renderer():
    assert visualization._use_shape_functions({}) is True
    assert visualization._use_shape_functions({"range": {}}) is True


@pytest.mark.parametrize("mode", ["classic", "shape_functions"])
def test_add_result_switches_between_classic_and_gpu(monkeypatch, mode):
    field = SimpleNamespace(name="DISP", metadata={"component": "Magnitude"})
    grid = object()
    actor = SimpleNamespace()
    plotter = SimpleNamespace(add_mesh=lambda supplied_grid, **kwargs: actor)
    shader_calls = []
    derived_calls = []

    monkeypatch.setattr(
        visualization, "_result_grids",
        lambda result, requested, options: (grid, grid),
    )
    monkeypatch.setattr(
        visualization, "_clim",
        lambda *args, **kwargs: (0.0, 10.0),
    )
    monkeypatch.setattr(
        visualization, "_render_scalar",
        lambda supplied, scalar, bounds: scalar,
    )
    monkeypatch.setattr(visualization, "_supports_result_shading", lambda supplied: False)
    monkeypatch.setattr(visualization, "scalar_bar_args", lambda *args, **kwargs: {})
    monkeypatch.setattr(visualization, "install_scalar_bar_end_caps", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        visualization,
        "_shader_color_field",
        lambda *args: derived_calls.append(args) or "component-then-magnitude",
    )
    monkeypatch.setattr(
        visualization,
        "install_element_shader_mapper",
        lambda *args: shader_calls.append(args),
    )

    options = {
        "range": {"interpolation": mode},
        "mesh_lines": False,
        "boundary_lines": False,
    }
    result_actor, returned_grid, *_ = visualization.add_result(
        plotter, object(), field, options
    )

    assert returned_grid is grid
    assert result_actor is actor
    assert actor._opencae_render_interpolation == mode
    if mode == "classic":
        assert not shader_calls
        assert not derived_calls
    else:
        assert len(shader_calls) == 1
        assert shader_calls[0][2] == "component-then-magnitude"
        assert len(derived_calls) == 1


@pytest.mark.parametrize(
    ("actor_mode", "requested_mode"),
    [
        ("classic", "shape_functions"),
        ("shape_functions", "classic"),
    ],
)
def test_animation_rebuilds_actor_when_renderer_mode_changes(
    monkeypatch, actor_mode, requested_mode
):
    actor = SimpleNamespace(_opencae_render_interpolation=actor_mode)
    monkeypatch.setattr(
        visualization,
        "_result_grids",
        lambda result, field, options: (object(), object()),
    )
    monkeypatch.setattr(visualization, "_clim", lambda *args, **kwargs: (0.0, 1.0))
    monkeypatch.setattr(
        visualization, "_render_scalar", lambda grid, scalar, bounds: scalar
    )
    # The update path must ask solution_scene to rebuild rather than calling
    # the wrong mapper's SetInputData method.
    assert visualization.update_result(
        actor,
        None,
        None,
        None,
        object(),
        options={"range": {"interpolation": requested_mode}},
    ) is None

def test_manual_lower_contour_bound_is_respected_for_nonnegative_fields():
    grid = SimpleNamespace(
        point_data={"STRESS:Mises": [0.0, 509.7]}, cell_data={}
    )
    settings = {
        "minimum": -500.0,
        "maximum": 509.7,
        "minimum_auto": False,
        "maximum_auto": False,
    }

    lower, upper = visualization._clim(
        grid, "STRESS:Mises", settings, nonnegative=True
    )

    assert lower < -500.0
    assert upper > 509.7


def test_automatic_lower_contour_bound_stays_zero_for_nonnegative_fields():
    grid = SimpleNamespace(
        point_data={"STRESS:Mises": [1.0, 509.7]}, cell_data={}
    )

    lower, upper = visualization._clim(
        grid, "STRESS:Mises", {}, nonnegative=True
    )

    assert lower == 0.0
    assert upper > 509.7
