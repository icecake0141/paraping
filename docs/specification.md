<!--
Copyright 2025 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# ParaPing Specification

## 1. Scope

ParaPing is an interactive terminal ICMP monitor for multi-host operational triage.
It continuously pings multiple hosts in parallel and visualizes network state in real time.

## 2. Core Capabilities

- Concurrent ping for multiple hosts
- Live timeline / sparkline visualization
- Sort and filter by latency/failure conditions
- Pause modes and snapshot export
- Per-host detail inspection (RTT and related stats)

## 3. Runtime Requirements

- Python 3.9+
- Linux: `ping_helper` binary with `cap_net_raw` (recommended)
- macOS/BSD: run with `sudo` when raw ICMP is required
- Optional network access for ASN lookup

## 4. Privileged ICMP Model (Linux)

- Raw socket privilege is isolated to `ping_helper`
- Main Python process runs without elevated privileges
- Do not grant capabilities to generic interpreters (e.g., `/usr/bin/python3`)

See also: [Ping Helper Detail](ping_helper.md)

## 5. Scheduling and Display Behavior

- Time-driven scheduler aligns columns by wall-clock time
- Pending markers can be shown before responses arrive
- Designed to reduce display drift during latency fluctuation

## 6. Safety Controls

- Global rate limit protection
- Per-host outstanding ping window limits

## 7. Platform Notes

- IPv4 is the primary supported path
- Capability setup (`setcap`) is Linux-specific

## 8. Related Documents

- [README](../README.md)
- [Testing Guide](testing.md)
- [Docs Index](index.md)
