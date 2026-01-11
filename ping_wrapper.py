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
"""

import os
import subprocess
import sys
import json


def ping_with_helper(host, timeout_ms=1000, helper_path="./ping_helper"):
    """
    Ping a host using the ping_helper binary.

    Args:
        host: The hostname or IP address to ping
        timeout_ms: Timeout in milliseconds (default: 1000)
        helper_path: Path to the ping_helper binary (default: ./ping_helper)

    Returns:
        float: RTT in milliseconds on success
        None: On timeout or error

    Raises:
        FileNotFoundError: If the ping_helper binary is not found
    """
    if not os.path.exists(helper_path):
        raise FileNotFoundError(
            f"ping_helper binary not found at {helper_path}. "
            f"Please run 'make build' to compile it."
        )

    try:
        # Run the helper binary
        result = subprocess.run(
            [helper_path, host, str(timeout_ms)],
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000.0) + 1.0,  # Add 1 second buffer
        )

        # Success case
        if result.returncode == 0:
            # Parse the output: rtt_ms=<value>
            for line in result.stdout.splitlines():
                if line.startswith("rtt_ms="):
                    try:
                        rtt_str = line.split("=", 1)[1]
                        return float(rtt_str)
                    except (ValueError, IndexError):
                        return None
            return None

        # Timeout case (exit code 7)
        if result.returncode == 7:
            return None

        # Other errors - return None
        return None

    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def main():
    """
    Command-line interface for the ping wrapper.

    Usage:
        python3 ping_wrapper.py <host> [timeout_ms]

    Outputs JSON with the result:
        {"host": "example.com", "rtt_ms": 12.345, "success": true}
        {"host": "example.com", "rtt_ms": null, "success": false}
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

    try:
        rtt_ms = ping_with_helper(host, timeout_ms)
        result = {
            "host": host,
            "rtt_ms": rtt_ms,
            "success": rtt_ms is not None
        }
        print(json.dumps(result))
        sys.exit(0 if rtt_ms is not None else 1)
    except FileNotFoundError as e:
        print(json.dumps({
            "host": host,
            "rtt_ms": None,
            "success": False,
            "error": str(e)
        }))
        sys.exit(2)
    except Exception as e:
        print(json.dumps({
            "host": host,
            "rtt_ms": None,
            "success": False,
            "error": str(e)
        }))
        sys.exit(3)


if __name__ == "__main__":
    main()
