"""Unit tests for v2 render state resolution."""

from collections import deque

from paraping_v2.engine import MonitorState
from paraping_v2.render_state import resolve_v2_render_state


def test_resolve_v2_render_state_returns_live_state_when_no_history() -> None:
    live_state = MonitorState(host_ids=[0], timeline_width=4)
    state, render_paused, snapshot_ts = resolve_v2_render_state(
        history_offset=0,
        history_buffer=deque(maxlen=4),
        live_state=live_state,
        paused=False,
    )
    assert state is live_state
    assert render_paused is False
    assert snapshot_ts is None


def test_resolve_v2_render_state_returns_snapshot_when_history_selected() -> None:
    live_state = MonitorState(host_ids=[0], timeline_width=4)
    snap_state = MonitorState(host_ids=[0], timeline_width=4)
    history_buffer = deque(
        [
            {"timestamp": 9.0, "state": MonitorState(host_ids=[0], timeline_width=4)},
            {"timestamp": 10.0, "state": snap_state},
        ],
        maxlen=4,
    )
    state, render_paused, snapshot_ts = resolve_v2_render_state(
        history_offset=1,
        history_buffer=history_buffer,
        live_state=live_state,
        paused=False,
    )
    assert state is history_buffer[0]["state"]
    assert render_paused is True
    assert snapshot_ts == 9.0
