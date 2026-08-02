from ..spec import CommandSpec

COMMANDS = (
    CommandSpec("MATERIAL", frozenset({"NAME", "MATERIAL"}), frozenset({"NAME"})),
    CommandSpec("ELASTIC", frozenset({"TYPE"}), variants=("ISOTROPIC", "GENISO", "ORTHOTROPIC", "ABD")),
    CommandSpec("HYPERELASTIC", frozenset({"NEO HOOKE", "NEOHOOKE", "NEO_HOOKE", "NEO-HOOKE"})),
    CommandSpec("DENSITY"),
    CommandSpec("THERMALEXPANSION"),
    CommandSpec("PROFILE", frozenset({"NAME", "PROFILE"}), frozenset({"NAME"})),
    CommandSpec(
        "SOLIDSECTION",
        frozenset({"ELSET", "MATERIAL", "MAT", "ORIENTATION"}),
        frozenset({"ELSET", "MATERIAL"}),
    ),
    CommandSpec(
        "SHELLSECTION",
        frozenset({"ELSET", "TYPE", "MATERIAL", "MAT", "THICKNESS", "ORIENTATION", "CSYSAXIS"}),
        frozenset({"ELSET", "TYPE"}),
        variants=("INTEGRATED", "ABD"),
    ),
    CommandSpec(
        "BEAMSECTION",
        frozenset({"ELSET", "MATERIAL", "MAT", "PROFILE"}),
        frozenset({"ELSET", "MATERIAL", "PROFILE"}),
    ),
    CommandSpec(
        "TRUSSSECTION",
        frozenset({"ELSET", "MATERIAL", "MAT", "AREA"}),
        frozenset({"ELSET", "MATERIAL", "AREA"}),
    ),
    CommandSpec("POINTMASS", frozenset({"NSET"}), frozenset({"NSET"})),
    CommandSpec(
        "FIELD",
        frozenset({"NAME", "TYPE", "COLS", "FILL"}),
        frozenset({"NAME", "TYPE", "COLS"}),
        variants=("NODE", "ELEMENT", "ELEMENT_NODAL", "ELEMENT_IP", "IP", "ELEMENT_MP", "MP"),
    ),
    CommandSpec(
        "ORIENTATION",
        frozenset({"NAME", "TYPE"}),
        frozenset({"NAME", "TYPE"}),
        variants=("RECTANGULAR", "CYLINDRICAL"),
    ),
)
