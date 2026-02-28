"""Global flood-protection validation for v2."""

from typing import Tuple

MAX_GLOBAL_PINGS_PER_SECOND = 50


def validate_global_rate_limit(host_count: int, interval: float) -> Tuple[bool, float, str]:
    """
    Validate that requested ping rate does not exceed the global cap.

    Returns:
        (is_valid, computed_rate, error_message)
    """
    if host_count <= 0 or interval <= 0:
        return False, 0.0, "Invalid parameters: host_count and interval must be positive"

    computed_rate = host_count / interval
    if computed_rate > MAX_GLOBAL_PINGS_PER_SECOND:
        max_hosts = int(MAX_GLOBAL_PINGS_PER_SECOND * interval)
        min_interval = host_count / MAX_GLOBAL_PINGS_PER_SECOND
        error_msg = (
            f"Error: Rate limit ({MAX_GLOBAL_PINGS_PER_SECOND} pings/sec) would be exceeded"
            f" (calculated: {computed_rate:.1f} pings/sec)\n"
            f"Suggestions:\n"
            f"  1. Reduce host count from {host_count} to {max_hosts} (at {interval}s interval)\n"
            f"  2. Increase interval from {interval}s to {min_interval:.1f}s (with {host_count} hosts)\n"
            f"  3. Run multiple paraping instances with different host subsets"
        )
        return False, computed_rate, error_msg
    return True, computed_rate, ""
