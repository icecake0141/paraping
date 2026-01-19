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
Unit tests for network_asn module.

Tests ASN parsing, network fetch, caching, and retry logic without requiring
actual network connectivity.
"""

import os
import queue
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import network_asn
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.network_asn import asn_worker, fetch_asn_via_whois, parse_asn_response, resolve_asn, should_retry_asn


class TestParseASNResponse(unittest.TestCase):
    """Test pure ASN parsing function (no network I/O)."""

    def test_parse_valid_response(self):
        """Test parsing a valid Team Cymru whois response."""
        response = """AS      | IP               | BGP Prefix          | CC | Registry | Allocated  | AS Name
15133   | 8.8.8.8          | 8.8.8.0/24          | US | arin     | 1992-12-01 | EDGECAST, US"""
        result = parse_asn_response(response)
        self.assertEqual(result, "AS15133")

    def test_parse_response_with_as_prefix(self):
        """Test parsing when ASN already has AS prefix."""
        response = """AS      | IP               | BGP Prefix
AS15133 | 8.8.8.8          | 8.8.8.0/24"""
        result = parse_asn_response(response)
        self.assertEqual(result, "AS15133")

    def test_parse_response_na_value(self):
        """Test parsing when ASN is NA (not available)."""
        response = """AS      | IP               | BGP Prefix
NA      | 127.0.0.1        | NA"""
        result = parse_asn_response(response)
        self.assertIsNone(result)

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        result = parse_asn_response("")
        self.assertIsNone(result)

    def test_parse_single_line_response(self):
        """Test parsing response with only header line."""
        response = "AS      | IP               | BGP Prefix"
        result = parse_asn_response(response)
        self.assertIsNone(result)

    def test_parse_response_with_whitespace(self):
        """Test parsing response with extra whitespace."""
        response = """AS      | IP               | BGP Prefix
  12345 | 1.2.3.4          | 1.2.3.0/24  """
        result = parse_asn_response(response)
        self.assertEqual(result, "AS12345")

    def test_parse_response_with_blank_lines(self):
        """Test parsing response with blank lines."""
        response = """AS      | IP               | BGP Prefix

12345   | 1.2.3.4          | 1.2.3.0/24

"""
        result = parse_asn_response(response)
        self.assertEqual(result, "AS12345")

    def test_parse_response_with_empty_asn(self):
        """Test parsing when ASN field is empty."""
        response = """AS      | IP               | BGP Prefix
        | 1.2.3.4          | 1.2.3.0/24"""
        result = parse_asn_response(response)
        self.assertIsNone(result)

    def test_parse_response_without_pipes(self):
        """Test parsing response without pipe delimiters.

        Note: The function splits by pipe, so without pipes,
        the entire line becomes a single field. This behavior
        is acceptable as malformed data from Team Cymru is unlikely.
        """
        response = """AS IP BGP
