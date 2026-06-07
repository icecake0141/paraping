"""History snapshot utilities for runtime monitor state."""

from collections import deque
from typing import Any, Dict, Tuple

from paraping.runtime.engine import MonitorState

SNAPSHOT_INTERVAL_SECONDS = 1.0


def create_state_snapshot(state: MonitorState, timestamp: float) -> Dict[str, Any]:
    """Create one immutable-style snapshot payload for runtime history."""
    return {
        "timestamp": timestamp,
        "state": state.clone(),
    }


def update_history_buffer(
    history_buffer: "deque[Dict[str, Any]]",
    state: MonitorState,
    now: float,
    last_snapshot_time: float,
    history_offset: int,
) -> Tuple[float, int]:
    """Append snapshot at the same cadence as removed history buffer updates."""
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    history_buffer.append(create_state_snapshot(state, now))
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset
