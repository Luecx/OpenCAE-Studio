from __future__ import annotations

from .region_materialization import materialize_region


def write_assembly_regions(project, exported, writer, context):
    del exported  # occurrence maps are registered in the export context
    aliases = context.options.setdefault("region_aliases", {})
    entity_aliases = context.options.setdefault("entity_aliases", {})
    for region in project.assembly.regions:
        projection = region.preferred_projection
        if projection is None:
            writer.comment(f"Assembly region {region.name} has no preferred solver projection and was not exported")
            continue
        materialized = materialize_region(
            region.definition,
            projection,
            writer,
            context,
            owner=region,
            proposed_name=region.name,
            cache_key=("named-assembly-region", region.id),
        )
        aliases[region.name] = materialized.name
        entity_aliases[region.id] = materialized.name
