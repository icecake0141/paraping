#!/usr/bin/env python3
# Copyright 2025 icecake0141
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review for correctness and security.
"""
Unit tests for terminal size normalization in paraping.core
"""

import unittest
import os
import sys
from collections.abc import Sequence
from unittest.mock import patch

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from paraping.core import _normalize_term_size, _extract_timeline_width_from_layout


class TestTermSizeNormalization(unittest.TestCase):
    """Test cases for terminal size normalization helper"""

    def test_normalize_none_returns_none(self):
        """Test that None input returns None"""
        result = _normalize_term_size(None)
        self.assertIsNone(result)

    def test_normalize_tuple(self):
        """Test normalization of tuple (columns, lines)"""
        result = _normalize_term_size((80, 24))
        self.assertIsNotNone(result)
        self.assertEqual(result.columns, 80)
        self.assertEqual(result.lines, 24)

    def test_normalize_list(self):
        """Test normalization of list [columns, lines]"""
        result = _normalize_term_size([120, 40])
        self.assertIsNotNone(result)
        self.assertEqual(result.columns, 120)
        self.assertEqual(result.lines, 40)

    def test_normalize_tuple_like_sequence(self):
        """Test normalization of tuple-like sequences"""

        class TupleLikeSize(Sequence):
            """Tuple-like sequence wrapper for term size testing."""
            def __init__(self, columns, lines):
                self._values = (columns, lines)

            def __getitem__(self, index):
                return self._values[index]

            def __len__(self):
                return len(self._values)

        result = _normalize_term_size(TupleLikeSize(90, 20))
        self.assertIsNotNone(result)
        self.assertEqual(result.columns, 90)
        self.assertEqual(result.lines, 20)

    def test_normalize_dict(self):
        """Test normalization of dict with columns and lines keys"""
        result = _normalize_term_size({'columns': 100, 'lines': 30})
        self.assertIsNotNone(result)
        self.assertEqual(result.columns, 100)
        self.assertEqual(result.lines, 30)

    def test_normalize_object_with_attributes(self):
        """Test that objects with columns/lines attributes are passed through"""
        term_size = os.terminal_size((80, 24))
        result = _normalize_term_size(term_size)
        self.assertIsNotNone(result)
        self.assertEqual(result.columns, 80)
        self.assertEqual(result.lines, 24)

    def test_normalize_invalid_tuple_too_short(self):
        """Test that too-short tuples return None"""
        result = _normalize_term_size((80,))
        self.assertIsNone(result)

    def test_normalize_invalid_dict_missing_keys(self):
        """Test that dicts missing required keys return None"""
        result = _normalize_term_size({'columns': 80})
        self.assertIsNone(result)

    def test_normalize_invalid_type(self):
        """Test that invalid types return None"""
        result = _normalize_term_size("not a valid size")
        self.assertIsNone(result)

    def test_normalize_tuple_with_string_numbers(self):
        """Test normalization handles string numbers in tuples"""
        result = _normalize_term_size(("80", "24"))
        self.assertIsNotNone(result)
        self.assertEqual(result.columns, 80)
        self.assertEqual(result.lines, 24)


