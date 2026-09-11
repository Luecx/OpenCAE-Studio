from dataclasses import dataclass

from ...core import register_model_type
from .region import NodeRegion


@register_model_type("node_set")
@dataclass
class NodeSet(NodeRegion):
    """Legacy persisted alias for NodeRegion."""
