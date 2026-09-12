"""Sequential project-file schema migrations."""

from copy import deepcopy

from .v23_to_v24 import migrate_v23_to_v24


_MIGRATIONS = {23: migrate_v23_to_v24}


def migrate_project_data(data, source_version: int, target_version: int):
    """Return a migrated copy by applying every registered schema step."""
    current = int(source_version)
    result = deepcopy(data)
    while current < int(target_version):
        migration = _MIGRATIONS.get(current)
        if migration is None:
            raise ValueError(
                f"No OpenCAE project migration is available from schema {current}"
            )
        result = migration(result)
        current += 1
    return result
