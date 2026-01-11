#!/usr/bin/env python3
# Copyright 2025 Multiping contributors
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
Unit tests for multiping functionality
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import argparse
import queue
import sys
import os

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import handle_options, read_input_file, ping_host, main  # noqa: E402


class TestHandleOptions(unittest.TestCase):
    """Test command line option parsing"""

    def test_default_options(self):
        """Test default option values"""
        with patch('sys.argv', ['main.py', 'example.com']):
            args = handle_options()
            self.assertEqual(args.timeout, 1)
            self.assertEqual(args.count, 4)
            self.assertEqual(args.verbose, False)
            self.assertEqual(args.hosts, ['example.com'])

    def test_custom_timeout(self):
        """Test custom timeout option"""
        with patch('sys.argv', ['main.py', '-t', '5', 'example.com']):
            args = handle_options()
            self.assertEqual(args.timeout, 5)

    def test_custom_count(self):
        """Test custom count option"""
        with patch('sys.argv', ['main.py', '-c', '10', 'example.com']):
            args = handle_options()
            self.assertEqual(args.count, 10)

    def test_verbose_flag(self):
        """Test verbose flag"""
        with patch('sys.argv', ['main.py', '-v', 'example.com']):
            args = handle_options()
            self.assertTrue(args.verbose)

    def test_multiple_hosts(self):
        """Test multiple hosts"""
        with patch('sys.argv', ['main.py', 'host1.com', 'host2.com', 'host3.com']):
            args = handle_options()
            self.assertEqual(len(args.hosts), 3)
            self.assertIn('host1.com', args.hosts)


class TestReadInputFile(unittest.TestCase):
    """Test input file reading functionality"""

    def test_read_valid_file(self):
        """Test reading a valid input file"""
        file_content = "host1.com\nhost2.com\nhost3.com\n"
        with patch('builtins.open', mock_open(read_data=file_content)):
            hosts = read_input_file('test.txt')
            self.assertEqual(len(hosts), 3)
            self.assertEqual(hosts, ['host1.com', 'host2.com', 'host3.com'])

    def test_read_file_with_comments(self):
        """Test reading file with comments"""
        file_content = "host1.com\n# This is a comment\nhost2.com\n"
        with patch('builtins.open', mock_open(read_data=file_content)):
            hosts = read_input_file('test.txt')
            self.assertEqual(len(hosts), 2)
            self.assertEqual(hosts, ['host1.com', 'host2.com'])

    def test_read_file_with_empty_lines(self):
        """Test reading file with empty lines"""
        file_content = "host1.com\n\nhost2.com\n\n"
        with patch('builtins.open', mock_open(read_data=file_content)):
            hosts = read_input_file('test.txt')
            self.assertEqual(len(hosts), 2)
            self.assertEqual(hosts, ['host1.com', 'host2.com'])

    def test_file_not_found(self):
        """Test handling of missing file"""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            hosts = read_input_file('nonexistent.txt')
            self.assertEqual(hosts, [])

    def test_permission_denied(self):
        """Test handling of permission error"""
        with patch('builtins.open', side_effect=PermissionError()):
            hosts = read_input_file('restricted.txt')
            self.assertEqual(hosts, [])


class TestPingHost(unittest.TestCase):
    """Test ping host functionality"""

    @patch('main.ICMP')
    @patch('main.IP')
    @patch('main.sr')
    def test_ping_host_success(self, mock_sr, mock_ip, mock_icmp):
        """Test successful ping"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        # Mock successful ping response - ans should be a truthy list
        mock_sent = MagicMock()
        mock_sent.time = 0.0
        mock_received = MagicMock()
        mock_received.time = 0.001
        mock_sr.return_value = ([[mock_sent, mock_received]], [])

        results = list(ping_host('example.com', 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result['host'], 'example.com')
            self.assertIn(result['status'], ['success', 'slow'])

    @patch('main.ICMP')
    @patch('main.IP')
    @patch('main.sr')
    def test_ping_host_failure(self, mock_sr, mock_ip, mock_icmp):
        """Test failed ping"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        # Mock failed ping response (no answers)
        mock_sr.return_value = ([], [MagicMock()])

        results = list(ping_host('example.com', 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result['host'], 'example.com')
            self.assertEqual(result['status'], 'fail')

    @patch('main.ICMP')
    @patch('main.IP')
    @patch('main.sr')
    def test_ping_host_partial_success(self, mock_sr, mock_ip, mock_icmp):
        """Test partial ping success"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        # Mock alternating success/failure
        mock_sent = MagicMock()
        mock_sent.time = 0.0
        mock_received = MagicMock()
        mock_received.time = 0.001
        mock_sr.side_effect = [
            ([[mock_sent, mock_received]], []),
            ([], [MagicMock()]),
            ([[mock_sent, mock_received]], []),
            ([], [MagicMock()])
        ]

        results = list(ping_host('example.com', 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        success_count = sum(1 for r in results if r['status'] in ['success', 'slow'])
        fail_count = sum(1 for r in results if r['status'] == 'fail')
        self.assertEqual(success_count, 2)
        self.assertEqual(fail_count, 2)

    @patch('main.ICMP')
    @patch('main.IP')
    @patch('main.sr')
    def test_ping_host_with_network_error(self, mock_sr, mock_ip, mock_icmp):
        """Test ping with network error"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        mock_sr.side_effect = OSError("Network unreachable")

        results = list(ping_host('example.com', 1, 2, 0.5, False))

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result['host'], 'example.com')
            self.assertEqual(result['status'], 'fail')