12345 1.2.3.4 1.2.3.0/24"""
        # Without pipes, entire line becomes first field after split
        # This extracts "12345" from the beginning
        result = parse_asn_response(response)
        # Function is lenient and will extract ASN even without proper format
        self.assertIsNotNone(result)


class TestFetchASNViaWhois(unittest.TestCase):
    """Test network fetch function with mocked socket."""

    @patch("paraping.network_asn.socket.create_connection")
    def test_fetch_successful(self, mock_create_connection):
        """Test successful ASN fetch via socket."""
        # Mock socket that returns valid response
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [
            b"AS      | IP\n",
            b"15133   | 8.8.8.8\n",
            b"",  # EOF
        ]
        mock_create_connection.return_value.__enter__.return_value = mock_sock

        result = fetch_asn_via_whois("8.8.8.8", timeout=3.0)

        self.assertIsNotNone(result)
        self.assertIn("15133", result)
        mock_sock.settimeout.assert_called_once_with(3.0)
        mock_sock.sendall.assert_called_once()

    @patch("paraping.network_asn.socket.create_connection")
    def test_fetch_timeout(self, mock_create_connection):
        """Test handling of socket timeout."""
        mock_create_connection.side_effect = TimeoutError("Connection timeout")

        result = fetch_asn_via_whois("8.8.8.8", timeout=1.0)

        self.assertIsNone(result)

    @patch("paraping.network_asn.socket.create_connection")
    def test_fetch_connection_error(self, mock_create_connection):
        """Test handling of connection error."""
        mock_create_connection.side_effect = OSError("Connection refused")

        result = fetch_asn_via_whois("8.8.8.8", timeout=3.0)

        self.assertIsNone(result)

    @patch("paraping.network_asn.socket.create_connection")
    def test_fetch_respects_max_bytes(self, mock_create_connection):
        """Test that fetch respects max_bytes limit."""
        # Mock socket that returns more data than max_bytes
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"A" * 4096
        mock_create_connection.return_value.__enter__.return_value = mock_sock

        result = fetch_asn_via_whois("8.8.8.8", max_bytes=8192)

        # Should stop reading after reaching max_bytes
        # With 4096 byte chunks, should read twice (8192 bytes total)
        self.assertEqual(mock_sock.recv.call_count, 2)

    @patch("paraping.network_asn.socket.create_connection")
    def test_fetch_custom_host_port(self, mock_create_connection):
        """Test fetch with custom whois server host and port."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b""
        mock_create_connection.return_value.__enter__.return_value = mock_sock

        fetch_asn_via_whois("8.8.8.8", host="custom.whois.server", port=4343)

        mock_create_connection.assert_called_once_with(("custom.whois.server", 4343), timeout=3.0)

    @patch("paraping.network_asn.socket.create_connection")
    def test_fetch_handles_non_utf8(self, mock_create_connection):
        """Test that fetch handles non-UTF-8 bytes gracefully."""
        mock_sock = MagicMock()
        # Include some non-UTF-8 bytes
        mock_sock.recv.side_effect = [
            b"AS | IP\n",
            b"15133 \xff\xfe | 8.8.8.8\n",  # Invalid UTF-8
            b"",
        ]
        mock_create_connection.return_value.__enter__.return_value = mock_sock

        result = fetch_asn_via_whois("8.8.8.8")

        # Should not raise exception, returns decoded string with errors ignored
        self.assertIsNotNone(result)
        self.assertIn("15133", result)


class TestResolveASN(unittest.TestCase):
    """Test high-level ASN resolution combining fetch and parse."""

    @patch("paraping.network_asn.fetch_asn_via_whois")
    def test_resolve_successful(self, mock_fetch):
        """Test successful ASN resolution."""
        mock_fetch.return_value = """AS      | IP               | BGP Prefix
15133   | 8.8.8.8          | 8.8.8.0/24"""

        result = resolve_asn("8.8.8.8")

        self.assertEqual(result, "AS15133")
        mock_fetch.assert_called_once_with("8.8.8.8", 3.0, 65536)

    @patch("paraping.network_asn.fetch_asn_via_whois")
    def test_resolve_fetch_failure(self, mock_fetch):
        """Test ASN resolution when network fetch fails."""
        mock_fetch.return_value = None

        result = resolve_asn("8.8.8.8")

        self.assertIsNone(result)

    @patch("paraping.network_asn.fetch_asn_via_whois")
    def test_resolve_parse_failure(self, mock_fetch):
        """Test ASN resolution when parsing fails."""
        mock_fetch.return_value = "Invalid response"

        result = resolve_asn("8.8.8.8")

        self.assertIsNone(result)

    @patch("paraping.network_asn.fetch_asn_via_whois")
    def test_resolve_with_custom_timeout(self, mock_fetch):
        """Test ASN resolution with custom timeout."""
        mock_fetch.return_value = """AS      | IP
12345   | 1.2.3.4"""

        resolve_asn("1.2.3.4", timeout=5.0, max_bytes=32768)

        mock_fetch.assert_called_once_with("1.2.3.4", 5.0, 32768)


