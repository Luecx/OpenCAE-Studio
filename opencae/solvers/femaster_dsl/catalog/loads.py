from ..spec import CommandSpec

VECTOR = frozenset({"LOAD_COLLECTOR", "ORIENTATION", "AMPLITUDE"})
COMMANDS = (
    CommandSpec("SUPPORT", frozenset({"SUPPORT_COLLECTOR", "ORIENTATION"}), frozenset({"SUPPORT_COLLECTOR"})),
    CommandSpec("CLOAD", VECTOR, frozenset({"LOAD_COLLECTOR"})),
    CommandSpec("DLOAD", VECTOR, frozenset({"LOAD_COLLECTOR"})),
    CommandSpec("PLOAD", frozenset({"LOAD_COLLECTOR", "AMPLITUDE"}), frozenset({"LOAD_COLLECTOR"})),
    CommandSpec("VLOAD", VECTOR, frozenset({"LOAD_COLLECTOR"})),
    CommandSpec("TLOAD", frozenset({"LOAD_COLLECTOR", "TEMPERATUREFIELD", "REFERENCETEMPERATURE"}), frozenset({"LOAD_COLLECTOR", "TEMPERATUREFIELD", "REFERENCETEMPERATURE"})),
    CommandSpec("INERTIALOAD", frozenset({"LOAD_COLLECTOR", "CONSIDER_POINT_MASSES"}), frozenset({"LOAD_COLLECTOR"})),
    CommandSpec("AMPLITUDE", frozenset({"NAME", "TYPE"}), frozenset({"NAME"}), variants=("STEP", "NEAREST", "LINEAR")),
)