class TestMain(unittest.TestCase):
    """Test main function"""

    @patch('main.threading.Thread')
    @patch('main.queue.Queue')
    @patch('main.sys.stdin')
    @patch('main.shutil.get_terminal_size')
    @patch('main.ThreadPoolExecutor')
    def test_main_with_hosts(self, mock_executor, mock_term_size, mock_stdin, mock_queue, mock_thread):
        """Test main function with hosts"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = False
        mock_term_size.return_value = MagicMock(columns=80, lines=24)

        # Mock queues to simulate completion
        result_queue = MagicMock()
        result_items = [
            {"host_id": 0, "status": "done"},
            {"host_id": 1, "status": "done"},
        ]

        def result_get_nowait():
            if result_items:
                return result_items.pop(0)
            raise queue.Empty()

        result_queue.get_nowait.side_effect = result_get_nowait
        rdns_request_queue = MagicMock()
        rdns_result_queue = MagicMock()
        rdns_result_queue.get_nowait.side_effect = queue.Empty()
        asn_request_queue = MagicMock()
        asn_result_queue = MagicMock()
        asn_result_queue.get_nowait.side_effect = queue.Empty()
        mock_queue.side_effect = [
            result_queue,
            rdns_request_queue,
            rdns_result_queue,
            asn_request_queue,
            asn_result_queue,
        ]
        mock_thread.return_value = MagicMock()

        args = argparse.Namespace(
            timeout=1,
            count=4,
            slow_threshold=0.5,
            verbose=False,
            hosts=['host1.com', 'host2.com'],
            input=None,
            panel_position='right',
            timezone=None,
            snapshot_timezone='utc',
            pause_mode='display',
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False

        # Mock futures
        mock_future = MagicMock()
        mock_future.done.return_value = True
        mock_future.result.return_value = None
        mock_executor_instance.submit.return_value = mock_future

        # Should not raise exception
        main(args)

    @patch('builtins.print')
    def test_main_with_invalid_count(self, mock_print):
        """Test main function with invalid count"""
        args = argparse.Namespace(
            timeout=1,
            count=0,
            verbose=False,
            hosts=['host1.com'],
            input=None
        )

        main(args)
        mock_print.assert_called()

    @patch('builtins.print')
    def test_main_with_no_hosts(self, mock_print):
        """Test main function with no hosts"""
        args = argparse.Namespace(
            timeout=1,
            count=4,
            verbose=False,
            hosts=[],
            input=None
        )

        main(args)
        mock_print.assert_called()

    @patch('main.threading.Thread')
    @patch('main.queue.Queue')
    @patch('main.sys.stdin')
    @patch('main.shutil.get_terminal_size')
    @patch('main.read_input_file')
    @patch('main.ThreadPoolExecutor')
    def test_main_with_input_file(
        self,
        mock_executor,
        mock_read_file,
        mock_term_size,
        mock_stdin,
        mock_queue,
        mock_thread,
    ):
        """Test main function with input file"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = False
        mock_term_size.return_value = MagicMock(columns=80, lines=24)

        mock_read_file.return_value = ['host1.com', 'host2.com']

        # Mock queues to simulate completion
        result_queue = MagicMock()
        result_items = [
            {"host_id": 0, "status": "done"},
            {"host_id": 1, "status": "done"},
        ]

        def result_get_nowait():
            if result_items:
                return result_items.pop(0)
            raise queue.Empty()

        result_queue.get_nowait.side_effect = result_get_nowait
        rdns_request_queue = MagicMock()
        rdns_result_queue = MagicMock()
        rdns_result_queue.get_nowait.side_effect = queue.Empty()
        asn_request_queue = MagicMock()
        asn_result_queue = MagicMock()
        asn_result_queue.get_nowait.side_effect = queue.Empty()
        mock_queue.side_effect = [
            result_queue,
            rdns_request_queue,
            rdns_result_queue,
            asn_request_queue,
            asn_result_queue,
        ]
        mock_thread.return_value = MagicMock()

        args = argparse.Namespace(
            timeout=1,
            count=4,
            slow_threshold=0.5,
            verbose=False,
            hosts=[],
            input='hosts.txt',
            panel_position='right',
            timezone=None,
            snapshot_timezone='utc',
            pause_mode='display',
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False

        # Mock futures
        mock_future = MagicMock()
        mock_future.done.return_value = True
        mock_future.result.return_value = None
        mock_executor_instance.submit.return_value = mock_future

        # Should not raise exception
        main(args)

        mock_read_file.assert_called_once_with('hosts.txt')


if __name__ == '__main__':
    unittest.main()
