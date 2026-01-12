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
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Add parent directory to path to import ping_wrapper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ping_wrapper import PingHelperError, ping_with_helper, main  # noqa: E402


class TestPingWithHelper(unittest.TestCase):
    """Tests for ping_with_helper error behavior."""

    @patch("ping_wrapper.os.path.exists", return_value=True)
    @patch("ping_wrapper.subprocess.run")
    def test_ping_with_helper_raises_with_stderr(self, mock_run, _mock_exists):
        """Non-timeout errors should include stderr in the exception."""
        mock_run.return_value = SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="permission denied",
        )

        with self.assertRaises(PingHelperError) as context:
            ping_with_helper("example.com")

        self.assertIn("return code 2", str(context.exception))
        self.assertIn("permission denied", str(context.exception))
        self.assertEqual(context.exception.stderr, "permission denied")


class TestPingWrapperMain(unittest.TestCase):
    """Tests for ping_wrapper CLI JSON output."""

    @patch("ping_wrapper.ping_with_helper")
    def test_main_includes_error_details(self, mock_ping_with_helper):
        """CLI JSON should include stderr details on failures."""
        mock_ping_with_helper.side_effect = PingHelperError(
            "ping_helper failed", returncode=2, stderr="permission denied"
        )

        with patch("sys.argv", ["ping_wrapper.py", "example.com"]), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as mock_stdout:
            with self.assertRaises(SystemExit) as context:
                main()

        self.assertEqual(context.exception.code, 3)
        output = mock_stdout.getvalue()
        payload = json.loads(output)
        self.assertIn("error", payload)
        self.assertIn("permission denied", payload["error"])


if __name__ == "__main__":
    unittest.main()
