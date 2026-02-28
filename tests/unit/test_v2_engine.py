"""Unit tests for paraping_v2 engine behavior."""

from paraping_v2.domain import PingEvent
from paraping_v2.engine import MonitorState
from paraping_v2.rate_limit import validate_global_rate_limit


def test_pending_event_is_replaced_by_success() -> None:
    state = MonitorState(host_ids=[0], timeline_width=8)

    state.apply_event(PingEvent(host_id=0, sequence=10, status="sent", sent_time=1000.0))
    state.apply_event(
        PingEvent(
            host_id=0,
            sequence=10,
            status="success",
            sent_time=1000.1,
            rtt_seconds=0.012,
            ttl=57,
        )
    )

    timeline = state.timelines[0]
    assert list(timeline.symbols) == ["."]
    assert list(timeline.rtt_history) == [0.012]
    assert list(timeline.ttl_history) == [57]
    assert state.stats[0].success == 1
    assert state.stats[0].total == 1


def test_result_without_pending_is_appended() -> None:
    state = MonitorState(host_ids=[0], timeline_width=8)

    state.apply_event(
        PingEvent(
            host_id=0,
            sequence=1,
            status="fail",
            sent_time=1000.0,
        )
    )

    timeline = state.timelines[0]
    assert list(timeline.symbols) == ["x"]
    assert state.stats[0].fail == 1
    assert state.stats[0].total == 1


def test_global_rate_limit_validation_matches_current_behavior() -> None:
    valid, rate, message = validate_global_rate_limit(host_count=50, interval=1.0)
    assert valid is True
    assert rate == 50.0
    assert message == ""

    valid, rate, message = validate_global_rate_limit(host_count=100, interval=1.0)
    assert valid is False
    assert rate == 100.0
    assert "Rate limit (50 pings/sec)" in message
