"""
Backward-compatible SequenceTracker import.

The implementation lives in ``paraping_v2.sequence_tracker`` as part of the
staged rewrite. This module keeps the public import path stable.
"""

from paraping_v2.sequence_tracker import SequenceTracker

__all__ = ["SequenceTracker"]
