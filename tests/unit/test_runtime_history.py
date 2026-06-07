"""Unit tests for runtime history snapshot behavior."""

from collections import deque

from paraping.runtime.domain import PingEvent
from paraping.runtime.engine import MonitorState
from paraping.runtime.history import update_history_buffer


def test_update_history_buffer_appends_snapshot_on_interval() -> None:
    state = MonitorState(host_ids=[0], timeline_width=4)
    state.apply_event(PingEvent(host_id=0, sequence=1, status="sent", sent_time=10.0))
    state.apply_event(PingEvent(host_id=0, sequence=1, status="success", sent_time=10.1, rtt_seconds=0.01, ttl=64))

    history_buffer = deque(maxlen=10)
    last_snapshot_time, history_offset = update_history_buffer(
        history_buffer=history_buffer,
        state=state,
        now=11.0,
        last_snapshot_time=0.0,
        history_offset=0,
    )

    assert last_snapshot_time == 11.0
    assert history_offset == 0
    assert len(history_buffer) == 1
    snapshot_state = history_buffer[0]["state"]
    assert list(snapshot_state.timelines[0].symbols) == ["."]
    assert snapshot_state.stats[0].success == 1


def test_update_history_buffer_does_not_append_before_interval() -> None:
    state = MonitorState(host_ids=[0], timeline_width=4)
    history_buffer = deque(maxlen=10)

    last_snapshot_time, history_offset = update_history_buffer(
        history_buffer=history_buffer,
        state=state,
        now=0.5,
        last_snapshot_time=0.0,
        history_offset=0,
    )

    assert last_snapshot_time == 0.0
    assert history_offset == 0
    assert len(history_buffer) == 0
