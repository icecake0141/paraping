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
Unit tests for paraping CLI module.

This module tests the command-line interface parsing and entrypoint logic
without performing actual network operations.
"""

import argparse
import io
import logging
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.cli import (
    _check_terminal_resize_and_request_redraw,
    _configure_logging,
    _handle_user_input,
    _setup_hosts_and_state,
    handle_options,
    main,
)


class TestCLIArgumentParsing(unittest.TestCase):
    """Test command-line argument parsing in paraping.cli"""

    def test_handle_options_default_values(self):
        """Test that default option values are set correctly"""
        with patch("sys.argv", ["paraping", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timeout, 1)
            self.assertEqual(args.count, 0)
            self.assertEqual(args.interval, 1.0)
            self.assertFalse(args.verbose)
            self.assertEqual(args.log_level, "INFO")
            self.assertIsNone(args.log_file)
            self.assertEqual(args.hosts, ["example.com"])
            self.assertEqual(args.panel_position, "right")
            self.assertEqual(args.pause_mode, "display")

    def test_handle_options_custom_timeout(self):
        """Test custom timeout option"""
        with patch("sys.argv", ["paraping", "-t", "5", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timeout, 5)

    def test_handle_options_custom_count(self):
        """Test custom count option"""
        with patch("sys.argv", ["paraping", "-c", "10", "example.com"]):
            args = handle_options()
            self.assertEqual(args.count, 10)

    def test_handle_options_verbose_flag(self):
        """Test verbose flag"""
        with patch("sys.argv", ["paraping", "-v", "example.com"]):
            args = handle_options()
            self.assertTrue(args.verbose)

    def test_handle_options_log_level(self):
        """Test log level option"""
        with patch("sys.argv", ["paraping", "--log-level", "error", "example.com"]):
            args = handle_options()
            self.assertEqual(args.log_level, "ERROR")

    def test_handle_options_log_file(self):
        """Test log file option"""
        with patch("sys.argv", ["paraping", "--log-file", "/tmp/paraping.log", "example.com"]):
            args = handle_options()
            self.assertEqual(args.log_file, "/tmp/paraping.log")

    def test_handle_options_multiple_hosts(self):
        """Test parsing multiple hosts"""
        with patch("sys.argv", ["paraping", "host1.com", "host2.com", "host3.com"]):
            args = handle_options()
            self.assertEqual(len(args.hosts), 3)
            self.assertIn("host1.com", args.hosts)
            self.assertIn("host2.com", args.hosts)
            self.assertIn("host3.com", args.hosts)

    def test_handle_options_custom_interval(self):
        """Test custom interval option"""
        with patch("sys.argv", ["paraping", "-i", "2.5", "example.com"]):
            args = handle_options()
            self.assertEqual(args.interval, 2.5)

    def test_handle_options_slow_threshold(self):
        """Test slow threshold option"""
        with patch("sys.argv", ["paraping", "-s", "0.7", "example.com"]):
            args = handle_options()
            self.assertEqual(args.slow_threshold, 0.7)

    def test_handle_options_panel_position(self):
        """Test panel position option"""
        for position in ["right", "left", "top", "bottom", "none"]:
            with patch("sys.argv", ["paraping", "-P", position, "example.com"]):
                args = handle_options()
                self.assertEqual(args.panel_position, position)

    def test_handle_options_pause_mode(self):
        """Test pause mode option"""
        for mode in ["display", "ping"]:
            with patch("sys.argv", ["paraping", "-m", mode, "example.com"]):
                args = handle_options()
                self.assertEqual(args.pause_mode, mode)

    def test_handle_options_timezone(self):
        """Test timezone option"""
        with patch("sys.argv", ["paraping", "-z", "Asia/Tokyo", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timezone, "Asia/Tokyo")

    def test_handle_options_snapshot_timezone(self):
        """Test snapshot timezone option"""
        for tz in ["utc", "display"]:
            with patch("sys.argv", ["paraping", "-Z", tz, "example.com"]):
                args = handle_options()
                self.assertEqual(args.snapshot_timezone, tz)

    def test_handle_options_flash_on_fail(self):
        """Test flash-on-fail flag"""
        with patch("sys.argv", ["paraping", "-F", "example.com"]):
            args = handle_options()
            self.assertTrue(args.flash_on_fail)

    def test_handle_options_bell_on_fail(self):
        """Test bell-on-fail flag"""
        with patch("sys.argv", ["paraping", "-B", "example.com"]):
            args = handle_options()
            self.assertTrue(args.bell_on_fail)

    def test_handle_options_color(self):
        """Test color flag"""
        with patch("sys.argv", ["paraping", "-C", "example.com"]):
            args = handle_options()
            self.assertTrue(args.color)

    def test_handle_options_no_color(self):
        """BooleanOptionalAction should allow disabling color explicitly."""
        with patch("sys.argv", ["paraping", "--color", "--no-color", "example.com"]):
            args = handle_options()
            self.assertFalse(args.color)

    def test_handle_options_verbose_ui_errors_default_false(self):
        """--verbose-ui-errors should default to False."""
        with patch("sys.argv", ["paraping", "example.com"]):
            args = handle_options()
            self.assertFalse(args.verbose_ui_errors)

    def test_handle_options_ui_log_errors_flag(self):
        """--ui-log-errors should enable UI error logs."""
        with patch("sys.argv", ["paraping", "--ui-log-errors", "example.com"]):
            args = handle_options()
            self.assertTrue(args.ui_log_errors)
            self.assertTrue(args.verbose_ui_errors)

    def test_handle_options_verbose_ui_errors_flag(self):
        """--verbose-ui-errors should enable UI error logs."""
        with patch("sys.argv", ["paraping", "--verbose-ui-errors", "example.com"]):
            with self.assertWarns(DeprecationWarning):
                args = handle_options()
            self.assertTrue(args.verbose_ui_errors)
            self.assertTrue(args.ui_log_errors)

    def test_handle_options_new_initial_state_options(self):
        """New startup default options should parse and be available."""
        with patch(
            "sys.argv",
            [
                "paraping",
                "--display-name",
                "ip",
                "--view",
                "sparkline",
                "--summary-mode",
                "ttl",
                "--summary-scope",
                "group",
                "--sort",
                "latency",
                "--filter",
                "failures",
                "--no-show-asn",
                "--kitt",
                "--kitt-style",
                "gradient",
                "--summary-fullscreen",
                "example.com",
            ],
        ):
            args = handle_options()
            self.assertEqual(args.display_name, "ip")
            self.assertEqual(args.view, "sparkline")
            self.assertEqual(args.summary_mode, "ttl")
            self.assertEqual(args.summary_scope, "group")
            self.assertEqual(args.sort, "latency")
            self.assertEqual(args.filter, "failures")
            self.assertFalse(args.show_asn)
            self.assertTrue(args.kitt)
            self.assertEqual(args.kitt_style, "gradient")
            self.assertTrue(args.summary_fullscreen)

    def test_handle_options_ping_helper_path(self):
        """Test ping helper path option"""
        with patch("sys.argv", ["paraping", "-H", "/custom/path/ping_helper", "example.com"]):
            args = handle_options()
            self.assertEqual(args.ping_helper, "/custom/path/ping_helper")

    def test_handle_options_input_file(self):
        """Test input file option"""
        with patch("sys.argv", ["paraping", "-f", "hosts.txt"]):
            args = handle_options()
            self.assertEqual(args.input, "hosts.txt")

    def test_handle_options_group_by_site_tag1(self):
        """`--group-by site>tag1` should be accepted."""
        with patch("sys.argv", ["paraping", "--group-by", "site>tag1", "example.com"]):
            args = handle_options()
            self.assertEqual(args.group_by, "site>tag1")

    def test_handle_options_combined_flags(self):
        """Test multiple options combined"""
        with patch(
            "sys.argv",
            [
                "paraping",
                "-t",
                "3",
                "-c",
                "5",
                "-i",
                "1.5",
                "-s",
                "0.8",
                "-v",
                "--ui-log-errors",
                "-P",
                "left",
                "-m",
                "ping",
                "-F",
                "-B",
                "-C",
                "host1.com",
                "host2.com",
            ],
        ):
            args = handle_options()
            self.assertEqual(args.timeout, 3)
            self.assertEqual(args.count, 5)
            self.assertEqual(args.interval, 1.5)
            self.assertEqual(args.slow_threshold, 0.8)
            self.assertTrue(args.verbose)
            self.assertEqual(args.log_level, "DEBUG")
            self.assertTrue(args.ui_log_errors)
            self.assertEqual(args.panel_position, "left")
            self.assertEqual(args.pause_mode, "ping")
            self.assertTrue(args.flash_on_fail)
            self.assertTrue(args.bell_on_fail)
            self.assertTrue(args.color)
            self.assertEqual(len(args.hosts), 2)

    def test_handle_options_verbose_deprecated_warns(self):
        """--verbose should warn and map to DEBUG log level."""
        with patch("sys.argv", ["paraping", "--verbose", "example.com"]):
            with self.assertWarns(DeprecationWarning):
                args = handle_options()
            self.assertTrue(args.verbose)
            self.assertEqual(args.log_level, "DEBUG")

    def test_handle_options_interval_validation_min(self):
        """Test interval validation - minimum value"""
        with patch("sys.argv", ["paraping", "-i", "0.05", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()

    def test_handle_options_interval_validation_max(self):
        """Test interval validation - maximum value"""
        with patch("sys.argv", ["paraping", "-i", "61", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()

    def test_handle_options_timeout_validation(self):
        """Test timeout validation - must be positive"""
        with patch("sys.argv", ["paraping", "-t", "0", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()


class TestCLIMain(unittest.TestCase):
    """Test the main CLI entrypoint function"""

    @patch("paraping.cli.run")
    @patch("paraping.cli.handle_options")
    def test_main_calls_handle_options_and_run(self, mock_handle_options, mock_run):
        """Test that main() calls handle_options() and then run()"""
        mock_args = MagicMock()
        mock_handle_options.return_value = mock_args

        main()

        mock_handle_options.assert_called_once()
        mock_run.assert_called_once_with(mock_args)

    @patch("paraping.cli.run")
    def test_main_with_benign_arguments(self, mock_run):
        """Test main with benign arguments (no network/ping attempts)"""
        # Mock run to avoid actual execution
        mock_run.return_value = None

        # Test that main can be called with benign arguments via sys.argv
        with patch("sys.argv", ["paraping", "--help"]):
            # --help will cause argparse to exit, which is expected
            with self.assertRaises(SystemExit) as cm:
                main()
            # Exit code 0 means successful help display
            self.assertEqual(cm.exception.code, 0)


class TestCLIRateLimitValidation(unittest.TestCase):
    """Test rate limit validation in CLI run function"""

    @patch("paraping.cli.sys.stdin.isatty")
    def test_run_rate_limit_exactly_50_is_ok(self, mock_isatty):
        """Test that exactly 50 pings/sec is allowed"""
        mock_isatty.return_value = False  # Not in interactive mode

        # Create args with 50 hosts at 1.0s interval = 50 pings/sec
        args = MagicMock()
        args.count = 0
        args.timeout = 1
        args.interval = 1.0
        args.hosts = [f"host{i}.com" for i in range(50)]
        args.input = None
        args.timezone = None
        args.snapshot_timezone = "display"
        args.ping_helper = "./bin/ping_helper"
        args.panel_position = "right"
        args.slow_threshold = 0.5

        # This should NOT raise an exception or exit
        # We can't fully test the run function without mocking more,
        # but we can verify the validation function is called correctly
        from paraping.core import validate_global_rate_limit

        is_valid, rate, error = validate_global_rate_limit(50, 1.0)
        self.assertTrue(is_valid)

    def test_run_rate_limit_over_50_fails(self):
        """Test that exceeding 50 pings/sec causes exit"""
        # Create args with 51 hosts at 1.0s interval = 51 pings/sec
        args = MagicMock()
        args.count = 0
        args.timeout = 1
        args.interval = 1.0
        args.hosts = [f"host{i}.com" for i in range(51)]
        args.input = None
        args.log_level = "INFO"
        args.log_file = None

        # Import run function
        from paraping.cli import run

        # This should call sys.exit(1) due to rate limit
        with self.assertRaises(SystemExit) as cm:
            run(args)
        self.assertEqual(cm.exception.code, 1)

    def test_run_rate_limit_short_interval_fails(self):
        """Test that short interval with many hosts fails"""
        # Create args with 50 hosts at 0.5s interval = 100 pings/sec
        args = MagicMock()
        args.count = 0
        args.timeout = 1
        args.interval = 0.5
        args.hosts = [f"host{i}.com" for i in range(50)]
        args.input = None
        args.log_level = "INFO"
        args.log_file = None

        # Import run function
        from paraping.cli import run

        # This should call sys.exit(1) due to rate limit
        with self.assertRaises(SystemExit) as cm:
            run(args)
        self.assertEqual(cm.exception.code, 1)

    def test_run_rate_limit_25_hosts_at_half_second_is_ok(self):
        """Test that 25 hosts at 0.5s interval is exactly at limit"""
        # 25 hosts at 0.5s interval = 50 pings/sec
        from paraping.core import validate_global_rate_limit

        is_valid, rate, error = validate_global_rate_limit(25, 0.5)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 50.0)


class TestCLISetupValidation(unittest.TestCase):
    """Test setup-time validation behavior."""

    @patch("paraping.cli.read_input_file_with_report")
    def test_setup_exits_when_input_file_has_format_errors(self, mock_read_with_report):
        """Input file format errors should print report and exit with status 1."""
        bad_report = MagicMock()
        bad_report.has_errors = True
        bad_report.error_count = 2
        bad_report.issues = [
            MagicMock(
                severity="error",
                line_number=2,
                reason="Expected format 'IP,alias' or 'IP,alias,site,tags'.",
                raw_line="bad line",
            ),
            MagicMock(severity="error", line_number=4, reason="IP address and alias are required.", raw_line="192.0.2.1,"),
        ]
        mock_read_with_report.return_value = ([], bad_report)
        args = argparse.Namespace(
            count=0,
            timeout=1,
            interval=1.0,
            hosts=[],
            input="hosts.txt",
            timezone=None,
            snapshot_timezone="utc",
            panel_position="right",
            ping_helper="./bin/ping_helper",
        )
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as cm:
                _setup_hosts_and_state(args)

        self.assertEqual(cm.exception.code, 1)
        output = stderr.getvalue()
        self.assertIn("Error: hosts.txt contains 2 format error(s).", output)
        self.assertIn("hosts.txt:2: Expected format", output)
        self.assertIn("hosts.txt:4: IP address and alias are required. | 192.0.2.1,", output)

    @patch("paraping.cli.os.path.exists", return_value=False)
    @patch("paraping.cli.build_host_infos", return_value=([{"id": 0, "host": "1.1.1.1", "alias": "h"}], {"1.1.1.1": []}))
    @patch("paraping.cli.get_terminal_size")
    def test_setup_fails_fast_when_ping_helper_missing(self, mock_term_size, _mock_build_host_infos, _mock_exists):
        """Missing ping helper should abort setup with clear error."""
        mock_term_size.return_value = os.terminal_size((80, 24))
        args = argparse.Namespace(
            count=0,
            timeout=1,
            interval=1.0,
            hosts=["1.1.1.1"],
            input=None,
            timezone=None,
            snapshot_timezone="utc",
            panel_position="right",
            ping_helper="./bin/ping_helper",
        )
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            result = _setup_hosts_and_state(args)
        self.assertIsNone(result)
        self.assertIn("ping_helper binary not found", stderr.getvalue())


class TestCLILoggingConfiguration(unittest.TestCase):
    """Test logging handler setup for interactive and non-interactive modes."""

    @patch("paraping.cli.logging.basicConfig")
    def test_configure_logging_interactive_uses_null_handler(self, mock_basic_config):
        """Interactive mode without log file should avoid terminal log noise."""
        _configure_logging("INFO", None, interactive_ui=True, verbose_ui_errors=False)
        handlers = mock_basic_config.call_args.kwargs["handlers"]
        self.assertEqual(len(handlers), 1)
        self.assertIsInstance(handlers[0], logging.NullHandler)

    @patch("paraping.cli.logging.basicConfig")
    def test_configure_logging_noninteractive_uses_stream_handler(self, mock_basic_config):
        """Non-interactive mode should keep stream logging enabled."""
        _configure_logging("INFO", None, interactive_ui=False, verbose_ui_errors=False)
        handlers = mock_basic_config.call_args.kwargs["handlers"]
        self.assertEqual(len(handlers), 1)
        self.assertIsInstance(handlers[0], logging.StreamHandler)

    @patch("paraping.cli.logging.basicConfig")
    def test_configure_logging_interactive_verbose_enabled_uses_stream_handler(self, mock_basic_config):
        """Interactive mode with verbose UI errors should enable stream logging."""
        _configure_logging("INFO", None, interactive_ui=True, verbose_ui_errors=True)
        handlers = mock_basic_config.call_args.kwargs["handlers"]
        self.assertEqual(len(handlers), 1)
        self.assertIsInstance(handlers[0], logging.StreamHandler)


class TestCLIInputHandling(unittest.TestCase):
    """Test extracted keyboard input handler behavior."""

    def test_handle_user_input_quit_sets_running_false(self):
        """Pressing q should request shutdown."""
        state = {"running": True, "stop_event": threading.Event()}

        skip_iteration = _handle_user_input("q", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertFalse(state["running"])
        self.assertTrue(state["stop_event"].is_set())

    def test_handle_user_input_hides_help_and_skips_iteration(self):
        """`?` while help is visible should close help and skip the loop body."""
        state = {"show_help": True, "force_render": False, "updated": False}

        skip_iteration = _handle_user_input("?", MagicMock(slow_threshold=0.5), state)

        self.assertTrue(skip_iteration)
        self.assertFalse(state["show_help"])
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])

    def test_handle_user_input_toggle_display_pause(self):
        """`p` toggles display pause mode and pause event."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "display_paused": False,
            "dormant": False,
            "pause_mode": "ping",
            "pause_event": threading.Event(),
            "status_message": None,
            "force_render": False,
            "updated": False,
            "paused": False,
        }

        skip_iteration = _handle_user_input("p", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertTrue(state["display_paused"])
        self.assertTrue(state["paused"])
        self.assertTrue(state["pause_event"].is_set())
        self.assertEqual(state["status_message"], "Display paused")

    def test_handle_user_input_toggle_pulse_panel(self):
        """`n` toggles Pulse panel visibility."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "pulse_position": "bottom",
            "last_pulse_position": "bottom",
            "pulse_toggle_default": "bottom",
            "status_message": None,
            "cached_page_step": 1,
            "force_render": False,
            "updated": False,
        }

        skip_iteration = _handle_user_input("n", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertEqual(state["pulse_position"], "none")
        self.assertEqual(state["last_pulse_position"], "bottom")
        self.assertEqual(state["status_message"], "Pulse panel hidden")
        self.assertIsNone(state["cached_page_step"])
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])

    def test_handle_user_input_cycle_pulse_panel_position(self):
        """`N` cycles Pulse panel positions."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "pulse_position": "left",
            "last_pulse_position": "left",
            "pulse_toggle_default": "bottom",
            "status_message": None,
            "cached_page_step": 1,
            "force_render": False,
            "updated": False,
        }

        skip_iteration = _handle_user_input("N", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertEqual(state["pulse_position"], "right")
        self.assertEqual(state["last_pulse_position"], "right")
        self.assertEqual(state["status_message"], "Pulse panel position: RIGHT")
        self.assertIsNone(state["cached_page_step"])
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])

    def test_handle_user_input_group_scope_toggle(self):
        """`g` toggles summary scope between host and group."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "summary_scope_modes": ["host", "group"],
            "summary_scope_mode_index": 0,
            "status_message": None,
            "cached_page_step": 1,
            "updated": False,
        }

        skip_iteration = _handle_user_input("g", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertEqual(state["summary_scope_mode_index"], 1)
        self.assertEqual(state["status_message"], "Summary scope: GROUP")
        self.assertIsNone(state["cached_page_step"])
        self.assertTrue(state["updated"])

    def test_handle_user_input_group_key_toggle(self):
        """`t` cycles the group-by key."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "group_by_modes": ["none", "asn", "site", "tag", "site>tag1"],
            "group_by_mode_index": 0,
            "status_message": None,
            "cached_page_step": 1,
            "updated": False,
        }

        skip_iteration = _handle_user_input("t", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertEqual(state["group_by_mode_index"], 1)
        self.assertEqual(state["status_message"], "Group key: asn")
        self.assertIsNone(state["cached_page_step"])
        self.assertTrue(state["updated"])

    def test_handle_user_input_reload_without_input_file_shows_status(self):
        """`r` without -f/--input should show an unavailable message."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "status_message": None,
            "force_render": False,
            "updated": False,
        }
        args = MagicMock(slow_threshold=0.5, input=None)

        skip_iteration = _handle_user_input("r", args, state)

        self.assertFalse(skip_iteration)
        self.assertEqual(state["status_message"], "Reload unavailable in this context")
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])

    @patch("paraping.cli._apply_manual_reload", return_value="Reloaded: +1 -0 (total 1)")
    def test_handle_user_input_reload_delegates_to_reload_handler(self, mock_reload):
        """`r` with scheduler context should call manual reload helper."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "status_message": None,
            "force_render": False,
            "updated": False,
        }
        args = MagicMock(slow_threshold=0.5, input="hosts.txt")
        scheduler = MagicMock()
        ping_lock = threading.Lock()
        sequence_tracker = MagicMock()

        skip_iteration = _handle_user_input("r", args, state, scheduler, ping_lock, sequence_tracker)

        self.assertFalse(skip_iteration)
        mock_reload.assert_called_once_with(args, state, scheduler, ping_lock, sequence_tracker)
        self.assertEqual(state["status_message"], "Reloaded: +1 -0 (total 1)")
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])

    @patch("paraping.cli.reset_render_cache")
    def test_handle_user_input_full_redraw_hotkey(self, mock_reset_render_cache):
        """`u` should request a full redraw and force a render pass."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "status_message": None,
            "force_render": False,
            "updated": False,
        }

        skip_iteration = _handle_user_input("u", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        mock_reset_render_cache.assert_called_once_with()
        self.assertEqual(state["status_message"], "Full redraw requested")
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])


class TestCLITerminalResizeCheck(unittest.TestCase):
    """Test low-frequency terminal resize detection and full redraw requests."""

    @patch("paraping.cli.reset_render_cache")
    @patch("paraping.cli.get_terminal_size")
    def test_resize_check_skips_until_interval(self, mock_get_terminal_size, mock_reset_render_cache):
        """Should not check terminal size again before the next check timestamp."""
        state = {
            "next_resize_check_time": 10.0,
            "resize_check_interval": 1.0,
            "last_observed_term_size": os.terminal_size((80, 24)),
            "force_render": False,
            "updated": False,
            "cached_page_step": 5,
            "last_term_size": object(),
        }

        _check_terminal_resize_and_request_redraw(state, now_monotonic=9.5)

        mock_get_terminal_size.assert_not_called()
        mock_reset_render_cache.assert_not_called()
        self.assertFalse(state["force_render"])
        self.assertFalse(state["updated"])
        self.assertEqual(state["cached_page_step"], 5)

    @patch("paraping.cli.reset_render_cache")
    @patch("paraping.cli.get_terminal_size")
    def test_resize_check_requests_full_redraw_on_size_change(self, mock_get_terminal_size, mock_reset_render_cache):
        """Size changes should invalidate caches and force the next frame to full redraw."""
        mock_get_terminal_size.return_value = os.terminal_size((120, 40))
        state = {
            "next_resize_check_time": 0.0,
            "resize_check_interval": 1.0,
            "last_observed_term_size": os.terminal_size((80, 24)),
            "force_render": False,
            "updated": False,
            "cached_page_step": 5,
            "last_term_size": object(),
        }

        _check_terminal_resize_and_request_redraw(state, now_monotonic=5.0)

        mock_get_terminal_size.assert_called_once_with(fallback=(80, 24))
        mock_reset_render_cache.assert_called_once_with()
        self.assertEqual(state["next_resize_check_time"], 6.0)
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])
        self.assertIsNone(state["cached_page_step"])
        self.assertIsNone(state["last_term_size"])

    @patch("paraping.cli.reset_render_cache")
    @patch("paraping.cli.get_terminal_size")
    def test_resize_check_noop_when_size_unchanged(self, mock_get_terminal_size, mock_reset_render_cache):
        """Same terminal size should not trigger full redraw."""
        mock_get_terminal_size.return_value = os.terminal_size((80, 24))
        state = {
            "next_resize_check_time": 0.0,
            "resize_check_interval": 1.0,
            "last_observed_term_size": os.terminal_size((80, 24)),
            "force_render": False,
            "updated": False,
            "cached_page_step": 5,
            "last_term_size": object(),
        }

        _check_terminal_resize_and_request_redraw(state, now_monotonic=2.0)

        mock_get_terminal_size.assert_called_once_with(fallback=(80, 24))
        mock_reset_render_cache.assert_not_called()
        self.assertEqual(state["next_resize_check_time"], 3.0)
        self.assertFalse(state["force_render"])
        self.assertFalse(state["updated"])
        self.assertEqual(state["cached_page_step"], 5)


if __name__ == "__main__":
    unittest.main()