class TestShouldRetryASN(unittest.TestCase):
    """Test ASN retry logic (pure logic, no time dependency in tests)."""

    def test_should_retry_not_in_cache(self):
        """Test retry when IP is not in cache."""
        asn_cache = {}
        result = should_retry_asn("1.2.3.4", asn_cache, now=100.0, failure_ttl=300.0)
        self.assertTrue(result)

    def test_should_not_retry_successful_cache(self):
        """Test no retry when successful result is cached."""
        asn_cache = {
            "1.2.3.4": {
                "value": "AS12345",
                "fetched_at": 100.0,
            }
        }
        result = should_retry_asn("1.2.3.4", asn_cache, now=150.0, failure_ttl=300.0)
        self.assertFalse(result)

    def test_should_not_retry_failed_within_ttl(self):
        """Test no retry when failed result is cached within TTL."""
        asn_cache = {
            "1.2.3.4": {
                "value": None,
                "fetched_at": 100.0,
            }
        }
        # Now is 250, fetched at 100, TTL is 300, so (250 - 100) < 300
        result = should_retry_asn("1.2.3.4", asn_cache, now=250.0, failure_ttl=300.0)
        self.assertFalse(result)

    def test_should_retry_failed_after_ttl(self):
        """Test retry when failed result is cached beyond TTL."""
        asn_cache = {
            "1.2.3.4": {
                "value": None,
                "fetched_at": 100.0,
            }
        }
        # Now is 500, fetched at 100, TTL is 300, so (500 - 100) >= 300
        result = should_retry_asn("1.2.3.4", asn_cache, now=500.0, failure_ttl=300.0)
        self.assertTrue(result)

    def test_should_retry_failed_exactly_at_ttl(self):
        """Test retry when failed result is exactly at TTL boundary."""
        asn_cache = {
            "1.2.3.4": {
                "value": None,
                "fetched_at": 100.0,
            }
        }
        # Now is 400, fetched at 100, TTL is 300, so (400 - 100) >= 300
        result = should_retry_asn("1.2.3.4", asn_cache, now=400.0, failure_ttl=300.0)
        self.assertTrue(result)


class TestASNWorker(unittest.TestCase):
    """Test ASN worker thread function."""

    @patch("paraping.network_asn.resolve_asn")
    def test_asn_worker_processes_requests(self, mock_resolve):
        """Test ASN worker processes requests from queue."""
        mock_resolve.side_effect = ["AS12345", "AS67890", None]

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Add test requests
        request_queue.put(("host1.com", "1.2.3.4"))
        request_queue.put(("host2.com", "5.6.7.8"))
        request_queue.put(("host3.com", "9.10.11.12"))
        request_queue.put(None)  # Sentinel to stop worker

        # Run worker
        asn_worker(request_queue, result_queue, stop_event, timeout=3.0)

        # Check results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get_nowait())

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], ("host1.com", "AS12345"))
        self.assertEqual(results[1], ("host2.com", "AS67890"))
        self.assertEqual(results[2], ("host3.com", None))

    @patch("paraping.network_asn.resolve_asn")
    def test_asn_worker_stops_on_event(self, mock_resolve):
        """Test ASN worker stops when stop_event is set."""
        mock_resolve.return_value = "AS12345"

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Start worker in thread
        worker_thread = threading.Thread(
            target=asn_worker,
            args=(request_queue, result_queue, stop_event, 3.0),
        )
        worker_thread.start()

        # Give worker a moment to start
        time.sleep(0.1)

        # Set stop event
        stop_event.set()

        # Wait for worker to exit
        worker_thread.join(timeout=1.0)

        # Worker should have exited
        self.assertFalse(worker_thread.is_alive())

    @patch("paraping.network_asn.resolve_asn")
    def test_asn_worker_handles_empty_queue(self, mock_resolve):
        """Test ASN worker handles empty queue gracefully."""
        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Start worker in thread
        worker_thread = threading.Thread(
            target=asn_worker,
            args=(request_queue, result_queue, stop_event, 3.0),
        )
        worker_thread.start()

        # Give worker a moment to process empty queue
        time.sleep(0.2)

        # Set stop event and wait for exit
        stop_event.set()
        worker_thread.join(timeout=1.0)

        # Worker should exit cleanly without errors
        self.assertFalse(worker_thread.is_alive())
        self.assertTrue(result_queue.empty())

    @patch("paraping.network_asn.resolve_asn")
    def test_asn_worker_passes_timeout(self, mock_resolve):
        """Test ASN worker passes timeout parameter to resolve_asn."""
        mock_resolve.return_value = "AS12345"

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        request_queue.put(("host1.com", "1.2.3.4"))
        request_queue.put(None)

        asn_worker(request_queue, result_queue, stop_event, timeout=5.0)

        # Check that resolve_asn was called with correct timeout
        mock_resolve.assert_called_once_with("1.2.3.4", timeout=5.0)


if __name__ == "__main__":
    unittest.main()
