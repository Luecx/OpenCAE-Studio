"""Regression tests for profile-driven real input-deck generation."""

from __future__ import annotations

from copy import deepcopy

from opencae.deck_formats import DeckProfile
from opencae.model.entities.resources.material_behaviors import DensityBehavior
from opencae.solvers.femaster import FEMasterAdapter
from opencae.ui.deck_format_manager.global_settings import DEFAULT_GLOBAL_SETTINGS
from opencae.ui.deck_format_manager.profile_state import build_profile
from opencae.ui.deck_format_manager.tree_catalog import TREE_SPEC


def _order(nodes=TREE_SPEC):
    state = {"__root__": tuple(node["key"] for node in nodes)}

    def visit(node):
        children = tuple(node.get("children", ()))
        if children:
            state[node["key"]] = tuple(child["key"] for child in children)
            for child in children:
                visit(child)

    for node in nodes:
        visit(node)
    return state


def _profile(states=None, *, order=None, settings=None):
    return build_profile(
        "FEMaster Test",
        "FEMaster",
        states or {},
        order or _order(),
        settings or DEFAULT_GLOBAL_SETTINGS,
    )


def test_custom_template_changes_real_femaster_deck(project_factory):
    data = project_factory(include_constraints=False)
    profile = _profile(
        {
            "materials.elastic.isotropic": {
                "template": (
                    "*ELASTIC, TYPE=ISOTROPIC\n"
                    "{poisson_ratio}, {youngs_modulus}"
                ),
                "enabled": True,
                "float_format": ".6f",
            }
        }
    )

    deck = FEMasterAdapter().write_deck_text(
        data["project"], data["analysis"], profile=profile
    )

    assert "*ELASTIC, TYPE=ISOTROPIC" in deck
    assert "0.300000, 210000.000000" in deck
    assert "210000, 0.3" not in deck


def test_runtime_for_loop_renders_flattened_nodes_and_elements(project_factory):
    data = project_factory(include_constraints=False)
    profile = _profile()

    deck = FEMasterAdapter().write_deck_text(
        data["project"], data["analysis"], profile=profile
    )

    assert "{for " not in deck
    assert "{endfor}" not in deck
    assert "*NODE, NSET=I1_NALL" in deck
    assert "*ELEMENT, TYPE=C3D4, ELSET=I1_E1" in deck
    assert "1, 0, 0, 0" in deck
    assert "1, 1, 2, 3, 4" in deck


def test_disabled_profile_record_is_removed_from_real_deck(project_factory):
    data = project_factory(include_constraints=False)
    data["material"].behaviors.append(DensityBehavior(value=7.85e-9))
    profile = _profile(
        {
            "materials.density": {
                "enabled": False,
                "float_format": ".6g",
            }
        }
    )

    deck = FEMasterAdapter().write_deck_text(
        data["project"], data["analysis"], profile=profile
    )

    assert "*MATERIAL, NAME=STEEL" in deck
    assert "*DENSITY" not in deck
    assert "*ELASTIC" in deck


def test_record_float_format_affects_real_mesh_output(project_factory):
    data = project_factory(include_constraints=False)
    profile = _profile(
        {
            "mesh.nodes": {
                "enabled": True,
                "float_format": ".6f",
            }
        }
    )

    deck = FEMasterAdapter().write_deck_text(
        data["project"], data["analysis"], profile=profile
    )

    assert "1, 0.000000, 0.000000, 0.000000" in deck
    assert "2, 1.000000, 0.000000, 0.000000" in deck


def test_profile_order_controls_material_behavior_order(project_factory):
    data = project_factory(include_constraints=False)
    data["material"].behaviors.append(DensityBehavior(value=7.85e-9))
    order = _order()
    material_order = list(order["materials"])
    material_order.remove("materials.density")
    material_order.insert(1, "materials.density")
    order["materials"] = tuple(material_order)
    profile = _profile(order=order)

    deck = FEMasterAdapter().write_deck_text(
        data["project"], data["analysis"], profile=profile
    )

    material = deck.index("*MATERIAL, NAME=STEEL")
    density = deck.index("*DENSITY", material)
    elastic = deck.index("*ELASTIC", material)
    assert material < density < elastic


def test_profile_roundtrip_preserves_runtime_semantics():
    source = _profile(
        {
            "loads.pressure": {
                "template": "*PLOAD, NAME={load_name}, SURFACE={surface}\n{pressure}",
                "enabled": False,
                "float_format": ".12e",
            }
        }
    )

    loaded = DeckProfile.from_dict(source.to_dict())

    assert loaded == source
    record = loaded.record("loads.pressure")
    assert record is not None
    assert not record.enabled
    assert record.float_format == ".12e"
    assert record.binding_template != ""


def test_builtin_femaster_path_remains_native(project_factory):
    data = project_factory(include_constraints=False)
    adapter = FEMasterAdapter()

    native = adapter.write_deck_text(data["project"], data["analysis"])
    explicit_builtin = adapter.write_deck_text(
        data["project"], data["analysis"], profile=None
    )

    assert explicit_builtin == native
