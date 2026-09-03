from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c):
    return (
        ActionSpec(A.ADD_INSTANCE,"Add Instance",I.INSTANCE,c.assembly.add_instance),
        ActionSpec(A.DUPLICATE_INSTANCE,"Duplicate",I.DUPLICATE,c.assembly.duplicate_instance),
        ActionSpec(A.TRANSFORM_INSTANCE,"Transform",I.MOVE,c.assembly.transform),
        ActionSpec(A.SUPPRESS_INSTANCE,"Suppress",I.DELETE,c.assembly.suppress_instance),
        ActionSpec(A.ASM_NODE_SET,"Node Set",I.NODE_SET,c.assembly.node_set),
        ActionSpec(A.ASM_ELEMENT_SET,"Element Set",I.ELEMENT_SET,c.assembly.element_set),
        ActionSpec(A.ASM_SURFACE,"Surface",I.SURFACE,c.assembly.surface),
        ActionSpec(A.ASM_CSYS,"Coordinate System",I.CSYS,c.assembly.coordinate_system),
        ActionSpec(A.ASM_RP,"Reference Point",I.RP,c.assembly.reference_point),
        ActionSpec(A.CONSTRAINT_KINEMATIC,"Kinematic",I.CONSTRAINT_KINEMATIC,lambda:c.assembly.constraint("Kinematic Coupling")),
        ActionSpec(A.CONSTRAINT_DISTRIBUTING,"Distributing",I.CONSTRAINT_DISTRIBUTING,lambda:c.assembly.constraint("Distributing Coupling")),
        ActionSpec(A.CONSTRAINT_TIE,"Tie",I.CONSTRAINT_TIE,lambda:c.assembly.constraint("Tie")),
        ActionSpec(A.CONSTRAINT_RIGID,"Rigid Body",I.CONSTRAINT_RIGID,lambda:c.assembly.constraint("Rigid Body")),
        ActionSpec(A.CONSTRAINT_CONNECTOR,"Connector",I.CONSTRAINT,lambda:c.assembly.constraint("Connector")),
        ActionSpec(A.CONSTRAINT_EQUATION,"Equation",I.CONSTRAINT_EQUATION,lambda:c.assembly.constraint("Equation")),
        ActionSpec(A.CONSTRAINT_MPC,"MPC",I.CONSTRAINT_MPC,lambda:c.assembly.constraint("MPC")),
    )
