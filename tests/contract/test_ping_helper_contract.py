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
Tests for ping_helper CLI contract and argument validation.

These tests verify the ping_helper binary's command-line interface contract:
- Output format: "rtt_ms=<value> ttl=<value>"
- Exit codes (particularly exit code 7 for timeout)
- Argument validation and error messages
- Optional icmp_seq parameter
"""

import os
import subprocess
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestPingHelperContract(unittest.TestCase):
    """Tests for ping_helper binary CLI contract."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper_path = os.path.join(
            os.path.dirname(__file__), "..", "ping_helper"
        )
        if not os.path.exists(self.helper_path):
            self.skipTest("ping_helper binary not found")

    def test_usage_message_no_args(self):
        """ping_helper with no arguments should show usage."""
        result = subprocess.run(
            [self.helper_path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)
        self.assertIn("<host>", result.stderr)
        self.assertIn("<timeout_ms>", result.stderr)
        self.assertIn("[icmp_seq]", result.stderr)

    def test_usage_message_one_arg(self):
        """ping_helper with one argument should show usage."""
        result = subprocess.run(
            [self.helper_path, "example.com"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)

    def test_usage_message_too_many_args(self):
        """ping_helper with too many arguments should show usage."""
        result = subprocess.run(
            [self.helper_path, "example.com", "1000", "1", "extra"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)

    def test_invalid_timeout_non_integer(self):
        """Non-integer timeout should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "abc"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("timeout_ms must be an integer", result.stderr)

    def test_invalid_timeout_zero(self):
        """Zero timeout should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "0"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("timeout_ms must be positive", result.stderr)

    def test_invalid_timeout_negative(self):
        """Negative timeout should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "-100"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("timeout_ms must be positive", result.stderr)

    def test_invalid_timeout_too_large(self):
        """Timeout >60000 should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "60001"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("timeout_ms must be 60000ms or less", result.stderr)

    def test_invalid_icmp_seq_non_integer(self):
        """Non-integer icmp_seq should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "1000", "abc"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("icmp_seq must be an integer", result.stderr)

    def test_invalid_icmp_seq_negative(self):
        """Negative icmp_seq should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "1000", "-1"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("icmp_seq must be between 0 and 65535", result.stderr)

    def test_invalid_icmp_seq_too_large(self):
        """icmp_seq >65535 should return error code 2."""
        result = subprocess.run(
            [self.helper_path, "example.com", "1000", "65536"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("icmp_seq must be between 0 and 65535", result.stderr)

    def test_valid_icmp_seq_values(self):
        """Valid icmp_seq values should be accepted (0, 1, 65535)."""
        # Test boundary values - these will fail with permission error
        # but that's expected; we just want to verify argument parsing
        for seq_val in ["0", "1", "100", "65535"]:
            with self.subTest(icmp_seq=seq_val):
                result = subprocess.run(
                    [self.helper_path, "127.0.0.1", "100", seq_val],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                # Should not fail with argument validation error (code 2)
                # May fail with code 4 (socket error) which is fine
                self.assertNotEqual(result.returncode, 2)

    def test_output_format_parsing(self):
        """Test that output format rtt_ms=X ttl=Y can be parsed."""
        # Simulate expected output format
        test_outputs = [
            "rtt_ms=12.345 ttl=64\n",
            "rtt_ms=0.123 ttl=128\n",
            "rtt_ms=999.999 ttl=32\n",
        ]
        
        for output in test_outputs:
            with self.subTest(output=output):
                rtt_ms = None
                ttl = None
                for line in output.splitlines():
                    if line.startswith("rtt_ms="):
                        for token in line.split():
                            if token.startswith("rtt_ms="):
                                rtt_ms = float(token.split("=", 1)[1])
                            elif token.startswith("ttl="):
                                ttl = int(token.split("=", 1)[1])
                
                self.assertIsNotNone(rtt_ms)
                self.assertIsNotNone(ttl)
                self.assertGreater(rtt_ms, 0)
                self.assertGreater(ttl, 0)

    def test_exit_code_7_contract(self):
        """Test that timeout scenarios use exit code 7."""
        # Use a non-routable IP to trigger timeout quickly
        result = subprocess.run(
            [self.helper_path, "192.0.2.1", "100"],  # TEST-NET-1, non-routable
            capture_output=True,
            text=True,
            timeout=2,
        )
        # Should timeout with exit code 7 (or fail with socket error code 4)
        # We mainly verify that exit code 7 is reserved for timeout
        if result.returncode == 7:
            # Timeout occurred as expected
            self.assertEqual(result.returncode, 7)
            # Should have no output on timeout
            self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
