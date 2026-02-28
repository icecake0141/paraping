"""Shadow-mode helpers for incremental migration to v2."""

import time
from typing import Any, Dict

from paraping_v2.domain import PingEvent


def apply_shadow_v2_event(v2_state: Any, result: Dict[str, Any], status: str, host_id: int) -> None:
    """
    Mirror one ping event into v2 state.

    This function intentionally accepts ``Any`` for ``v2_state`` so the caller
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
    v2_state.apply_event(event)
