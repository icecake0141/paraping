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
Unit tests for paraping.core module.

This module tests pure domain logic functions without performing actual network calls.
"""

import logging
import os
import socket
import sys
import unittest
from unittest.mock import mock_open, patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.core import (
    HISTORY_DURATION_MINUTES,
    MAX_HOST_THREADS,
    SNAPSHOT_INTERVAL_SECONDS,
    build_host_infos,
    parse_host_file_line,
    read_input_file,
)


class TestParseHostFileLine(unittest.TestCase):
    """Test cases for parse_host_file_line function"""

    def test_parse_valid_ipv4_entry(self):
        """Test parsing a valid IPv4 entry"""
        result = parse_host_file_line("192.0.2.1,webserver", 1, "hosts.txt")
        self.assertIsNotNone(result)
        self.assertEqual(result["host"], "192.0.2.1")
        self.assertEqual(result["alias"], "webserver")
        self.assertEqual(result["ip"], "192.0.2.1")

    def test_parse_valid_entry_with_spaces(self):
        """Test parsing with extra whitespace"""
        result = parse_host_file_line("  192.0.2.2  ,  database  ", 2, "hosts.txt")
        self.assertIsNotNone(result)
        self.assertEqual(result["host"], "192.0.2.2")
        self.assertEqual(result["alias"], "database")
        self.assertEqual(result["ip"], "192.0.2.2")

    def test_parse_valid_extended_entry_with_site_and_tags(self):
        """Test parsing extended entry with site and tags."""
        result = parse_host_file_line("192.0.2.10,app01,Tokyo,core;prod", 3, "hosts.txt")
        self.assertIsNotNone(result)
        self.assertEqual(result["host"], "192.0.2.10")
        self.assertEqual(result["alias"], "app01")
        self.assertEqual(result["site"], "Tokyo")
        self.assertEqual(result["tags"], ["core", "prod"])

    def test_parse_empty_line(self):
        """Test parsing empty line returns None"""
        result = parse_host_file_line("", 1, "hosts.txt")
        self.assertIsNone(result)

    def test_parse_whitespace_only_line(self):
        """Test parsing whitespace-only line returns None"""
        result = parse_host_file_line("   \t  \n", 1, "hosts.txt")
        self.assertIsNone(result)

    def test_parse_comment_line(self):
        """Test parsing comment line returns None"""
        result = parse_host_file_line("# This is a comment", 1, "hosts.txt")
        self.assertIsNone(result)

    def test_parse_invalid_format_missing_comma(self):
        """Test parsing line without comma returns None"""
        with logging.captured_logs("paraping.core") as records:
            result = parse_host_file_line("192.0.2.1 webserver", 1, "hosts.txt")
        self.assertIsNone(result)
        self.assertTrue(records)

    def test_parse_invalid_format_too_many_parts(self):
        """Test parsing line with too many parts returns None"""
        with logging.captured_logs("paraping.core") as records:
            result = parse_host_file_line("192.0.2.1,alias,extra", 1, "hosts.txt")
        self.assertIsNone(result)
        self.assertTrue(records)

    def test_parse_invalid_ip_address(self):
        """Test parsing invalid IP address returns None"""
        with logging.captured_logs("paraping.core") as records:
            result = parse_host_file_line("999.999.999.999,invalid", 1, "hosts.txt")
        self.assertIsNone(result)
        self.assertTrue(records)

    def test_parse_ipv6_address_with_warning(self):
        """Test that IPv6 addresses are accepted but generate a warning"""
        with logging.captured_logs("paraping.core") as records:
            result = parse_host_file_line("::1,localhost", 1, "hosts.txt")
        self.assertIsNotNone(result)
        self.assertEqual(result["host"], "::1")
        self.assertEqual(result["alias"], "localhost")
        self.assertEqual(result["ip"], "::1")
        self.assertTrue(records)

    def test_parse_empty_ip(self):
        """Test parsing empty IP field returns None"""
        with logging.captured_logs("paraping.core") as records:
            result = parse_host_file_line(",alias", 1, "hosts.txt")
        self.assertIsNone(result)
        self.assertTrue(records)

    def test_parse_empty_alias(self):
        """Test parsing empty alias field returns None"""
        with logging.captured_logs("paraping.core") as records:
            result = parse_host_file_line("192.0.2.1,", 1, "hosts.txt")
        self.assertIsNone(result)
        self.assertTrue(records)


class TestReadInputFile(unittest.TestCase):
    """Test cases for read_input_file function"""

    def test_read_valid_file(self):
        """Test reading a valid input file"""
        file_content = "192.0.2.1,server1\n192.0.2.2,server2\n# comment\n192.0.2.3,server3"
        with patch("builtins.open", mock_open(read_data=file_content)):
            result = read_input_file("hosts.txt")

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["alias"], "server1")
        self.assertEqual(result[1]["alias"], "server2")
        self.assertEqual(result[2]["alias"], "server3")

    def test_read_file_with_empty_lines(self):
        """Test reading file with empty lines"""
        file_content = "192.0.2.1,server1\n\n192.0.2.2,server2\n   \n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            result = read_input_file("hosts.txt")

        self.assertEqual(len(result), 2)

    def test_read_file_with_comments_only(self):
        """Test reading file with only comments"""
        file_content = "# comment 1\n# comment 2\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            result = read_input_file("hosts.txt")

        self.assertEqual(len(result), 0)

    def test_read_nonexistent_file(self):
        """Test reading non-existent file returns empty list"""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with logging.captured_logs("paraping.core") as records:
                result = read_input_file("nonexistent.txt")

        self.assertEqual(result, [])
        self.assertTrue(records)

    def test_read_file_permission_error(self):
        """Test handling permission error"""
        with patch("builtins.open", side_effect=PermissionError()):
            with logging.captured_logs("paraping.core") as records:
                result = read_input_file("noperm.txt")

        self.assertEqual(result, [])
        self.assertTrue(records)

    def test_read_file_generic_exception(self):
        """Test handling generic OS/IO exception"""
        with patch("builtins.open", side_effect=OSError("Generic error")):
            with logging.captured_logs("paraping.core") as records:
                result = read_input_file("error.txt")

        self.assertEqual(result, [])
        self.assertTrue(records)


class TestBuildHostInfos(unittest.TestCase):
    """Test cases for build_host_infos function"""

    @patch("socket.getaddrinfo")
    def test_build_from_string_hosts(self, mock_getaddrinfo):
        """Test building host infos from list of strings"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("192.0.2.1", 0))]

        hosts = ["example.com", "test.com"]
        host_infos, host_map = build_host_infos(hosts)

        self.assertEqual(len(host_infos), 2)
        self.assertEqual(host_infos[0]["host"], "example.com")
        self.assertEqual(host_infos[0]["alias"], "example.com")
        self.assertEqual(host_infos[0]["id"], 0)
        self.assertEqual(host_infos[1]["id"], 1)

    @patch("socket.getaddrinfo")
    def test_build_from_dict_hosts(self, mock_getaddrinfo):
        """Test building host infos from list of dicts"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("192.0.2.1", 0))]

        hosts = [
            {"host": "192.0.2.1", "alias": "server1", "ip": "192.0.2.1"},
            {"host": "192.0.2.2", "alias": "server2", "ip": "192.0.2.2"},
        ]
        host_infos, host_map = build_host_infos(hosts)

        self.assertEqual(len(host_infos), 2)
        self.assertEqual(host_infos[0]["alias"], "server1")
        self.assertEqual(host_infos[0]["ip"], "192.0.2.1")
        self.assertEqual(host_infos[1]["alias"], "server2")

    @patch("socket.getaddrinfo")
    def test_build_initializes_pending_flags(self, mock_getaddrinfo):
        """Test that rdns_pending and asn_pending are initialized"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("192.0.2.1", 0))]

        hosts = ["example.com"]
        host_infos, _ = build_host_infos(hosts)

        self.assertFalse(host_infos[0]["rdns_pending"])
        self.assertFalse(host_infos[0]["asn_pending"])
        self.assertIsNone(host_infos[0]["rdns"])
        self.assertIsNone(host_infos[0]["asn"])

    @patch("socket.getaddrinfo")
    def test_build_handles_dns_failure(self, mock_getaddrinfo):
        """Test handling DNS resolution failure"""
        mock_getaddrinfo.side_effect = socket.gaierror("DNS error")

        hosts = ["invalid.example"]
        host_infos, _ = build_host_infos(hosts)

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["ip"], "invalid.example")

    @patch("socket.getaddrinfo")
    def test_build_creates_host_map(self, mock_getaddrinfo):
        """Test that host_map is created correctly"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("192.0.2.1", 0))]

        hosts = ["example.com", "example.com"]  # Duplicate host
        host_infos, host_map = build_host_infos(hosts)

        self.assertIn("example.com", host_map)
        self.assertEqual(len(host_map["example.com"]), 2)

    @patch("socket.getaddrinfo")
    def test_build_prefers_ipv4_over_ipv6(self, mock_getaddrinfo):
        """Test that IPv4 is preferred when both IPv4 and IPv6 are available"""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET6, socket.SOCK_RAW, 0, "", ("2001:db8::1", 0)),
            (socket.AF_INET, socket.SOCK_RAW, 0, "", ("192.0.2.1", 0)),
        ]

        hosts = ["dual-stack.example.com"]
        host_infos, _ = build_host_infos(hosts)

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["ip"], "192.0.2.1")

    @patch("socket.getaddrinfo")
    def test_build_uses_ipv6_when_only_ipv6_available(self, mock_getaddrinfo):
        """Test that IPv6 is used when only IPv6 addresses are available"""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET6, socket.SOCK_RAW, 0, "", ("2001:db8::1", 0)),
        ]

        with logging.captured_logs("paraping.core") as records:
            hosts = ["ipv6-only.example.com"]
            host_infos, _ = build_host_infos(hosts)

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["ip"], "2001:db8::1")
        self.assertTrue(records)


class TestConstants(unittest.TestCase):
    """Test that constants are defined correctly"""

    def test_max_host_threads_defined(self):
        """Test MAX_HOST_THREADS is defined"""
        self.assertIsInstance(MAX_HOST_THREADS, int)
        self.assertGreater(MAX_HOST_THREADS, 0)

    def test_history_duration_defined(self):
        """Test HISTORY_DURATION_MINUTES is defined"""
        self.assertIsInstance(HISTORY_DURATION_MINUTES, int)
        self.assertGreater(HISTORY_DURATION_MINUTES, 0)

    def test_snapshot_interval_defined(self):
        """Test SNAPSHOT_INTERVAL_SECONDS is defined"""
        self.assertIsInstance(SNAPSHOT_INTERVAL_SECONDS, (int, float))
        self.assertGreater(SNAPSHOT_INTERVAL_SECONDS, 0)


if __name__ == "__main__":
    unittest.main()
