"""Tests for runtime event mirroring."""

from paraping.runtime.engine import MonitorState
from paraping.runtime.event_mirror import mirror_ping_event


def test_mirror_ping_event_ignores_non_ping_status() -> None:
    state = {"monitor_state": MonitorState(host_ids=[0], timeline_width=4)}
    mirror_ping_event(state["monitor_state"], {"host_id": 0, "sequence": 1}, "done", 0)
    assert list(state["monitor_state"].timelines[0].symbols) == []


def test_mirror_ping_event_tracks_pending_and_replaces_with_result() -> None:
    state = {"monitor_state": MonitorState(host_ids=[0], timeline_width=4)}
    mirror_ping_event(state["monitor_state"], {"host_id": 0, "sequence": 7, "sent_time": 100.0}, "sent", 0)
    mirror_ping_event(
        state["monitor_state"],
        {"host_id": 0, "sequence": 7, "rtt": 0.015, "ttl": 61, "sent_time": 100.1},
        "success",
        0,
    )
    timeline = state["monitor_state"].timelines[0]
    assert list(timeline.symbols) == ["."]
    assert state["monitor_state"].stats[0].success == 1
