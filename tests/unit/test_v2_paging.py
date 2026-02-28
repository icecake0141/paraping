"""Unit tests for paging helpers in paraping_v2.paging."""

import os
from collections import deque
from unittest.mock import patch

from paraping_v2.paging import get_cached_page_step_v2


@patch("paraping.ui_render.get_terminal_size")
def test_get_cached_page_step_v2_uses_cache_when_term_size_unchanged(mock_term_size) -> None:
    mock_term_size.return_value = os.terminal_size((80, 24))
    host_infos = [
        {
            "id": 0,
            "alias": "host1",
            "host": "host1",
            "ip": "192.0.2.1",
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }
    ]
    buffers = {
        0: {
            "timeline": deque(["."] * 3, maxlen=10),
            "rtt_history": deque([0.01, 0.02, 0.03], maxlen=10),
            "time_history": deque([1000.0] * 3, maxlen=10),
            "ttl_history": deque([64, 64, 64], maxlen=10),
            "categories": {
                "success": deque([1], maxlen=10),
                "slow": deque([], maxlen=10),
                "fail": deque([], maxlen=10),
            },
        }
    }
    stats = {
        0: {
            "success": 3,
            "slow": 0,
            "fail": 0,
            "total": 3,
            "rtt_sum": 0.06,
            "rtt_sum_sq": 0.0,
            "rtt_count": 3,
        }
    }
    symbols = {"success": ".", "slow": "~", "fail": "x"}
    page_step, cached, _ = get_cached_page_step_v2(
        50,
        (80, 24),
        host_infos,
        buffers,
        stats,
        symbols,
        "none",
        "alias",
        "host",
        "all",
        0.5,
        False,
    )
    assert page_step == 50
    assert cached == 50
