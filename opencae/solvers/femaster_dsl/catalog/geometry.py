from ..spec import CommandSpec

COMMANDS = (
    CommandSpec("MODEL", frozenset({"NAME"})),
    CommandSpec("NODE", frozenset({"NSET", "NAME"})),
    CommandSpec("ELEMENT", frozenset({"TYPE", "ELSET"}), frozenset({"TYPE"})),
    CommandSpec("NSET", frozenset({"NAME", "NSET", "GENERATE"}), frozenset({"NSET"})),
    CommandSpec("ELSET", frozenset({"NAME", "ELSET", "GENERATE"}), frozenset({"ELSET"})),
    CommandSpec("SURFACE", frozenset({"NAME", "TYPE"}), frozenset({"NAME"})),
    CommandSpec("SFSET", frozenset({"NAME", "SFSET"}), frozenset({"SFSET"})),
)
