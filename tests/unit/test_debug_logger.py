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
Unit tests for debug_logger module - arrow key input troubleshooting.

DEBUG: These tests are for temporary debugging features and should be removed
after the arrow key issue is resolved.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import debug_logger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.debug_logger import (
    KeyInputDebugLogger,
    get_debug_logger,
    init_debug_logger,
    is_debug_enabled,
    shutdown_debug_logger,
)


class TestKeyInputDebugLogger(unittest.TestCase):
    """Test the KeyInputDebugLogger class."""

    def setUp(self):
        """Create a temporary log file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log")
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up temporary log file."""
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_logger_initialization(self):
        """Test logger can be initialized."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        self.assertIsNotNone(logger)
        self.assertEqual(logger.log_file_path, self.temp_file_path)
        self.assertIsNone(logger.log_file)  # Not started yet

    def test_start_session(self):
        """Test starting a debug logging session."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        logger.start_session()
        self.assertIsNotNone(logger.log_file)
        logger.close()

        # Verify session header was written
        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 0)
            header = json.loads(lines[0])
            self.assertEqual(header["event_type"], "SESSION_START")
            self.assertIn("timestamp_utc", header)
            self.assertIn("platform", header)

    def test_log_key_event(self):
        """Test logging a key input event."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        logger.start_session()

        logger.log_key_event(
            raw_bytes=b"\x1b[A",
            char_read="arrow_up",
            parsed_result="arrow_up",
            timing_info={"sequence_duration": 0.05},
            stdin_ready=True,
            notes="Test arrow up",
        )

        logger.close()

        # Verify event was logged
        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Find KEY_INPUT event
            key_event = None
            for line in lines:
                event = json.loads(line)
                if event["event_type"] == "KEY_INPUT":
                    key_event = event
                    break
            
            self.assertIsNotNone(key_event)
            self.assertEqual(key_event["char_read"], "arrow_up")
            self.assertEqual(key_event["parsed_result"], "arrow_up")
            self.assertEqual(key_event["raw_bytes_hex"], "1b5b41")  # ESC [ A
            self.assertTrue(key_event["stdin_ready"])

    def test_log_escape_sequence(self):
        """Test logging escape sequence details."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        logger.start_session()

        logger.log_escape_sequence(
            sequence="[A",
            complete=True,
            duration=0.03,
            timeout_occurred=False,
        )

        logger.close()

        # Verify event was logged
        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            esc_event = None
            for line in lines:
                event = json.loads(line)
                if event["event_type"] == "ESCAPE_SEQUENCE":
                    esc_event = event
                    break
            
            self.assertIsNotNone(esc_event)
            self.assertEqual(esc_event["sequence"], "[A")
            self.assertTrue(esc_event["complete"])
            self.assertFalse(esc_event["timeout_occurred"])

    def test_log_parse_result(self):
        """Test logging parse results."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        logger.start_session()

        logger.log_parse_result(
            input_sequence="[A",
            parsed_result="arrow_up",
            fallback_used=False,
        )

        logger.close()

        # Verify event was logged
        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            parse_event = None
            for line in lines:
                event = json.loads(line)
                if event["event_type"] == "PARSE_RESULT":
                    parse_event = event
                    break
            
            self.assertIsNotNone(parse_event)
            self.assertEqual(parse_event["input_sequence"], "[A")
            self.assertEqual(parse_event["parsed_result"], "arrow_up")
            self.assertTrue(parse_event["success"])

    def test_prompt_message_progression(self):
        """Test prompt message changes as keys are tested."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        logger.start_session()

        # Initial prompt
        prompt1 = logger.get_prompt_message()
        self.assertIn("arrow keys", prompt1.lower())

        # Simulate testing arrow up
        logger.log_key_event(
            raw_bytes=b"\x1b[A",
            char_read="arrow_up",
            parsed_result="arrow_up",
            timing_info={},
            stdin_ready=True,
        )

        prompt2 = logger.get_prompt_message()
        self.assertIn("1/4", prompt2)  # One arrow tested

        # Test all arrows
        for arrow in ["arrow_down", "arrow_left", "arrow_right"]:
            logger.log_key_event(
                raw_bytes=b"\x1b[X",
                char_read=arrow,
                parsed_result=arrow,
                timing_info={},
                stdin_ready=True,
            )

        prompt3 = logger.get_prompt_message()
        self.assertIn("complete", prompt3.lower())
        self.assertTrue(logger.is_test_complete())

        logger.close()

    def test_session_end(self):
        """Test session ending writes summary."""
        logger = KeyInputDebugLogger(self.temp_file_path)
        logger.start_session()
        logger.close()

        # Verify session end event was written
        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            end_event = json.loads(lines[-1])
            self.assertEqual(end_event["event_type"], "SESSION_END")


class TestDebugLoggerGlobalFunctions(unittest.TestCase):
    """Test global debug logger management functions."""

    def tearDown(self):
        """Ensure logger is shut down after each test."""
        shutdown_debug_logger()
        # Clean up any log file created
        if os.path.exists("paraping_debug_keys.log"):
            os.unlink("paraping_debug_keys.log")

    def test_init_and_get_debug_logger(self):
        """Test initializing and retrieving global logger."""
        self.assertIsNone(get_debug_logger())
        self.assertFalse(is_debug_enabled())

        init_debug_logger()
        logger = get_debug_logger()
        
        self.assertIsNotNone(logger)
        self.assertTrue(is_debug_enabled())

        shutdown_debug_logger()
        self.assertIsNone(get_debug_logger())
        self.assertFalse(is_debug_enabled())

    def test_shutdown_before_init(self):
        """Test shutting down when logger was never initialized."""
        # Should not raise exception
        shutdown_debug_logger()
        self.assertIsNone(get_debug_logger())


if __name__ == "__main__":
    unittest.main()
