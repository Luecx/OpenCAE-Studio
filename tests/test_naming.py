from dataclasses import dataclass

from opencae.model.naming import is_unique, next_name


@dataclass
class Named:
    name: str


def test_next_name_skips_existing_numbers_case_insensitively():
    values = [Named("NODE_SET-1"), Named("node_set-2"), Named("NODE_SET-4")]
    assert next_name("NODE_SET", values) == "NODE_SET-3"


def test_unique_name_allows_current_name_only():
    assert is_unique("Set-A", ("Set-A", "Set-B"), "Set-A")
    assert not is_unique("set-b", ("Set-A", "Set-B"), "Set-A")
