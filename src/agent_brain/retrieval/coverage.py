"""Coverage API for immutable retrieval generations.

The implementation lives with the generation publisher; this module provides a
small discoverable surface for callers that want inventory/status/check
without importing the larger index module.
"""

from agent_brain.retrieval.index import check_index, status_index
from agent_brain.retrieval.scan import iter_markdown_inventory, source_inventory

coverage_status = status_index
coverage_check = check_index

__all__ = [
    "check_index",
    "coverage_check",
    "coverage_status",
    "iter_markdown_inventory",
    "source_inventory",
    "status_index",
]
