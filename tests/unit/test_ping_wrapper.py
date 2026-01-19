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
Unit tests for ping_wrapper error handling.
"""

import io
import json
import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Add parent directory to path to import ping_wrapper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.ping_wrapper import PingHelperError, main, ping_with_helper  # noqa: E402


class TestPingWithHelper(unittest.TestCase):
    """Tests for ping_with_helper error behavior."""

    @patch("paraping.ping_wrapper.os.path.exists", return_value=True)
    @patch("paraping.ping_wrapper.subprocess.run")
    def test_timeout_exit_code_returns_none(self, mock_run, _mock_exists):
        """Timeout (exit code 7) should return (None, None)."""
        mock_run.return_value = SimpleNamespace(
            returncode=7,
            stdout="",
            stderr="",
        )

        result = ping_with_helper("example.com")
        self.assertEqual(result, (None, None))

    @patch("paraping.ping_wrapper.os.path.exists", return_value=True)
    @patch("paraping.ping_wrapper.subprocess.run")
    def test_subprocess_timeout_returns_none(self, mock_run, _mock_exists):
        """subprocess.TimeoutExpired should return (None, None)."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["./ping_helper", "example.com", "1000"], timeout=2.0)

        result = ping_with_helper("example.com")
        self.assertEqual(result, (None, None))

    def test_helper_not_found_raises_file_not_found(self):
        """Missing helper binary should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError) as context:
            ping_with_helper("example.com", helper_path="/nonexistent/ping_helper")

        self.assertIn("ping_helper binary not found", str(context.exception))
        self.assertIn("/nonexistent/ping_helper", str(context.exception))

    @patch("paraping.ping_wrapper.os.path.exists", return_value=True)
    @patch("paraping.ping_wrapper.subprocess.run")
    def test_helper_execution_error_raises_with_stderr(self, mock_run, _mock_exists):
        """Non-timeout errors should raise PingHelperError with stderr."""
        mock_run.return_value = SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="permission denied",
        )

        with self.assertRaises(PingHelperError) as context:
            ping_with_helper("example.com")

        self.assertIn("return code 2", str(context.exception))
        self.assertIn("permission denied", str(context.exception))
        self.assertEqual(context.exception.returncode, 2)
        self.assertEqual(context.exception.stderr, "permission denied")

    @patch("paraping.ping_wrapper.os.path.exists", return_value=True)
    @patch("paraping.ping_wrapper.subprocess.run")
    def test_helper_execution_error_no_stderr(self, mock_run, _mock_exists):
        """Non-timeout errors without stderr should still raise PingHelperError."""
        mock_run.return_value = SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="",
        )

        with self.assertRaises(PingHelperError) as context:
            ping_with_helper("example.com")

        self.assertIn("return code 1", str(context.exception))
        self.assertEqual(context.exception.returncode, 1)
        self.assertEqual(context.exception.stderr, "")

    @patch("paraping.ping_wrapper.os.path.exists", return_value=True)
    @patch("paraping.ping_wrapper.subprocess.run")
    def test_success_case_with_rtt_and_ttl(self, mock_run, _mock_exists):
        """Successful ping should parse rtt_ms and ttl."""
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="rtt_ms=12.345 ttl=64\n",
            stderr="",
        )

        rtt_ms, ttl = ping_with_helper("example.com")
        self.assertAlmostEqual(rtt_ms, 12.345, places=3)
        self.assertEqual(ttl, 64)

    @patch("paraping.ping_wrapper.os.path.exists", return_value=True)
    @patch("paraping.ping_wrapper.subprocess.run")
    def test_success_case_no_output(self, mock_run, _mock_exists):
        """Success with no output should return (None, None)."""
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

        result = ping_with_helper("example.com")
        self.assertEqual(result, (None, None))


class TestPingWrapperMain(unittest.TestCase):
    """Tests for ping_wrapper CLI JSON output."""

    @patch("paraping.ping_wrapper.ping_with_helper")
    def test_main_success(self, mock_ping_with_helper):
        """CLI should output success JSON on successful ping."""
        mock_ping_with_helper.return_value = (12.345, 64)

        with (
            patch("sys.argv", ["ping_wrapper.py", "example.com"]),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 0)
        output = mock_stdout.getvalue()
        payload = json.loads(output)
        self.assertEqual(payload["host"], "example.com")
        self.assertAlmostEqual(payload["rtt_ms"], 12.345, places=3)
        self.assertEqual(payload["ttl"], 64)
        self.assertTrue(payload["success"])

    @patch("paraping.ping_wrapper.ping_with_helper")
    def test_main_timeout(self, mock_ping_with_helper):
        """CLI should output failure JSON on timeout."""
        mock_ping_with_helper.return_value = (None, None)

        with (
            patch("sys.argv", ["ping_wrapper.py", "example.com"]),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 1)
        output = mock_stdout.getvalue()
        payload = json.loads(output)
        self.assertEqual(payload["host"], "example.com")
        self.assertIsNone(payload["rtt_ms"])
        self.assertIsNone(payload["ttl"])
        self.assertFalse(payload["success"])

    @patch("paraping.ping_wrapper.ping_with_helper")
    def test_main_file_not_found(self, mock_ping_with_helper):
        """CLI should output error JSON when helper not found."""
        mock_ping_with_helper.side_effect = FileNotFoundError("ping_helper binary not found at /nonexistent/ping_helper")

        with (
            patch("sys.argv", ["ping_wrapper.py", "example.com"]),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 2)
        output = mock_stdout.getvalue()
        payload = json.loads(output)
        self.assertIn("error", payload)
        self.assertIn("ping_helper binary not found", payload["error"])
        self.assertFalse(payload["success"])

    @patch("paraping.ping_wrapper.ping_with_helper")
    def test_main_helper_error_with_stderr(self, mock_ping_with_helper):
        """CLI should output error JSON with stderr on helper errors."""
        mock_ping_with_helper.side_effect = PingHelperError(
            "ping_helper failed with return code 2: permission denied", returncode=2, stderr="permission denied"
        )

        with (
            patch("sys.argv", ["ping_wrapper.py", "example.com"]),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 3)
        output = mock_stdout.getvalue()
        payload = json.loads(output)
        self.assertIn("error", payload)
        self.assertIn("permission denied", payload["error"])
        self.assertFalse(payload["success"])

    @patch("paraping.ping_wrapper.ping_with_helper")
    def test_main_unexpected_exception(self, mock_ping_with_helper):
        """CLI should output error JSON on unexpected exceptions."""
        mock_ping_with_helper.side_effect = RuntimeError("Unexpected error")

        with (
            patch("sys.argv", ["ping_wrapper.py", "example.com"]),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 3)
        output = mock_stdout.getvalue()
        payload = json.loads(output)
        self.assertIn("error", payload)
        self.assertIn("Unexpected error", payload["error"])
        self.assertFalse(payload["success"])


if __name__ == "__main__":
    unittest.main()
