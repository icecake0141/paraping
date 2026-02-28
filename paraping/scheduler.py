"""
Backward-compatible Scheduler import.

The implementation lives in ``paraping_v2.scheduler`` as part of the staged
rewrite. This module keeps the public import path stable.
"""

from paraping_v2.scheduler import Scheduler

__all__ = ["Scheduler"]
