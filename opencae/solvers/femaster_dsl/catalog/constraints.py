from ..spec import CommandSpec

COMMANDS = (
    CommandSpec("RBM", frozenset({"ELSET", "SET"})),
    CommandSpec(
        "COUPLING",
        frozenset({"MASTER", "TYPE", "SLAVE", "SFSET"}),
        frozenset({"MASTER", "TYPE"}),
        variants=("KINEMATIC", "STRUCTURAL"),
    ),
    CommandSpec(
        "TIE",
        frozenset({"MASTER", "SLAVE", "ADJUST", "DISTANCE"}),
        frozenset({"MASTER", "SLAVE"}),
    ),
    CommandSpec(
        "CONNECTOR",
        frozenset({"TYPE", "NSET1", "NSET2", "COORDINATESYSTEM"}),
        frozenset({"TYPE", "NSET1", "NSET2"}),
        variants=("BEAM", "HINGE", "CYLINDRICAL", "TRANSLATOR", "JOIN", "JOINRX"),
    ),
)
