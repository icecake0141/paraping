"""
ParaPing runtime core building blocks.

This package is introduced as an incremental rewrite target while preserving
the existing CLI and runtime behavior in the current implementation.
"""

from paraping.runtime.constants import HISTORY_DURATION_MINUTES, MAX_HOST_THREADS, SNAPSHOT_INTERVAL_SECONDS
from paraping.runtime.domain import HostInfo, HostStats, PingEvent
from paraping.runtime.engine import MonitorState
from paraping.runtime.event_mirror import mirror_ping_event
from paraping.runtime.history import create_state_snapshot, update_history_buffer
from paraping.runtime.hosts import build_host_infos, parse_host_file_line, read_input_file
from paraping.runtime.paging import compute_history_page_step, get_cached_page_step
from paraping.runtime.rate_limit import MAX_GLOBAL_PINGS_PER_SECOND, validate_global_rate_limit
from paraping.runtime.render_projection import project_render_state, sync_render_host
from paraping.runtime.render_state import resolve_render_state
from paraping.runtime.scheduler import Scheduler
from paraping.runtime.sequence_tracker import SequenceTracker
from paraping.runtime.term_size import extract_timeline_width_from_layout, normalize_term_size

__all__ = [
    "HISTORY_DURATION_MINUTES",
    "SNAPSHOT_INTERVAL_SECONDS",
    "MAX_HOST_THREADS",
    "HostInfo",
    "HostStats",
    "PingEvent",
    "MonitorState",
    "create_state_snapshot",
    "update_history_buffer",
    "resolve_render_state",
    "mirror_ping_event",
    "parse_host_file_line",
    "read_input_file",
    "build_host_infos",
    "compute_history_page_step",
    "get_cached_page_step",
    "normalize_term_size",
    "extract_timeline_width_from_layout",
    "project_render_state",
    "sync_render_host",
    "Scheduler",
    "SequenceTracker",
    "MAX_GLOBAL_PINGS_PER_SECOND",
    "validate_global_rate_limit",
]
