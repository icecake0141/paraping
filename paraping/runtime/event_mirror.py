"""Shadow-mode helpers for incremental migration to runtime."""

import time
from typing import Any, Dict

from paraping.runtime.domain import PingEvent, PingStatus


def mirror_ping_event(monitor_state: Any, result: Dict[str, Any], status: PingStatus, host_id: int) -> None:
    """
    Mirror one ping event into runtime state.

    This function intentionally accepts ``Any`` for ``monitor_state`` so the caller
    can pass monitor state without introducing circular dependencies.
    """
    if status not in ("sent", "success", "slow", "fail"):
        return
    event_time = result.get("sent_time")
    if event_time is None:
        event_time = time.time()
    event = PingEvent(
        host_id=host_id,
        sequence=result.get("sequence", 0),
        status=status,
        sent_time=float(event_time),
        rtt_seconds=result.get("rtt"),
        ttl=result.get("ttl"),
    )
    monitor_state.apply_event(event)
