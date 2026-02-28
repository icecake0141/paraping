"""Render state resolution for v2 live and history modes."""

from collections import deque
from typing import Any, Dict, Optional, Tuple

from paraping_v2.engine import MonitorState


def resolve_v2_render_state(
    history_offset: int,
    history_buffer: "deque[Dict[str, Any]]",
    live_state: MonitorState,
    paused: bool,
) -> Tuple[MonitorState, bool, Optional[float]]:
    """
    Resolve which v2 state should be rendered.

    Returns:
        (state_to_render, render_paused, snapshot_timestamp)
    """
    if 0 < history_offset <= len(history_buffer):
        snapshot = history_buffer[-(history_offset + 1)]
        return snapshot["state"], True, snapshot["timestamp"]
    return live_state, paused, None
