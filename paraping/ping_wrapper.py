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
Python wrapper for the privileged ICMP ping_helper.

This module provides a function to ping a host using the compiled ping_helper
binary, which has the cap_net_raw capability set. This allows non-root users
to send ICMP echo requests without granting privileges to the Python interpreter.

The ping_helper binary follows a strict CLI contract:
  - Usage: ping_helper <host> <timeout_ms> [icmp_seq]
  - Success (exit 0): Outputs "rtt_ms=<value> ttl=<value>"
  - Timeout (exit 7): No output, normal timeout behavior (not an error)
  - Errors (exit 1-6, 8): Error message to stderr with specific exit codes

For detailed information about the helper contract, see docs/ping_helper.md.
"""

import json
import os
import subprocess
import sys


class PingHelperError(RuntimeError):
    """Raised when ping_helper returns an error."""

    def __init__(self, message, returncode=None, stderr=None):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def ping_with_helper(host, timeout_ms=1000, helper_path="./ping_helper", icmp_seq=None):
    """
    Ping a host using the ping_helper binary.

    This function wraps the ping_helper C binary and handles its exit codes
    according to the documented CLI contract. It distinguishes between normal
    timeouts (exit 7) and actual errors (other non-zero exit codes).

    Args:
        host: The hostname or IP address to ping
        timeout_ms: Timeout in milliseconds (default: 1000)
        helper_path: Path to the ping_helper binary (default: ./ping_helper)
        icmp_seq: Optional ICMP sequence number (0-65535). If None, uses default (1)

    Returns:
        tuple[float | None, int | None]: (RTT in milliseconds, TTL) on success;
        (None, None) on timeout (normal behavior, not an error)

    Raises:
        FileNotFoundError: If the ping_helper binary is not found
        PingHelperError: If the helper exits with an error code (1-6, 8)
            - Exit 1: Invalid arguments
            - Exit 2: Argument validation error
            - Exit 3: Host resolution failed
            - Exit 4: Socket error or insufficient privileges
            - Exit 5: Send error
            - Exit 6: Select error
            - Exit 8: Receive error
        ValueError: If timeout_ms is not positive or icmp_seq is out of range

    Examples:
        Successful ping:
        >>> rtt_ms, ttl = ping_with_helper("8.8.8.8", 1000)
        >>> assert rtt_ms is not None and ttl is not None
        >>> assert rtt_ms > 0 and ttl > 0

        Timeout (normal, returns None):
        >>> rtt_ms, ttl = ping_with_helper("192.0.2.1", 100)  # Non-routable IP
        >>> assert rtt_ms is None and ttl is None

        Error handling:
        >>> try:
        ...     rtt_ms, ttl = ping_with_helper("invalid.example", 1000)
        ... except PingHelperError as e:
        ...     assert e.returncode in (2, 3, 4, 5, 6, 8)
        ...     assert e.stderr is not None
    """
    if timeout_ms <= 0:
        raise ValueError("timeout_ms must be a positive integer in milliseconds.")

    if icmp_seq is not None and (icmp_seq < 0 or icmp_seq > 65535):
        raise ValueError("icmp_seq must be between 0 and 65535.")

    if not os.path.exists(helper_path):
        raise FileNotFoundError(f"ping_helper binary not found at {helper_path}. " f"Please run 'make build' to compile it.")

    try:
        # Build command arguments
        cmd_args = [helper_path, host, str(timeout_ms)]
        if icmp_seq is not None:
            cmd_args.append(str(icmp_seq))

        # Run the helper binary
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000.0) + 1.0,  # Add 1 second buffer
            check=False,  # We handle non-zero exit codes ourselves
        )

        # Success case
        if result.returncode == 0:
            # Parse the output: rtt_ms=<value>
            for line in result.stdout.splitlines():
                if line.startswith("rtt_ms="):
                    rtt_ms = None
                    ttl = None
                    for token in line.split():
                        if token.startswith("rtt_ms="):
                            rtt_str = token.split("=", 1)[1]
                            try:
                                rtt_ms = float(rtt_str)
                            except ValueError:
                                rtt_ms = None
                        elif token.startswith("ttl="):
                            ttl_str = token.split("=", 1)[1]
                            try:
                                ttl = int(ttl_str)
                            except ValueError:
                                ttl = None
                    return (rtt_ms, ttl)
            return (None, None)

        # Timeout case (exit code 7)
        if result.returncode == 7:
            return (None, None)

        # Other errors - include stderr in exception
        stderr = result.stderr.strip() if result.stderr else ""
        details = f"ping_helper failed with return code {result.returncode}"
        if stderr:
            details = f"{details}: {stderr}"
        raise PingHelperError(details, returncode=result.returncode, stderr=stderr)

    except subprocess.TimeoutExpired:
        return (None, None)


def main():
    """
    Command-line interface for the ping wrapper.

    Usage:
        python3 ping_wrapper.py <host> [timeout_ms]

    Outputs JSON with the result:
        {"host": "example.com", "rtt_ms": 12.345, "ttl": 64, "success": true}
        {"host": "example.com", "rtt_ms": null, "ttl": null, "success": false}
    """
    if len(sys.argv) < 2:
        print("Usage: python3 ping_wrapper.py <host> [timeout_ms]", file=sys.stderr)
        sys.exit(1)

    host = sys.argv[1]
    timeout_ms = 1000
    if len(sys.argv) >= 3:
        try:
            timeout_ms = int(sys.argv[2])
        except ValueError:
            print("Error: timeout_ms must be an integer", file=sys.stderr)
            sys.exit(1)
        if timeout_ms <= 0:
            print("Error: timeout_ms must be a positive integer", file=sys.stderr)
            sys.exit(1)

    try:
        rtt_ms, ttl = ping_with_helper(host, timeout_ms)
        result = {
            "host": host,
            "rtt_ms": rtt_ms,
            "ttl": ttl,
            "success": rtt_ms is not None,
        }
        print(json.dumps(result))
        sys.exit(0 if rtt_ms is not None else 1)
    except FileNotFoundError as e:
        print(
            json.dumps(
                {
                    "host": host,
                    "rtt_ms": None,
                    "ttl": None,
                    "success": False,
                    "error": str(e),
                }
            )
        )
        sys.exit(2)
    except PingHelperError as e:
        error_message = str(e)
        if e.stderr and e.stderr not in error_message:
            error_message = f"{error_message} (stderr: {e.stderr})"
        print(
            json.dumps(
                {
                    "host": host,
                    "rtt_ms": None,
                    "ttl": None,
                    "success": False,
                    "error": error_message,
                }
            )
        )
        sys.exit(3)
    except Exception as e:
        print(
            json.dumps(
                {
                    "host": host,
                    "rtt_ms": None,
                    "ttl": None,
                    "success": False,
                    "error": str(e),
                }
            )
        )
        sys.exit(3)


if __name__ == "__main__":
    main()
