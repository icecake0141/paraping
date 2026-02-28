"""Unit tests for v2 to legacy state adapter."""

from collections import deque

from paraping_v2.domain import PingEvent
from paraping_v2.engine import MonitorState
from paraping_v2.legacy_adapter import project_legacy_state_from_v2, sync_legacy_host_from_v2


def _build_legacy_host_buffers(width: int = 8) -> dict:
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


def _build_legacy_stats() -> dict:
    return {
        "success": 0,
        "fail": 0,
        "slow": 0,
        "total": 0,
        "rtt_sum": 0.0,
        "rtt_sum_sq": 0.0,
        "rtt_count": 0,
    }


def test_sync_legacy_host_from_v2_projects_timeline_and_categories() -> None:
    state = MonitorState(host_ids=[0], timeline_width=8)
    state.apply_event(PingEvent(host_id=0, sequence=1, status="sent", sent_time=10.0))
    state.apply_event(PingEvent(host_id=0, sequence=1, status="success", sent_time=10.1, rtt_seconds=0.02, ttl=59))
    state.apply_event(PingEvent(host_id=0, sequence=2, status="sent", sent_time=11.0))

    legacy_buffers = _build_legacy_host_buffers()
    legacy_stats = _build_legacy_stats()
    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

    sync_legacy_host_from_v2(state, 0, legacy_buffers, legacy_stats, symbols)

    assert list(legacy_buffers["timeline"]) == [".", "-"]
    assert list(legacy_buffers["categories"]["success"]) == [1]
    assert list(legacy_buffers["categories"]["pending"]) == [2]
    assert legacy_stats["success"] == 1
    assert legacy_stats["total"] == 1
    assert legacy_stats["rtt_count"] == 1


def test_project_legacy_state_from_v2_builds_all_hosts() -> None:
    state = MonitorState(host_ids=[0, 1], timeline_width=4)
    state.apply_event(PingEvent(host_id=0, sequence=1, status="fail", sent_time=1.0))
    state.apply_event(PingEvent(host_id=1, sequence=2, status="sent", sent_time=2.0))

    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
    buffers, stats = project_legacy_state_from_v2(state, symbols)

    assert list(buffers[0]["timeline"]) == ["x"]
    assert list(buffers[1]["timeline"]) == ["-"]
    assert stats[0]["fail"] == 1
    assert stats[1]["total"] == 0