class TestTermSizeNormalizationInContext(unittest.TestCase):
    """Test terminal size normalization in the context of get_cached_page_step"""

    @patch('ui_render.get_terminal_size')
    def test_get_cached_page_step_with_tuple_last_term_size(self, mock_term_size):
        """Test get_cached_page_step works when last_term_size is a tuple"""
        from paraping.core import get_cached_page_step
        from collections import deque

        mock_term_size.return_value = os.terminal_size((80, 24))

        host_infos = [{
            "id": 0,
            "alias": "host1",
            "host": "host1",
            "ip": "192.0.2.1",
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }]
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

        # Call with last_term_size as a tuple (simulating older cached value)
        page_step, cached, new_term_size = get_cached_page_step(
            50,  # cached_page_step
            (80, 24),  # last_term_size as tuple
            host_infos, buffers, stats, symbols,
            "none", "alias", "host", "all", 0.5, False
        )

        # Should not crash and should return cached value since size unchanged
        self.assertEqual(page_step, 50)
        self.assertEqual(cached, 50)

    @patch('ui_render.get_terminal_size')
    def test_get_cached_page_step_recalculates_with_tuple_mismatch(self, mock_term_size):
        """Test get_cached_page_step recalculates when tuple size differs"""
        from paraping.core import get_cached_page_step
        from collections import deque

        mock_term_size.return_value = os.terminal_size((120, 40))

        host_infos = [{
            "id": 0,
            "alias": "host1",
            "host": "host1",
            "ip": "192.0.2.1",
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }]
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

        # Call with different last_term_size (as tuple)
        page_step, cached, new_term_size = get_cached_page_step(
            50,  # cached_page_step
            (80, 24),  # last_term_size as tuple (different from current 120x40)
            host_infos, buffers, stats, symbols,
            "none", "alias", "host", "all", 0.5, False
        )

        # Should recalculate and not return the cached 50
        self.assertNotEqual(page_step, 50)
        self.assertIsInstance(new_term_size, os.terminal_size)

    @patch('ui_render.get_terminal_size')
    def test_get_cached_page_step_handles_invalid_last_term_size(self, mock_term_size):
        """Test get_cached_page_step handles invalid last_term_size gracefully"""
        from paraping.core import get_cached_page_step
        from collections import deque

        mock_term_size.return_value = os.terminal_size((80, 24))

        host_infos = [{
            "id": 0,
            "alias": "host1",
            "host": "host1",
            "ip": "192.0.2.1",
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }]
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

        # Call with invalid last_term_size (string)
        page_step, cached, new_term_size = get_cached_page_step(
            50,  # cached_page_step
            "invalid",  # invalid last_term_size
            host_infos, buffers, stats, symbols,
            "none", "alias", "host", "all", 0.5, False
        )

        # Should not crash and should recalculate
        self.assertIsNotNone(page_step)
        self.assertIsInstance(new_term_size, os.terminal_size)


class TestExtractTimelineWidth(unittest.TestCase):
    """Test cases for timeline width extraction from layout results"""

    def test_extract_from_tuple(self):
        """Test extraction from tuple (width, label_width, timeline_width, hosts)"""
        layout = (80, 20, 57, 10)
        result = _extract_timeline_width_from_layout(layout, 80)
        self.assertEqual(result, 57)

    def test_extract_from_list(self):
        """Test extraction from list [width, label_width, timeline_width, hosts]"""
        layout = [120, 25, 92, 15]
        result = _extract_timeline_width_from_layout(layout, 120)
        self.assertEqual(result, 92)

    def test_extract_from_object_with_attribute(self):
        """Test extraction from object with timeline_width attribute"""
        from types import SimpleNamespace
        layout = SimpleNamespace(
            width=100,
            label_width=20,
            timeline_width=77,
            visible_hosts=12
        )
        result = _extract_timeline_width_from_layout(layout, 100)
        self.assertEqual(result, 77)

    def test_extract_fallback_short_tuple(self):
        """Test fallback when tuple is too short"""
        layout = (80, 20)
        result = _extract_timeline_width_from_layout(layout, 80)
        # Should fall back to main_width - 15 (TIMELINE_LABEL_ESTIMATE_WIDTH)
        self.assertEqual(result, 65)

    def test_extract_fallback_invalid_value(self):
        """Test fallback when timeline_width is invalid"""
        layout = (80, 20, "invalid", 10)
        result = _extract_timeline_width_from_layout(layout, 80)
        # Should fall back to main_width - 15
        self.assertEqual(result, 65)

    def test_extract_fallback_none_value(self):
        """Test fallback when timeline_width is None"""
        layout = (80, 20, None, 10)
        result = _extract_timeline_width_from_layout(layout, 80)
        # Should fall back to main_width - 15
        self.assertEqual(result, 65)

    def test_extract_ensures_minimum(self):
        """Test that result is always at least 1"""
        layout = (10, 5, 2, 5)
        result = _extract_timeline_width_from_layout(layout, 10)
        self.assertEqual(result, 2)
        self.assertGreaterEqual(result, 1)

    def test_extract_fallback_ensures_minimum(self):
        """Test that fallback result is always at least 1"""
        layout = (5, 3)
        result = _extract_timeline_width_from_layout(layout, 5)
        # main_width - 15 = -10, but should be clamped to 1
        self.assertEqual(result, 1)

    def test_extract_string_number_conversion(self):
        """Test that string numbers are converted to integers"""
        layout = (80, 20, "60", 10)
        result = _extract_timeline_width_from_layout(layout, 80)
        self.assertEqual(result, 60)
        self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main()
