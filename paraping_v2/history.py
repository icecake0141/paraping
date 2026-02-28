"""History snapshot utilities for v2 monitor state."""

from collections import deque
from typing import Any, Dict, Tuple

from paraping_v2.engine import MonitorState

SNAPSHOT_INTERVAL_SECONDS = 1.0


def create_state_snapshot_v2(state: MonitorState, timestamp: float) -> Dict[str, Any]:
    """Create one immutable-style snapshot payload for v2 history."""
    return {
        "timestamp": timestamp,
        "state": state.clone(),
    }


def update_history_buffer_v2(
    history_buffer: "deque[Dict[str, Any]]",
    state: MonitorState,
    now: float,
    last_snapshot_time: float,
    history_offset: int,
) -> Tuple[float, int]:
    """Append snapshot at the same cadence as legacy history buffer updates."""
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    history_buffer.append(create_state_snapshot_v2(state, now))
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset
