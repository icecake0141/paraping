"""Tests for v2 shadow event mirroring."""

from paraping_v2.engine import MonitorState
from paraping_v2.shadow import apply_shadow_v2_event


def test_shadow_apply_ignores_non_ping_status() -> None:
    state = {"v2_state": MonitorState(host_ids=[0], timeline_width=4)}
    apply_shadow_v2_event(state["v2_state"], {"host_id": 0, "sequence": 1}, "done", 0)
    assert list(state["v2_state"].timelines[0].symbols) == []


def test_shadow_apply_tracks_pending_and_replaces_with_result() -> None:
    state = {"v2_state": MonitorState(host_ids=[0], timeline_width=4)}
    apply_shadow_v2_event(state["v2_state"], {"host_id": 0, "sequence": 7, "sent_time": 100.0}, "sent", 0)
    apply_shadow_v2_event(
        state["v2_state"],
        {"host_id": 0, "sequence": 7, "rtt": 0.015, "ttl": 61, "sent_time": 100.1},
        "success",
        0,
    )
    timeline = state["v2_state"].timelines[0]
    assert list(timeline.symbols) == ["."]
    assert state["v2_state"].stats[0].success == 1
