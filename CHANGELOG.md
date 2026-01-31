<!--
Copyright 2026 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# Changelog

All notable changes to ParaPing will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Time-Driven Scheduler
- **Real-time ping scheduler** (`paraping/scheduler.py`): Eliminates timeline drift by scheduling pings at precise intervals based on wall-clock time rather than sleep-based delays
  - Configurable ping interval (default: 1.0s, range: 0.1-60.0s)
  - Optional stagger timing to spread pings across hosts and avoid bursts
  - Per-host timing state tracking with monotonic time calculations
  - Mock event generation for testing purposes
  - **Benefits**: Keeps timeline columns aligned across hosts even with varying network latency

#### Global Rate Limit Protection
- **50 pings/sec global rate limit** to prevent network flooding and system overload
  - Enforced formula: `host_count / interval ≤ 50`
  - Pre-execution validation with clear error messages
  - Helpful suggestions when limit is exceeded (increase interval or reduce hosts)
  - **Safety**: Prevents accidental network flooding when monitoring many hosts
  - **Default behavior**: Tool exits with error if rate limit would be exceeded
  - Implementation: `validate_global_rate_limit()` in `paraping/core.py`
  - Test coverage: 15+ tests covering boundary conditions, error paths, and edge cases

#### Pending Markers & Timeline Synchronization
- **Real-time pending markers** to show pings in-flight before results arrive
  - Visual indicator: `-` (dark gray) appended immediately when ping is dispatched
  - Replaces pending marker with final status (`.` success, `!` slow, `x` fail) when response arrives
  - Keeps timeline columns synchronized across all hosts for easier visual comparison
  - Optional feature enabled via `emit_pending=True` parameter in `ping_host()`
  - **Benefits**: Improves UI responsiveness and allows operators to see ping activity before responses arrive
  - Implementation: "sent" events yielded by `ping_host()` before actual ping result
  - Timeline update logic handles pending slot replacement with sequence number validation

#### Per-Host Outstanding Ping Window Enforcement
- **SequenceTracker** (`paraping/sequence_tracker.py`): Manages ICMP sequence numbers and enforces maximum outstanding pings per host
  - Default limit: 3 outstanding pings per host
  - Prevents queue buildup and resource exhaustion
  - Thread-safe implementation with proper locking
  - Automatic uint16 sequence number wraparound (0-65535)
  - Per-host tracking with independent sequence counters
  - **Safety**: Prevents overwhelming slow or unresponsive hosts with too many concurrent pings
  - Test coverage: 16+ tests including thread safety, wraparound, and limit enforcement

### Changed
- **CLI help text**: Updated to include global rate limit note in `--interval` description
- **Error handling**: Rate limit validation now happens before ping execution begins
- **Timeline behavior**: Pending markers are now displayed by default for better visual feedback

### Documentation
- Added comprehensive test coverage (374 total tests):
  - 27 scheduler tests covering timing, stagger, and host management
  - 15 rate limit tests covering all boundary conditions and error paths
  - 26 pending marker tests covering emission, replacement, and edge cases
  - 16 sequence tracker tests covering outstanding ping window enforcement
  - 2 timeline synchronization tests for pending slot updates
- **README.md**: Documents global rate limit protection feature
- **CLI help**: Includes rate limit warning in interval parameter description
- **Test documentation**: All test modules include docstrings explaining coverage

### Technical Details

#### Scheduler Design
The scheduler uses wall-clock time calculations rather than accumulating sleep intervals:
```python
# First ping: apply stagger based on host index
next_time = start_time + (host_index * stagger)

# Subsequent pings: add interval to last ping time
next_time = last_ping_time + interval
```

This approach prevents timeline drift even when ping responses have varying latency.

#### Rate Limit Enforcement
Rate limit check is performed before starting ping operations:
```python
is_valid, rate, error = validate_global_rate_limit(host_count, interval)
if not is_valid:
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)
```

#### Pending Marker Flow
1. Scheduler determines it's time to ping a host
2. `ping_host()` with `emit_pending=True` yields a "sent" event immediately
3. CLI appends `-` (pending marker) to timeline
4. Actual ping is performed (may take up to timeout duration)
5. When response arrives, CLI replaces pending marker with final status
6. If no prior pending marker exists, final status is appended normally (fallback)

#### Outstanding Ping Window
The SequenceTracker enforces a maximum of 3 outstanding pings per host:
```python
sequence_tracker = SequenceTracker(max_outstanding=3)
seq = sequence_tracker.get_next_sequence(host)
if seq is None:
    # At limit, skip this ping
    continue
```

### Testing & Quality Assurance
- All 361 unit/integration/contract tests pass
- Linters: flake8, pylint, ruff (configurable via pyproject.toml)
- Formatters: black, isort
- Pre-commit hooks configured for quality checks
- Test coverage includes error paths, boundary conditions, and thread safety
- All new Python files include Apache-2.0 license headers and LLM attribution

### Migration Notes
- **No breaking changes**: All new features are backward compatible
- Rate limit is enforced by default; users with >50 hosts at 1s interval must increase interval
  - Example: 100 hosts requires ≥2.0s interval to stay under 50 pings/sec limit
- Pending markers are enabled by default in the TUI for better visual feedback
- Outstanding ping window (3 per host) is always enforced for stability

### Security & Safety
- **Rate limit protection** prevents accidental network flooding
- **Outstanding ping window** prevents resource exhaustion from slow hosts
- **SequenceTracker thread safety** prevents race conditions in concurrent ping operations
- All new code reviewed for security vulnerabilities
- No secrets or credentials stored in code
