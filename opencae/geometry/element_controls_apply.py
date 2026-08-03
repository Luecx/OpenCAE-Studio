from opencae.model.entities.mesh import ElementOrder
from .element_adjacency import propagation_closure
from .element_conversion import convert
from .element_records import records
from .element_targets import resolve_target_ids


def apply_control(part, control):
    elements = records(part.mesh); target = resolve_target_ids(part, control.target)
    selected = {eid for eid in target if elements[eid].topology == control.topology}
    affected = propagation_closure(part.mesh, selected)
    if selected: convert(part, selected, affected, control.order, control.formulation)
    return selected, affected


def apply_all_controls(part):
    elements = records(part.mesh)
    if elements:
        default = ElementOrder.SECOND if part.mesh.settings.element_order > 1 else ElementOrder.FIRST
        convert(part, set(), set(elements), default, "Standard")
    for control in part.mesh.element_controls: apply_control(part, control)


def requires_second_order(part):
    return part.mesh.settings.element_order > 1 or any(control.order == ElementOrder.SECOND for control in part.mesh.element_controls)
