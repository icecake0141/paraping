"""Unit tests for runtime render projection."""

from collections import deque

from paraping.runtime.domain import PingEvent
from paraping.runtime.engine import MonitorState
from paraping.runtime.render_projection import project_render_state, sync_render_host


def _build_render_host_buffers(width: int = 8) -> dict:
    return {
        "timeline": deque(maxlen=width),
        "rtt_history": deque(maxlen=width),
        "time_history": deque(maxlen=width),
        "ttl_history": deque(maxlen=width),
        "categories": {
            "success": deque(maxlen=width),
            "fail": deque(maxlen=width),
            "slow": deque(maxlen=width),
            "pending": deque(maxlen=width),
        },
    }


def _build_render_stats() -> dict:
    return {
        "success": 0,
        "fail": 0,
        "slow": 0,
        "total": 0,
        "rtt_sum": 0.0,
        "rtt_sum_sq": 0.0,
        "rtt_count": 0,
    }


def test_sync_render_host_projects_timeline_and_categories() -> None:
    state = MonitorState(host_ids=[0], timeline_width=8)
    state.apply_event(PingEvent(host_id=0, sequence=1, status="sent", sent_time=10.0))
    state.apply_event(PingEvent(host_id=0, sequence=1, status="success", sent_time=10.1, rtt_seconds=0.02, ttl=59))
    state.apply_event(PingEvent(host_id=0, sequence=2, status="sent", sent_time=11.0))

    render_buffers = _build_render_host_buffers()
    render_stats = _build_render_stats()
    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

    sync_render_host(state, 0, render_buffers, render_stats, symbols)

    assert list(render_buffers["timeline"]) == [".", "-"]
    assert list(render_buffers["categories"]["success"]) == [1]
    assert list(render_buffers["categories"]["pending"]) == [2]
    assert render_stats["success"] == 1
    assert render_stats["total"] == 1
    assert render_stats["rtt_count"] == 1


def test_project_render_state_builds_all_hosts() -> None:
    state = MonitorState(host_ids=[0, 1], timeline_width=4)
    state.apply_event(PingEvent(host_id=0, sequence=1, status="fail", sent_time=1.0))
    state.apply_event(PingEvent(host_id=1, sequence=2, status="sent", sent_time=2.0))

    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
    buffers, stats = project_render_state(state, symbols)

    assert list(buffers[0]["timeline"]) == ["x"]
    assert list(buffers[1]["timeline"]) == ["-"]
    assert stats[0]["fail"] == 1
    assert stats[1]["total"] == 0
