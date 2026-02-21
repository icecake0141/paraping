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
# Review required for correctness, security, and licensing.

"""
Unit tests for global rate limit validation.

This module tests the rate limit enforcement to ensure ParaPing
never exceeds 50 pings/sec globally.
"""

import os
import sys
import unittest

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.core import MAX_GLOBAL_PINGS_PER_SECOND, validate_global_rate_limit


class TestGlobalRateLimit(unittest.TestCase):
    """Test global rate limit validation"""

    def test_rate_limit_exactly_at_limit_is_ok(self):
        """Test that exactly 50 pings/sec is allowed"""
        # 50 hosts at 1.0s interval = 50 pings/sec
        is_valid, rate, error = validate_global_rate_limit(50, 1.0)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 50.0)
        self.assertEqual(error, "")

    def test_rate_limit_just_over_limit_fails(self):
        """Test that 51 hosts at 1.0s interval fails"""
        # 51 hosts at 1.0s interval = 51 pings/sec (exceeds limit)
        is_valid, rate, error = validate_global_rate_limit(51, 1.0)
        self.assertFalse(is_valid)
        self.assertEqual(rate, 51.0)
        self.assertIn("Rate limit", error)
        self.assertIn("would be exceeded", error)
        self.assertIn("51.0 pings/sec", error)

    def test_rate_limit_below_limit_is_ok(self):
        """Test that rates below 50 pings/sec are allowed"""
        # 25 hosts at 1.0s interval = 25 pings/sec
        is_valid, rate, error = validate_global_rate_limit(25, 1.0)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 25.0)
        self.assertEqual(error, "")

    def test_rate_limit_short_interval_exceeds(self):
        """Test that short intervals can exceed rate limit"""
        # 50 hosts at 0.5s interval = 100 pings/sec (exceeds limit)
        is_valid, rate, error = validate_global_rate_limit(50, 0.5)
        self.assertFalse(is_valid)
        self.assertEqual(rate, 100.0)
        self.assertIn("Rate limit", error)
        self.assertIn("would be exceeded", error)

    def test_rate_limit_short_interval_at_limit(self):
        """Test that 25 hosts at 0.5s interval is exactly at limit"""
        # 25 hosts at 0.5s interval = 50 pings/sec
        is_valid, rate, error = validate_global_rate_limit(25, 0.5)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 50.0)
        self.assertEqual(error, "")

    def test_rate_limit_long_interval_is_ok(self):
        """Test that long intervals allow more hosts"""
        # 100 hosts at 2.0s interval = 50 pings/sec
        is_valid, rate, error = validate_global_rate_limit(100, 2.0)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 50.0)
        self.assertEqual(error, "")

    def test_rate_limit_very_long_interval_is_ok(self):
        """Test that very long intervals allow many hosts"""
        # 500 hosts at 10.0s interval = 50 pings/sec
        is_valid, rate, error = validate_global_rate_limit(500, 10.0)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 50.0)
        self.assertEqual(error, "")

    def test_rate_limit_single_host_is_ok(self):
        """Test that single host at any allowed interval is ok"""
        # 1 host at 0.1s interval = 10 pings/sec
        is_valid, rate, error = validate_global_rate_limit(1, 0.1)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 10.0)
        self.assertEqual(error, "")

    def test_rate_limit_invalid_zero_hosts(self):
        """Test that zero hosts is invalid"""
        is_valid, rate, error = validate_global_rate_limit(0, 1.0)
        self.assertFalse(is_valid)
        self.assertIn("Invalid parameters", error)

    def test_rate_limit_invalid_zero_interval(self):
        """Test that zero interval is invalid"""
        is_valid, rate, error = validate_global_rate_limit(10, 0.0)
        self.assertFalse(is_valid)
        self.assertIn("Invalid parameters", error)

    def test_rate_limit_invalid_negative_hosts(self):
        """Test that negative host count is invalid"""
        is_valid, rate, error = validate_global_rate_limit(-5, 1.0)
        self.assertFalse(is_valid)
        self.assertIn("Invalid parameters", error)

    def test_rate_limit_invalid_negative_interval(self):
        """Test that negative interval is invalid"""
        is_valid, rate, error = validate_global_rate_limit(10, -1.0)
        self.assertFalse(is_valid)
        self.assertIn("Invalid parameters", error)

    def test_rate_limit_error_message_includes_suggestions(self):
        """Test that error messages include numbered actionable suggestions"""
        is_valid, rate, error = validate_global_rate_limit(100, 1.0)
        self.assertFalse(is_valid)
        # Check that error includes the new actionable suggestion format
        self.assertIn("Suggestions:", error)
        self.assertIn("Reduce host count from 100 to", error)
        self.assertIn("Increase interval from", error)
        self.assertIn("Run multiple paraping instances with different host subsets", error)

    def test_rate_limit_fractional_hosts_at_limit(self):
        """Test boundary with fractional calculation"""
        # 30 hosts at 0.6s interval = 50 pings/sec
        is_valid, rate, error = validate_global_rate_limit(30, 0.6)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(rate, 50.0, places=5)
        self.assertEqual(error, "")

    def test_rate_limit_max_constant_is_50(self):
        """Test that the constant is correctly set to 50"""
        self.assertEqual(MAX_GLOBAL_PINGS_PER_SECOND, 50)


if __name__ == "__main__":
    unittest.main()
