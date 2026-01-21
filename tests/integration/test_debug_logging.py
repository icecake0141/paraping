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
Integration test for debug logging workflow.

DEBUG: This test is for temporary debugging features and should be removed
after the arrow key issue is resolved.

This test validates the end-to-end workflow of debug logging:
1. Initialization of debug logger
2. Key event capture
3. Prompt message generation
4. Log file writing
5. Proper cleanup
"""

import json
import os
import sys
import tempfile
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.debug_logger import (
    get_debug_logger,
    init_debug_logger,
    is_debug_enabled,
    shutdown_debug_logger,
)
from paraping.input_keys import parse_escape_sequence


class TestDebugLoggingWorkflow(unittest.TestCase):
    """Integration test for the complete debug logging workflow."""

    def setUp(self):
        """Create temporary log file."""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        )
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up logger and temp file."""
        shutdown_debug_logger()
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_complete_arrow_key_debugging_workflow(self):
        """
        Test the complete workflow a user would follow to debug arrow keys.

        This simulates:
        1. Starting ParaPing with --debug-keys
        2. Pressing various keys including arrows
        3. Following prompt messages
        4. Exiting and reviewing logs
        """
        # Step 1: Initialize debug mode (simulates --debug-keys flag)
        self.assertFalse(is_debug_enabled())
        init_debug_logger(self.temp_file_path)
        self.assertTrue(is_debug_enabled())

        logger = get_debug_logger()
        self.assertIsNotNone(logger)

        # Step 2: Get initial prompt message
        initial_prompt = logger.get_prompt_message()
        self.assertIn("arrow keys", initial_prompt.lower())
        self.assertIn("↑↓←→", initial_prompt)

        # Step 3: Simulate pressing regular keys
        logger.log_key_event(
            raw_bytes=b"q",
            char_read="q",
            parsed_result=None,
            timing_info={},
            stdin_ready=True,
            notes="Regular key",
        )

        # Step 4: Simulate pressing arrow up
        sequence_up = "[A"
        parsed_up = parse_escape_sequence(sequence_up)
        self.assertEqual(parsed_up, "arrow_up")

        logger.log_escape_sequence(
            sequence=sequence_up, complete=True, duration=0.03, timeout_occurred=False
        )

        logger.log_key_event(
            raw_bytes=b"\x1b[A",
            char_read="arrow_up",
            parsed_result="arrow_up",
            timing_info={"sequence_duration": 0.03},
            stdin_ready=True,
            notes="Arrow up pressed",
        )

        # Step 5: Check prompt updates
        prompt_after_one = logger.get_prompt_message()
        self.assertIn("1/4", prompt_after_one)

        # Step 6: Simulate pressing remaining arrows
        arrow_sequences = [("[B", "arrow_down"), ("[C", "arrow_right"), ("[D", "arrow_left")]

        for seq, arrow_name in arrow_sequences:
            parsed = parse_escape_sequence(seq)
            self.assertEqual(parsed, arrow_name)

            logger.log_escape_sequence(
                sequence=seq, complete=True, duration=0.03, timeout_occurred=False
            )

            logger.log_key_event(
                raw_bytes=f"\x1b{seq}".encode("latin-1"),
                char_read=arrow_name,
                parsed_result=arrow_name,
                timing_info={"sequence_duration": 0.03},
                stdin_ready=True,
                notes=f"{arrow_name} pressed",
            )

        # Step 7: Check test completion
        # The prompt updates automatically when all 4 arrows are tested
        final_prompt = logger.get_prompt_message()
        self.assertIn("complete", final_prompt.lower())
        self.assertTrue(logger.is_test_complete())

        # Step 8: Shutdown (simulates program exit)
        shutdown_debug_logger()
        self.assertFalse(is_debug_enabled())

        # Step 9: Verify log file contents
        self.assertTrue(os.path.exists(self.temp_file_path))

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Should have: SESSION_START, multiple KEY_INPUT, ESCAPE_SEQUENCE, PARSE_RESULT, SESSION_END
        self.assertGreater(len(lines), 5)

        # Verify first event is SESSION_START
        first_event = json.loads(lines[0])
        self.assertEqual(first_event["event_type"], "SESSION_START")
        self.assertIn("platform", first_event)

        # Verify last event is SESSION_END
        last_event = json.loads(lines[-1])
        self.assertEqual(last_event["event_type"], "SESSION_END")
        self.assertEqual(len(last_event["arrows_tested"]), 4)

        # Verify we captured all arrow key events
        arrow_events = []
        for line in lines:
            event = json.loads(line)
            if (
                event.get("event_type") == "KEY_INPUT"
                and event.get("parsed_result")
                and "arrow" in event.get("parsed_result", "")
            ):
                arrow_events.append(event)

        self.assertEqual(len(arrow_events), 4)

        # Verify all arrows were logged
        logged_arrows = {event["parsed_result"] for event in arrow_events}
        expected_arrows = {"arrow_up", "arrow_down", "arrow_left", "arrow_right"}
        self.assertEqual(logged_arrows, expected_arrows)

        # Verify raw bytes are captured
        for event in arrow_events:
            self.assertIn("raw_bytes_hex", event)
            self.assertTrue(event["raw_bytes_hex"].startswith("1b"))  # ESC

    def test_debug_mode_with_timeout_scenario(self):
        """Test logging when escape sequence times out."""
        init_debug_logger(self.temp_file_path)
        logger = get_debug_logger()

        # Simulate incomplete escape sequence (timeout scenario)
        logger.log_escape_sequence(
            sequence="[",  # Incomplete - missing the final character
            complete=False,
            duration=0.12,  # Exceeds typical timeout
            timeout_occurred=True,
        )

        logger.log_key_event(
            raw_bytes=b"\x1b[",
            char_read="\x1b",  # Returns ESC when sequence incomplete
            parsed_result=None,
            timing_info={"sequence_duration": 0.12},
            stdin_ready=True,
            notes="Timeout occurred",
        )

        shutdown_debug_logger()

        # Verify timeout is captured in log
        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        timeout_events = []
        for line in lines:
            event = json.loads(line)
            if event.get("event_type") == "ESCAPE_SEQUENCE":
                if event.get("timeout_occurred"):
                    timeout_events.append(event)

        self.assertEqual(len(timeout_events), 1)
        self.assertFalse(timeout_events[0]["complete"])
        self.assertGreater(timeout_events[0]["duration_seconds"], 0.1)


if __name__ == "__main__":
    unittest.main()
