"""Adapters between runtime state and render buffer/stat structures."""

from collections import deque
from typing import Any, Dict, Tuple


def _symbol_to_status(symbols: Dict[str, str]) -> Dict[str, str]:
    return {value: key for key, value in symbols.items()}


def sync_render_host(
    monitor_state: Any,
    host_id: int,
    host_buffer: Dict[str, Any],
    host_stats: Dict[str, Any],
    symbols: Dict[str, str],
) -> None:
    """
    Project one host's runtime state back into render buffer/stats dictionaries.

    This keeps current rendering and summary logic unchanged while event
    application gradually migrates to the runtime engine.
    """
    timeline = monitor_state.timelines[host_id]
    status_from_symbol = _symbol_to_status(symbols)

    host_buffer["timeline"].clear()
    host_buffer["timeline"].extend(timeline.symbols)

    host_buffer["rtt_history"].clear()
    host_buffer["rtt_history"].extend(timeline.rtt_history)

    host_buffer["time_history"].clear()
    host_buffer["time_history"].extend(timeline.time_history)

    host_buffer["ttl_history"].clear()
    host_buffer["ttl_history"].extend(timeline.ttl_history)

    for category in host_buffer["categories"].values():
        category.clear()

    for symbol, sequence in zip(timeline.symbols, timeline.sequence_history):
        status = status_from_symbol.get(symbol)
        if status is None:
            continue
        if sequence is None:
            continue
        if status in host_buffer["categories"]:
            host_buffer["categories"][status].append(sequence)

    stats = monitor_state.stats[host_id]
    host_stats["success"] = stats.success
    host_stats["slow"] = stats.slow
    host_stats["fail"] = stats.fail
    host_stats["total"] = stats.total
    host_stats["rtt_sum"] = stats.rtt_sum
    host_stats["rtt_sum_sq"] = stats.rtt_sum_sq
    host_stats["rtt_count"] = stats.rtt_count


def project_render_state(monitor_state: Any, symbols: Dict[str, str]) -> Tuple[Dict[int, Any], Dict[int, Any]]:
    """Build render-shaped render buffers/stats from a runtime state snapshot."""
    buffers: Dict[int, Any] = {}
    stats: Dict[int, Any] = {}
    for host_id, timeline in monitor_state.timelines.items():
        width = timeline.symbols.maxlen or 1
        host_buffer = {
            "timeline": deque(maxlen=width),
            "rtt_history": deque(maxlen=width),
            "time_history": deque(maxlen=width),
            "ttl_history": deque(maxlen=width),
            "categories": {status: deque(maxlen=width) for status in symbols},
        }
        host_stats = {
            "success": 0,
            "fail": 0,
            "slow": 0,
            "total": 0,
            "rtt_sum": 0.0,
            "rtt_sum_sq": 0.0,
            "rtt_count": 0,
        }
        sync_render_host(monitor_state, host_id, host_buffer, host_stats, symbols)
        buffers[host_id] = host_buffer
        stats[host_id] = host_stats
    return buffers, stats
