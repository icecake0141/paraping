"""
ParaPing v2 core building blocks.

This package is introduced as an incremental rewrite target while preserving
the existing CLI and runtime behavior in the current implementation.
"""

from paraping_v2.constants import HISTORY_DURATION_MINUTES, MAX_HOST_THREADS, SNAPSHOT_INTERVAL_SECONDS
from paraping_v2.domain import HostInfo, HostStats, PingEvent
from paraping_v2.engine import MonitorState
from paraping_v2.history import create_state_snapshot_v2, update_history_buffer_v2
from paraping_v2.hosts import build_host_infos_v2, parse_host_file_line_v2, read_input_file_v2
from paraping_v2.legacy_adapter import project_legacy_state_from_v2, sync_legacy_host_from_v2
from paraping_v2.paging import compute_history_page_step_v2, get_cached_page_step_v2
from paraping_v2.rate_limit import MAX_GLOBAL_PINGS_PER_SECOND, validate_global_rate_limit
from paraping_v2.render_state import resolve_v2_render_state
from paraping_v2.scheduler import Scheduler
from paraping_v2.sequence_tracker import SequenceTracker
from paraping_v2.shadow import apply_shadow_v2_event
from paraping_v2.term_size import extract_timeline_width_from_layout_v2, normalize_term_size_v2

__all__ = [
    "HISTORY_DURATION_MINUTES",
    "SNAPSHOT_INTERVAL_SECONDS",
    "MAX_HOST_THREADS",
    "HostInfo",
    "HostStats",
    "PingEvent",
    "MonitorState",
    "create_state_snapshot_v2",
    "update_history_buffer_v2",
    "resolve_v2_render_state",
    "apply_shadow_v2_event",
    "parse_host_file_line_v2",
    "read_input_file_v2",
    "build_host_infos_v2",
    "compute_history_page_step_v2",
    "get_cached_page_step_v2",
    "normalize_term_size_v2",
    "extract_timeline_width_from_layout_v2",
    "project_legacy_state_from_v2",
    "sync_legacy_host_from_v2",
    "Scheduler",
    "SequenceTracker",
    "MAX_GLOBAL_PINGS_PER_SECOND",
    "validate_global_rate_limit",
]
