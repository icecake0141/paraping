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

# ParaPing
[![CI/CD Pipeline](https://github.com/icecake0141/paraping/actions/workflows/ci.yml/badge.svg)](https://github.com/icecake0141/paraping/actions/workflows/ci.yml)
[![Dependabot Updates](https://github.com/icecake0141/paraping/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/icecake0141/paraping/actions/workflows/dependabot/dependabot-updates)
[![Dependabot — Run tests](https://github.com/icecake0141/paraping/actions/workflows/dependabot-test.yml/badge.svg)](https://github.com/icecake0141/paraping/actions/workflows/dependabot-test.yml)
[![PR Checks](https://github.com/icecake0141/paraping/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/icecake0141/paraping/actions/workflows/pr-checks.yml)

## Table of Contents / 目次

### 🇬🇧 English
- [English](#english)
- [Features](#features)
- [Requirements](#requirements)
  - [Linux-Specific: Privileged ICMP Helper (Recommended)](#linux-specific-privileged-icmp-helper-recommended)
- [Installation](#installation)
  - [Quick Start (Recommended)](#quick-start-recommended)
  - [Installation Methods Comparison](#installation-methods-comparison)
  - [Detailed Installation Instructions](#detailed-installation-instructions)
  - [Uninstalling ParaPing](#uninstalling-paraping)
  - [Building and Cleaning](#building-and-cleaning)
- [Usage](#usage)
  - [Command-line Options](#command-line-options)
  - [Environment Variables](#environment-variables)
  - [Interactive Controls](#interactive-controls)
  - [Timeline/Sparkline Legend](#timelinesparkline-legend)
- [Notes](#notes)
  - [Safety Features & Rate Limiting](#safety-features--rate-limiting)
- [Performance and Scalability](#performance-and-scalability)
  - [Current Architecture](#current-architecture)
  - [Multi-Host Performance](#multi-host-performance)
  - [Scalability Considerations](#scalability-considerations)
  - [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [Development & Validation](#development--validation)
  - [Setting Up Development Environment](#setting-up-development-environment)
  - [Building the Project](#building-the-project)
  - [Linting](#linting)
  - [Code Formatting](#code-formatting)
  - [Testing](#testing)
  - [Makefile Development Workflow](#makefile-development-workflow)
  - [Pre-PR Validation Checklist](#pre-pr-validation-checklist)
- [Supplement: ASN Lookup Mechanisms](#supplement-asn-lookup-mechanisms)
- [Supplement: rDNS Result Caching Behavior](#supplement-rdns-result-caching-behavior)
- [License](#license)

### 🇯🇵 日本語
- [日本語](#日本語)
  - [機能](#機能)
  - [要件](#要件)
  - [インストール](#インストール)
    - [クイックスタート（推奨）](#クイックスタート推奨)
    - [インストール方法の比較](#インストール方法の比較)
    - [詳細なインストール手順](#詳細なインストール手順)
    - [ParaPing のアンインストール](#paraping-のアンインストール)
    - [ビルドとクリーンアップ](#ビルドとクリーンアップ)
  - [使い方](#使い方)
    - [コマンドラインオプション](#コマンドラインオプション)
    - [インタラクティブ操作](#インタラクティブ操作)
    - [タイムライン / スパークライン凡例](#タイムライン--スパークライン凡例)
  - [注意事項](#注意事項)
  - [パフォーマンスとスケーラビリティ](#パフォーマンスとスケーラビリティ)
    - [現行アーキテクチャ](#現行アーキテクチャ)
    - [マルチホスト性能](#マルチホスト性能)
    - [スケーラビリティに関する考慮事項](#スケーラビリティに関する考慮事項)
    - [将来の拡張](#将来の拡張)
  - [貢献](#貢献)
  - [開発と検証](#開発と検証)
    - [プロジェクトのビルド](#プロジェクトのビルド)
    - [Linting](#linting-1)
    - [テスト](#テスト)
    - [PR 前検証チェックリスト](#pr-前検証チェックリスト)
- [補足: ASN ルックアップメカニズム](#補足-asn-ルックアップメカニズム)
- [補足: rDNS 結果のキャッシング動作](#補足-rdns-結果のキャッシング動作)
  - [ライセンス](#ライセンス)

## English

ParaPing is an interactive, terminal-based ICMP monitor that pings many hosts in parallel and visualizes results as a live timeline or sparkline. It provides operator controls for sorting, filtering, pausing, snapshots, and per-host RTT inspection to aid rapid network triage.

## Features
- Concurrent ICMP ping to multiple hosts (capability-based helper binary).
- Live timeline or sparkline visualization with success/slow/fail/pending markers.
- **Real-time pending markers**: Visual indicator (`-`) shows pings in-flight before results arrive, keeping timeline columns synchronized across hosts for easier comparison.
- **Time-driven scheduler**: Precise wall-clock-based scheduling eliminates timeline drift, ensuring columns stay aligned even with varying network latency.
- Animated activity indicator (Knight Rider-style) while pings are running.
- Summary panel with host statistics, RTT jitter/standard deviation, aggregate counts, and TTL display.
- Boxed panel layout for ping results, summaries, and the status line.
- Summary host ordering matches the current ping result sort order.
- Sort and filter results by failures, streaks, latency, or host name.
- Toggle display name mode: IP, reverse DNS, or alias.
- Optional ASN display (fetched from Team Cymru) with auto-retry.
- Optional colored output for success/slow/fail states.
- Pause modes: freeze display only (`p`) or use Dormant Mode (`P`) to pause ping + display.
- Snapshot export to a timestamped text file.
- Fullscreen ASCII RTT graph per host with axis labels and scale, including X-axis seconds-ago labels (selectable via TUI).
- Configurable timezone for timestamps and snapshot naming.
- Input file support for host lists (one per line in `IP,alias` format; comments allowed).
- **Global rate limit protection**: Enforces a maximum of 50 pings/sec globally (host_count / interval ≤ 50) to prevent network flooding. The tool will exit with an error if this limit is exceeded.
- **Per-host outstanding ping window**: Maximum of 3 concurrent pings per host prevents queue buildup and resource exhaustion when monitoring slow or unresponsive hosts.

## Requirements
- Python 3.9 or newer.
- The `ping_helper` binary built with `cap_net_raw` (Linux) to run without `sudo`.
- Root/administrator privileges if you cannot use the helper (non-Linux platforms).
- Network access for optional ASN lookups.
- IPv4-only ping support: IPv6 addresses can be specified in configuration files but will likely fail during ping. When a hostname resolves to both IPv4 and IPv6 addresses, IPv4 is automatically preferred.

### Linux-Specific: Privileged ICMP Helper (Recommended)

On Linux, use the included `ping_helper` binary with capability-based privileges instead of running Python as root. This is more secure as it limits raw socket access to a single small binary. The helper also connects its raw socket and applies ICMP filters to reduce per-process packet fan-out, which improves reliability when monitoring many hosts concurrently.

**Dependencies:**
- `gcc` (for building the helper)
- `libcap2-bin` (for setting capabilities with `setcap`)

Install dependencies on Debian/Ubuntu:
```bash
sudo apt-get install gcc libcap2-bin
```

**Build and configure the helper:**
```bash
# Build the helper binary (source: src/native/ping_helper.c, output: bin/ping_helper)
make build

# Set capabilities (requires sudo)
sudo make setcap

# Test the helper
python3 paraping/ping_wrapper.py google.com
```

If `ping_wrapper.py` fails, its JSON output includes an `error` field with details from `ping_helper` (including stderr when available) to aid troubleshooting.

**Helper CLI Contract:**
The `ping_helper` binary accepts the following arguments:
```bash
ping_helper <host> <timeout_ms> [icmp_seq]
```
- `<host>`: Hostname or IPv4 address (required)
- `<timeout_ms>`: Timeout in milliseconds, 1-60000 (required)
- `[icmp_seq]`: Optional ICMP sequence number, 0-65535 (default: 1)

**Output and Exit Codes:**
- **Success (exit 0)**: Prints `rtt_ms=<value> ttl=<value>` to stdout
- **Timeout (exit 7)**: No output, returns exit code 7 (normal timeout, not an error)
- **Errors (exit 1-6, 8)**: Error message to stderr with specific exit codes:
  - 1: Invalid arguments
  - 2: Argument validation error (timeout_ms or icmp_seq out of range)
  - 3: Host resolution failed
  - 4: Socket error or insufficient privileges
  - 5: Send error
  - 6: Select error
  - 8: Receive error

**Documentation:** For detailed information about `ping_helper`'s design, CLI contract, validation logic, and limitations, see [docs/ping_helper.md](docs/ping_helper.md).

**Note for macOS/BSD users:** The `setcap` command is Linux-specific and not available on macOS or BSD systems. On these platforms, you would need to use the setuid bit instead (e.g., `sudo chown root:wheel bin/ping_helper && sudo chmod u+s bin/ping_helper`), but this is less secure and not recommended. Follow platform best practices for granting minimal privilege.

**Security Note:** Never grant `cap_net_raw` or any capabilities to `/usr/bin/python3` or other general-purpose interpreters. Only grant the minimal required privilege to the specific `ping_helper` binary.

## Installation

ParaPing supports multiple installation methods to suit different workflows and user preferences. Choose the method that works best for you.

### Quick Start (Recommended)

For most users, we recommend the **simple make approach** which creates a local virtual environment:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Setup user environment (creates .venv and builds ping_helper)
make

# On Linux: Configure ICMP helper capabilities (requires sudo)
sudo make setcap

# Run paraping
make run ARGS='--help'
# Or run directly
python3 paraping.py --help
```

This approach:
- Creates a `.venv` virtual environment in the repository
- Builds the `ping_helper` binary for ICMP operations
- Provides a `paraping.py` executable at the repository root
- No installation to system or user site-packages required
- Works on Linux, macOS, and Windows (setcap is Linux-only)

**To see all available commands:**
```bash
make help
```

### Installation Methods Comparison

| Method | Use Case | Requires sudo | PATH | Dependency Management |
|--------|----------|--------------|------|----------------------|
| `make` (default) | **Quickest start** - local venv | No (except setcap) | Not needed | venv isolated |
| `make install-user` | Install as command | No (except setcap) | `~/.local/bin` | pip handles it |
| `make install-system` | System-wide, all users | Yes | `/usr/local/bin` | pip handles it |
| `make install-wrapper` | Minimal, no pip install | Yes | `/usr/local/bin` | Manual PYTHONPATH |
| `pipx install .` | Isolated environment | No | `~/.local/bin` | pipx handles it |
| `pip install -e .` | Development/editable | No | Current venv | pip handles it |

### Detailed Installation Instructions

#### 0. Quick Setup with Virtual Environment (Fastest)

Creates a local `.venv` and runs from the repository without installing:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# One command setup (creates .venv and builds ping_helper)
make

# On Linux: Configure ICMP helper (requires sudo)
sudo make setcap

# Run the tool
make run ARGS='8.8.8.8 1.1.1.1'
# Or activate venv and run directly
source .venv/bin/activate
python paraping.py --help
```

**Pros:**
- Fastest setup - no pip installation needed
- Isolated environment in `.venv`
- Run with `make run ARGS='...'` or `python3 paraping.py`
- No PATH configuration required
- Easy cleanup with `make clean`
- **Recommended for quick testing or casual use**

**Cons:**
- Must run from repository directory
- `paraping` command not globally available

#### 1. User-Level Installation

Installs to `~/.local` for the current user only. No sudo needed, clean uninstall, doesn't affect system Python. **Recommended if you want the `paraping` command available globally.**

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install the package for current user
make install-user

# Build and configure the ICMP helper (Linux only)
make build
sudo make setcap

# Verify installation
paraping --help
```

**PATH Configuration:** If `paraping` command is not found, add `~/.local/bin` to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Pros:**
- No sudo required for Python package installation
- Clean separation from system Python packages
- Easy to uninstall with `make uninstall-user`
- Recommended for most users

**Cons:**
- Requires `~/.local/bin` in PATH (usually automatic on modern systems)
- Per-user installation (won't be available for other users)

#### 2. System-Wide Installation

Installs to system-wide Python site-packages. Requires sudo. Available for all users.

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install the package system-wide (requires sudo)
make install-system

# Build and configure the ICMP helper (Linux only)
make build
sudo make setcap

# Verify installation
paraping --help
```

**Pros:**
- Available for all users on the system
- Command installed to `/usr/local/bin` (always in PATH)

**Cons:**
- Requires sudo for installation
- May conflict with system Python packages
- Harder to clean up

#### 3. Wrapper Script Installation (Advanced)

Installs a lightweight shell wrapper without pip. Requires manual PYTHONPATH setup.

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install wrapper script to /usr/local/bin
make install-wrapper

# Build and configure the ICMP helper (Linux only)
make build
sudo make setcap

# The wrapper expects the paraping module to be importable
# Either install with make install-user/install-system first,
# or set PYTHONPATH when running:
export PYTHONPATH=/path/to/paraping:$PYTHONPATH
paraping --help
```

**Pros:**
- Minimal installation footprint
- No pip dependency tracking
- Can run from any directory

**Cons:**
- Requires manual PYTHONPATH management OR prior pip install
- Not recommended unless you have specific requirements

#### 4. Using pipx (Alternative)

If you use `pipx` for isolated Python CLI tools:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install using pipx (installs in isolated environment)
pipx install .

# Build and configure the ICMP helper (Linux only)
make build
sudo make setcap

# Verify installation
paraping --help
```

**Pros:**
- Isolated virtual environment per tool
- Automatic PATH management
- Clean uninstall with `pipx uninstall paraping`

**Cons:**
- Requires pipx to be installed
- Slightly more complex dependency management

#### 5. Development Installation (Editable Mode)

For development or contributing to ParaPing:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install in editable mode (changes reflect immediately)
pip install -e .

# Build the privileged ICMP helper (Linux only)
make build
sudo make setcap

# Run from anywhere, changes take effect immediately
paraping --help
```

**Pros:**
- Changes to code take effect immediately without reinstall
- Ideal for development and testing
- Works in virtual environments

**Cons:**
- Requires keeping the source directory
- Not suitable for production use

#### 6. Legacy Installation (Without Package Installation)

Run directly from the repository without installing:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping
python3 -m pip install -r requirements.txt

# Build the privileged ICMP helper (Linux only)
make build
sudo make setcap

# Run directly from the repository
python3 -m paraping --help
# Or use the main.py wrapper
./main.py --help
```

**Note:** ParaPing requires the `readchar` package (see `requirements.txt`). Install it with `pip install -r requirements.txt` before running.

### Uninstalling ParaPing

Depending on how you installed ParaPing:

```bash
# Uninstall user-level installation
make uninstall-user

# Uninstall system-wide installation
make uninstall-system

# Remove wrapper script
make uninstall-wrapper

# Using pipx
pipx uninstall paraping

# Using pip directly
pip uninstall paraping
```

### Building and Cleaning

```bash
# Build the Python wheel package
make build-python

# Clean Python build artifacts
make clean-python

# Clean all build artifacts (Python + C helper)
make clean
```

**Note:** The native `ping_helper` binary must be built separately using `make build` and configured with capabilities using `sudo make setcap` (Linux only) regardless of the Python installation method chosen.

## Usage

![ParaPing Demo](docs/images/usage-demo.gif)

```bash
./paraping [options] <host1> <host2> ...
```

Example (with a host list file and 2-second timeout):
```bash
./paraping -t 2 -f hosts.txt
```
Example (explicit IPv4 addresses only):
```bash
./paraping 1.1.1.1 8.8.8.8
```

### Command-line Options
- `-t`, `--timeout`: Timeout in seconds for each ping (default: 1).
- `-c`, `--count`: Number of ping attempts per host (default: 0 for infinite).
- `-i`, `--interval`: Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0). **Note**: Global rate limit is 50 pings/sec; the tool will fail if (host_count / interval) > 50.
- `-s`, `--slow-threshold`: RTT threshold (seconds) to mark a ping as slow (default: 0.5).
- `-v`, `--verbose`: Enable detailed per-packet logging output (non-UI mode).
- `--log-level`: Logging level (`DEBUG|INFO|WARNING|ERROR`, default: `INFO`).
- `--log-file`: Optional log file path for persistent logging.
- `-f`, `--input`: Read hosts from a file (one per line; format: `IP,alias`; `#` comments supported).
- `-P`, `--panel-position`: Summary panel position (`right|left|top|bottom|none`).
- `-m`, `--pause-mode`: Pause behavior (`display|ping`).
- `-z`, `--timezone`: IANA timezone name for on-screen timestamps.
- `-Z`, `--snapshot-timezone`: Timezone for snapshot filenames (`utc|display`).
- `-F`, `--flash-on-fail`: Flash screen (invert colors) when a ping fails to draw attention.
- `-B`, `--bell-on-fail`: Ring terminal bell when a ping fails to draw attention.
- `-C`, `--color`: Enable colored output (blue=success, yellow=slow, red=fail).
- `-H`, `--ping-helper`: Path to the `ping_helper` binary (default: `./bin/ping_helper`).

### Environment Variables
- `PARAPING_PING_RATE`: Override the estimated global ping send rate shown in the status line (pings/sec).
- `PARAPING_PING_INTERVAL`: Override the per-host ping interval (seconds) used to estimate the status line rate when `PARAPING_PING_RATE` is unset.

### Interactive Controls
- `n`: Cycle display name mode (ip/rdns/alias).
- `v`: Toggle view (timeline/sparkline).
- `g`: Open host selection for fullscreen RTT graph.
- `o`: Cycle sort (failures/streak/latency/host).
- `f`: Cycle filter (failures/latency/all).
- `a`: Toggle ASN display (auto hides when space is tight).
- `m`: Cycle summary info (rates/avg RTT/TTL/streak).
- `c`: Toggle colored output.
- `b`: Toggle terminal bell on ping failure.
- `F`: Toggle summary fullscreen view.
- `w`: Toggle the summary panel on/off.
- `W`: Cycle summary panel position (left/right/top/bottom).
- `p`: Pause/resume display updates.
- `P`: Toggle Dormant Mode (pause ping monitoring + display updates).
- `s`: Save a snapshot to `paraping_snapshot_YYYYMMDD_HHMMSS.txt`.
- `←` / `→`: Navigate backward/forward in time by one page. History keeps recording while browsing; the view is frozen until you return to live.
- `↑` / `↓`: Scroll the host list (when not in host-selection mode). In host-selection mode use `n` (next) and `p` (previous) to move the selection; when the selection moves beyond the visible area, the host list scrolls to keep the selection in view.
- `H`: Show help (press any key to close).
- `ESC`: Exit fullscreen graph.
- `q`: Quit.

### Timeline/Sparkline Legend
- `.` success
- `!` slow (RTT >= `--slow-threshold`)
- `x` failure/timeout
- `-` pending (ping sent but response not yet received)
- When `--color` is enabled: white=success, yellow=slow, red=failure, dark gray=pending.

## Notes
- ICMP requires elevated privileges (run with `sudo` or Administrator on Windows) unless using the capability-based helper on Linux.
- ASN lookups use `whois.cymru.com`; blocked networks will show blank ASN values.
- IPv6 addresses can be specified but pinging will likely fail (ping_helper only supports IPv4). When hostnames resolve to both IPv4 and IPv6, IPv4 is automatically preferred.
- The monitor starts one worker thread per host and enforces a hard limit of 128 hosts. It exits with an error if exceeded.
- When the summary panel is positioned at the top/bottom, it expands to use available empty rows.
- When the summary panel is positioned at the top/bottom, it shows all summary fields if the width allows.

### Safety Features & Rate Limiting

#### Global Rate Limit (50 pings/sec)
ParaPing enforces a **maximum of 50 pings per second** globally to prevent network flooding and system overload. The rate is calculated as:

```
rate = host_count / interval
```

For example:
- ✅ **Valid**: 50 hosts at 1.0s interval = 50 pings/sec (at limit)
- ✅ **Valid**: 25 hosts at 0.5s interval = 50 pings/sec (at limit)
- ✅ **Valid**: 100 hosts at 2.0s interval = 50 pings/sec (at limit)
- ❌ **Invalid**: 100 hosts at 1.0s interval = 100 pings/sec (exceeds limit)
- ❌ **Invalid**: 51 hosts at 1.0s interval = 51 pings/sec (exceeds limit)

If you exceed the limit, ParaPing will exit with an error message suggesting:
- Increase the `--interval` value
- Reduce the number of hosts
- Split monitoring across multiple instances

**Why this limit?** The 50 pings/sec limit protects against:
- Overwhelming network devices or firewalls
- Triggering rate-limiting or IDS alerts
- Consuming excessive system resources (CPU, file descriptors, kernel buffers)

#### Per-Host Outstanding Ping Window (3 concurrent pings max)
ParaPing limits each host to a maximum of **3 outstanding pings** (sent but not yet replied) to prevent resource exhaustion when monitoring slow or unresponsive hosts.

**Benefits:**
- Prevents queue buildup from hosts with high latency or packet loss
- Avoids consuming excessive file descriptors and memory
- Ensures responsive behavior even when some hosts are slow

**Behavior:** If a host already has 3 pings in-flight, ParaPing will skip sending additional pings until at least one completes or times out.

#### Time-Driven Scheduler
ParaPing uses a **wall-clock-based scheduler** rather than sleep-based timing to eliminate timeline drift:

**Traditional approach (accumulates drift):**
```python
while True:
    send_ping()
    sleep(interval)  # Actual delay = interval + ping_time + processing
```

**ParaPing approach (eliminates drift):**
```python
next_ping_time = start_time + (ping_count * interval)
wait_until(next_ping_time)
send_ping()
```

**Benefits:**
- Timeline columns stay perfectly aligned across all hosts
- Visual comparison is easier when columns represent the same time offset
- No drift accumulation even with varying network latency

**Stagger timing (per-host ping delay):** ParaPing automatically introduces a small time offset between pings to different hosts to reduce simultaneous ICMP burst load. The stagger value is calculated as `interval / number_of_hosts`, so each host's first ping is delayed by `host_index × stagger` seconds relative to the start:

```
Host 0: ping at t=0.0s, t=1.0s, t=2.0s, ...
Host 1: ping at t=0.1s, t=1.1s, t=2.1s, ...  (stagger=0.1s with 10 hosts, 1s interval)
Host 2: ping at t=0.2s, t=1.2s, t=2.2s, ...
```

This design ensures that the ICMP traffic is evenly distributed over the interval, preventing all hosts from being pinged at exactly the same instant and reducing peak load on both the monitoring host and the network.

#### Pending Markers & Timeline Synchronization
ParaPing displays **real-time pending markers** (`-`) to show pings in-flight:

**Flow:**
1. Scheduler determines it's time to ping a host
2. Pending marker `-` is immediately appended to the timeline
3. Ping is sent (may take up to timeout duration)
4. When response arrives, pending marker is replaced with final status (`.`, `!`, or `x`)

**Benefits:**
- Immediate visual feedback that pings are being sent
- Timeline columns stay synchronized even with varying network latency
- Easier to distinguish between "no ping sent yet" and "ping sent but waiting for response"

**Example timeline progression:**
```
Time 0.0s: -         (ping sent, waiting)
Time 0.5s: .         (response received, replaced - with .)
Time 1.0s: -.        (next ping sent)
Time 1.1s: ..        (response received)
```

## Performance and Scalability

### Current Architecture
ParaPing uses a **one helper process per ping** model where each ping invocation spawns a new `ping_helper` process. This design prioritizes:
- **Security**: Minimal privilege separation with capability-based access control
- **Simplicity**: Each helper is independent with no shared state
- **Reliability**: Process isolation prevents one failed ping from affecting others

### Multi-Host Performance
The current architecture is optimized for **moderate concurrent host monitoring** (up to 128 hosts):
- Each host runs in its own worker thread with independent ping processes
- Connected sockets and ICMP filters reduce per-process packet fan-out
- 256KB receive buffers minimize packet drops under high ICMP volume

### Scalability Considerations
For high-volume or batch scenarios (hundreds of hosts, sub-second intervals):
- **Process overhead**: Spawning processes adds ~1-5ms latency per ping
- **System limits**: Each ping creates a raw socket; check `ulimit -n` for file descriptor limits
- **Kernel load**: High ping rates may require tuning socket buffer sizes or ICMP rate limits

### Future Enhancements
Potential optimizations for large-scale deployments (not currently implemented):
- **Batch mode**: Single helper process handling multiple hosts to reduce process spawn overhead
- **Persistent workers**: Long-lived helper processes accepting multiple ping requests
- **Shared socket pool**: Reusable raw sockets for same-destination pings

**Note**: The current one-process-per-ping model is intentional and provides the best security/reliability trade-off for typical monitoring workloads (1-128 hosts at 1-second intervals). For different workloads, consider the above optimizations.

## Contributing
Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines, code quality standards, and how to submit pull requests.

For information about the codebase modularization, module ownership boundaries, test organization, and coverage reporting, see [MODULARIZATION.md](docs/MODULARIZATION.md).

## Development & Validation

This section provides exact commands for validating your changes locally before submitting a pull request. These commands match the CI pipeline configuration and must pass for PRs to be merged.

### Setting Up Development Environment

**Quick setup using the Makefile (Recommended):**
```bash
# Setup development environment with all dev tools
make dev
```

This command creates a `.venv`, installs all development dependencies (pytest, flake8, pylint, black, ruff, isort, mypy), installs pre-commit hooks, and builds the `ping_helper` binary.

**Activate the development environment:**
```bash
source .venv/bin/activate
```

**Alternative manual setup:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make build
```

### Building the Project

**Build the ICMP helper binary:**
```bash
make build
```

**Set capabilities (Linux only, requires sudo):**
```bash
sudo make setcap
```

**Platform notes:**
- **Linux**: Use `setcap` to grant `cap_net_raw` to the `ping_helper` binary. This is more secure than running Python as root.
- **macOS/BSD**: The `setcap` command is not available. You can use the setuid bit (`sudo chown root:wheel bin/ping_helper && sudo chmod u+s bin/ping_helper`), but this is not recommended for security reasons.
- **Security**: Never grant `cap_net_raw` or any capabilities to general-purpose interpreters like `/usr/bin/python3`. Only grant the minimal required privilege to the specific `ping_helper` binary.

### Linting

The CI pipeline enforces strict linting standards. Run these commands locally before submitting a PR:

**Using the Makefile (runs all linters):**
```bash
make lint
```

**Manual linting commands:**

**1. Flake8 (strict - MUST PASS):**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```
This checks for Python syntax errors and undefined names. Zero errors required.

**2. Flake8 (style - informational):**
```bash
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```
This reports style violations (line length, complexity, PEP 8). Currently informational only, but fixing these issues is encouraged.

**3. Pylint (code quality - MUST PASS):**
```bash
pylint . --fail-under=9.0
```
This checks code quality and must score at least 9.0/10 to pass.

**4. Mypy (type checking - MUST PASS):**
```bash
mypy
```
This enforces strict type checking based on `pyproject.toml`.

**Run all lint checks at once:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics && \
pylint . --fail-under=9.0 && \
mypy
```

### Code Formatting

**Format code using the Makefile:**
```bash
make format
```

This runs `black` and `isort` to automatically format your code according to project standards.

### Testing

**Run tests using the Makefile:**
```bash
make test
```

**Manual testing commands:**

**Run all tests with coverage (matches CI):**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

**Generate HTML coverage report for detailed analysis:**
```bash
pytest tests/ -v --cov=. --cov-report=html
# View report: open htmlcov/index.html in browser
```

**Run specific test file:**
```bash
pytest tests/test_main.py -v
```

**Check coverage by module:**
```bash
pytest tests/ --cov=. --cov-report=term
```

**Run tests with minimum coverage threshold:**
```bash
pytest tests/ --cov=. --cov-report=term --cov-fail-under=80
```

All tests must pass before submitting a PR. Add tests for new functionality.

### Makefile Development Workflow

The Makefile provides convenient targets for common development tasks:

```bash
make help        # Show all available targets
make dev         # Setup development environment
make test        # Run test suite
make lint        # Run all linters
make format      # Format code with black and isort
make run         # Run paraping with ARGS='...'
make clean       # Clean all build artifacts
```

### Pre-PR Validation Checklist


Before opening a pull request, ensure you:
1. ✅ Build the project: `make build` (Linux) or verify the helper compiles
2. ✅ Run lint checks: all three flake8/pylint commands above must pass
3. ✅ Run mypy type checks: `mypy`
4. ✅ Run tests: `pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml`
5. ✅ Update documentation if behavior changed
6. ✅ Follow the [LLM PR policy](.github/workflows/copilot-instructions.md) if using AI assistance (include license headers, LLM attribution, and validation commands in your PR description)

For complete contribution guidelines, see [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Supplement: ASN Lookup Mechanisms

ASN lookups via Team Cymru whois service use the following mechanisms to ensure efficiency and responsible resource usage:

- **Caching**: Successful lookups are cached for the program session, eliminating redundant queries for the same IP
- **Retry with TTL**: Failed lookups are retried after a 5-minute delay, preventing excessive requests
- **Thread Management**: A single worker thread processes requests sequentially, avoiding service overload

## Supplement: rDNS Result Caching Behavior

Reverse DNS (rDNS) results for IP addresses are cached at the first attempt: if name resolution succeeds, the hostname is stored and always reused; if it fails, None is stored and reused. There is no automatic retry or repeated lookup once the initial resolution is complete.

## License
Apache License 2.0. See [LICENSE](LICENSE).

---

## 日本語

ParaPing は、複数のホストへ並列に ICMP ping を実行し、ライブのタイムラインまたはスパークラインとして結果を可視化する対話型のターミナルツールです。ソート、フィルタ、一時停止、スナップショット、ホストごとの RTT のフルスクリーングラフなどの操作が可能で、ネットワークのトラブルシュートに便利な情報を提供します。

### 機能
- 複数ホストへの並列 ICMP ping（capability ベースの補助バイナリを利用）
- 成功 / 遅延 / 失敗を示すライブのタイムライン / スパークライン表示
- 動的なアクティビティインジケータ（Knight Rider スタイル）
- ホスト別統計（RTT、ジッタ、標準偏差、集計カウント、TTL など）を表示するサマリーパネル
- 結果、サマリー、ステータス行をボックス化して表示
- 現在のソート順に合わせたサマリーホストの並び替え
- 失敗数・連続失敗・レイテンシ・ホスト名でのソートおよびフィルタリング
- 表示名モード切替：IP / 逆引き（rDNS）/ エイリアス
- 任意で ASN 表示（Team Cymru による取得、リトライ機能付き）
- 成功 / 遅延 / 失敗に応じた色分け（オプション）
- 表示のみ停止または ping も停止する一時停止モード
- タイムスタンプ付きスナップショットのテキスト出力
- ホストごとのフルスクリーン ASCII RTT グラフ（軸ラベル、スケール、X 軸に「何秒前」ラベル）
- タイムゾーン設定（画面表示・スナップショット名に利用可能）
- 入力ファイル対応（1 行に `IP,alias`、`#` 行はコメントとして無視）

### 要件
- Python 3.9 以上
- Linux では `cap_net_raw` を付与した `ping_helper` バイナリを使うことで通常ユーザ権限で実行可能
- 補助バイナリを使えない環境では管理者権限（sudo / Administrator）が必要
- ASN 取得を行う場合はネットワーク接続が必要（whois.cymru.com を使用）
- IPv4 のみサポート（ホストは IPv4 に解決される必要あり）

#### Linux 特有: 権限を限定する ICMP ヘルパー（推奨）
Linux では Python を root で動かす代わりに、小さな専用バイナリ（`ping_helper`）だけに必要な権限を与えるやり方を推奨します。これにより権限を最小化できます。ヘルパーは生ソケットを用い、ICMP フィルタを適用してパケットのファンアウトを抑えるため、多数ホストの同時監視で安定性が高まります。

依存パッケージ（Debian/Ubuntu の例）:
```bash
sudo apt-get install gcc libcap2-bin
```

ビルドと設定手順:
```bash
# ヘルパーをビルド（ソース: src/native/ping_helper.c、出力: bin/ping_helper）
make build

# ヘルパーに必要な capability を付与（sudo が必要）
sudo make setcap

# 動作確認（例）
python3 paraping/ping_wrapper.py google.com
```

ヘルパーの CLI（引数）:
```bash
ping_helper <host> <timeout_ms> [icmp_seq]
```
- `<host>`: ホスト名または IPv4 アドレス（必須）
- `<timeout_ms>`: タイムアウト（ミリ秒、1〜60000、必須）
- `[icmp_seq]`: ICMP シーケンス番号（オプション、0〜65535、デフォルト 1）

出力と終了コードの概略:
- 成功（exit 0）: stdout に `rtt_ms=<value> ttl=<value>`
- タイムアウト（exit 7）: 出力なし（正常なタイムアウト）
- エラー（exit 1–6, 8）: stderr にエラーメッセージ（引数エラー、解決失敗、ソケット/送受信エラー等）

macOS / BSD の注意:
- `setcap` は Linux 固有です。macOS / BSD では setuid による手段がありますが、セキュリティ上の理由で推奨しません。各プラットフォームのベストプラクティスに従って最小権限化してください。

セキュリティ注意:
- 汎用インタプリタ（例: `/usr/bin/python3`）へ `cap_net_raw` 等の権限を与えないでください。特定の小さなヘルパーバイナリのみに権限を付与してください。

### インストール

ParaPing は複数のインストール方法をサポートしています。自分のワークフローに合った方法を選択してください。

#### クイックスタート（推奨）

ほとんどのユーザーには、sudo を必要としない `~/.local` へのユーザーレベルインストールを推奨します：

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# 現在のユーザー用にインストール（sudo 不要）
make install-user

# 権限付与された ICMP ヘルパーをビルド（Linux のみ）
make build
sudo make setcap

# paraping を実行
paraping --help
```

**PATH 設定:** `paraping` コマンドが見つからない場合、`~/.local/bin` を PATH に追加してください：
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### インストール方法の比較

| 方法 | 用途 | sudo が必要 | PATH | 依存関係管理 |
|------|------|------------|------|-------------|
| `make install-user` | **推奨** ほとんどのユーザー向け | いいえ（setcap 以外） | `~/.local/bin` | pip が管理 |
| `make install-system` | システム全体、全ユーザー | はい | `/usr/local/bin` | pip が管理 |
| `make install-wrapper` | 最小限、pip インストールなし | はい | `/usr/local/bin` | 手動 PYTHONPATH |
| `pipx install .` | 隔離された環境 | いいえ | `~/.local/bin` | pipx が管理 |
| `pip install -e .` | 開発/編集可能 | いいえ | 現在の venv | pip が管理 |

#### 詳細なインストール手順

##### 1. ユーザーレベルインストール（推奨）

現在のユーザーのみ用に `~/.local` へインストールします。sudo 不要、クリーンなアンインストール、システム Python に影響しません。

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# 現在のユーザー用にパッケージをインストール
make install-user

# ICMP ヘルパーをビルドして設定（Linux のみ）
make build
sudo make setcap

# インストールを確認
paraping --help
```

**利点:**
- Python パッケージのインストールに sudo が不要
- システム Python パッケージからクリーンに分離
- `make uninstall-user` で簡単にアンインストール
- ほとんどのユーザーに推奨

**欠点:**
- PATH に `~/.local/bin` が必要（最近のシステムでは通常自動）
- ユーザーごとのインストール（他のユーザーには利用できない）

##### 2. システム全体へのインストール

システム全体の Python site-packages へインストールします。sudo が必要です。全ユーザーが利用可能です。

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# パッケージをシステム全体にインストール（sudo が必要）
make install-system

# ICMP ヘルパーをビルドして設定（Linux のみ）
make build
sudo make setcap

# インストールを確認
paraping --help
```

**利点:**
- システム上の全ユーザーが利用可能
- コマンドは `/usr/local/bin` にインストール（常に PATH に含まれる）

**欠点:**
- インストールに sudo が必要
- システム Python パッケージと競合する可能性
- クリーンアップが困難

##### 3. ラッパースクリプトインストール（上級者向け）

pip を使用せずに軽量なシェルラッパーをインストールします。手動で PYTHONPATH を設定する必要があります。

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# /usr/local/bin にラッパースクリプトをインストール
make install-wrapper

# ICMP ヘルパーをビルドして設定（Linux のみ）
make build
sudo make setcap

# ラッパーは paraping モジュールがインポート可能であることを期待します
# まず make install-user/install-system でインストールするか、
# 実行時に PYTHONPATH を設定してください：
export PYTHONPATH=/path/to/paraping:$PYTHONPATH
paraping --help
```

**利点:**
- 最小限のインストールフットプリント
- pip 依存関係追跡なし
- どのディレクトリからでも実行可能

**欠点:**
- 手動での PYTHONPATH 管理が必要、または事前の pip インストールが必要
- 特定の要件がない限り推奨しません

##### 4. pipx の使用（代替手段）

Python CLI ツールの隔離に `pipx` を使用する場合：

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# pipx を使用してインストール（隔離環境にインストール）
pipx install .

# ICMP ヘルパーをビルドして設定（Linux のみ）
make build
sudo make setcap

# インストールを確認
paraping --help
```

**利点:**
- ツールごとに隔離された仮想環境
- 自動 PATH 管理
- `pipx uninstall paraping` でクリーンにアンインストール

**欠点:**
- pipx のインストールが必要
- やや複雑な依存関係管理

##### 5. 開発インストール（編集可能モード）

ParaPing の開発やコントリビューションの場合：

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# 編集可能モードでインストール（変更がすぐに反映される）
pip install -e .

# 権限付与された ICMP ヘルパーをビルド（Linux のみ）
make build
sudo make setcap

# どこからでも実行可能、変更がすぐに有効になる
paraping --help
```

**利点:**
- コードの変更が再インストールなしですぐに反映される
- 開発とテストに最適
- 仮想環境で動作

**欠点:**
- ソースディレクトリを保持する必要がある
- 本番環境での使用には不適切

##### 6. レガシーインストール（パッケージインストールなし）

インストールせずにリポジトリから直接実行：

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping
python3 -m pip install -r requirements.txt

# 権限付与された ICMP ヘルパーをビルド（Linux のみ）
make build
sudo make setcap

# リポジトリから直接実行
python3 -m paraping --help
# または main.py ラッパーを使用
./main.py --help
```

**注:** ParaPing は `readchar` パッケージに依存しています（`requirements.txt` 参照）。実行前に `pip install -r requirements.txt` でインストールしてください。

#### ParaPing のアンインストール

インストール方法に応じて：

```bash
# ユーザーレベルインストールをアンインストール
make uninstall-user

# システム全体のインストールをアンインストール
make uninstall-system

# ラッパースクリプトを削除
make uninstall-wrapper

# pipx を使用
pipx uninstall paraping

# pip を直接使用
pip uninstall paraping
```

#### ビルドとクリーンアップ

```bash
# Python wheel パッケージをビルド
make build-python

# Python ビルド成果物をクリーンアップ
make clean-python

# すべてのビルド成果物をクリーンアップ（Python + C ヘルパー）
make clean
```

**注:** ネイティブ `ping_helper` バイナリは、選択した Python インストール方法に関係なく、`make build` を使用して個別にビルドし、`sudo make setcap`（Linux のみ）を使用して capabilities を設定する必要があります。

### 使い方

![ParaPing デモ](docs/images/usage-demo.gif)

```bash
./paraping [options] <host1> <host2> ...
```

例（ホスト一覧ファイルを使用しタイムアウト 2 秒）:
```bash
./paraping -t 2 -f hosts.txt
```

例（IPv4 を直接指定）:
```bash
./paraping 1.1.1.1 8.8.8.8
```

#### コマンドラインオプション
- `-t`, `--timeout`: 各 ping のタイムアウト（秒、デフォルト 1）
- `-c`, `--count`: 各ホストの ping 回数（デフォルト 0 = 無限）
- `-i`, `--interval`: ping 間隔（秒、デフォルト 1.0、範囲 0.1–60.0）
- `-s`, `--slow-threshold`: 遅延判定の RTT 閾値（秒、デフォルト 0.5）
- `-v`, `--verbose`: ログ出力向けの詳細 ping 情報（非 UI）
- `--log-level`: ログレベル（`DEBUG|INFO|WARNING|ERROR`、デフォルト `INFO`）
- `--log-file`: ログの保存先ファイル（任意）
- `-f`, `--input`: ホスト一覧ファイル（1 行 `IP,alias`、`#` はコメント）
- `-P`, `--panel-position`: サマリーパネル位置（`right|left|top|bottom|none`）
- `-m`, `--pause-mode`: 一時停止モード（`display|ping`）
- `-z`, `--timezone`: 表示用タイムゾーン（IANA 名、例: Asia/Tokyo）
- `-Z`, `--snapshot-timezone`: スナップショット名に使うタイムゾーン（`utc|display`）
- `-F`, `--flash-on-fail`: 失敗時に画面を反転して注目を促す
- `-B`, `--bell-on-fail`: 失敗時に端末ベルを鳴らす
- `-C`, `--color`: 色付き表示を有効化
- `-H`, `--ping-helper`: `ping_helper` バイナリのパス（デフォルト `./bin/ping_helper`）

#### インタラクティブ操作
- `n`: 表示名モードを切替（ip / rdns / alias）
- `v`: 表示切替（timeline / sparkline）
- `g`: ホスト選択を開いてフルスクリーン RTT グラフへ
- `o`: ソート方式を切替（failures / streak / latency / host）
- `f`: フィルタを切替（failures / latency / all）
- `a`: ASN 表示をトグル（表示領域が狭いと自動で非表示）
- `m`: サマリ表示内容を切替（rates / avg RTT / TTL / streak）
- `c`: 色付き表示をトグル
- `b`: 失敗時のベルをトグル
- `F`: サマリのフルスクリーン表示をトグル
- `w`: サマリーパネルの表示/非表示をトグル
- `W`: サマリーパネル位置を切替（left / right / top / bottom）
- `p`: 一時停止 / 再開（表示更新のみ）
- `P`: Dormant モードをトグル（ping 監視と表示更新の両方を停止）
- `s`: スナップショットを `paraping_snapshot_YYYYMMDD_HHMMSS.txt` として保存
- `←` / `→`: 履歴を1ページ単位で遡る / 進める（履歴は録り続けられ、ライブ表示に戻るまで画面は固定）
- `↑` / `↓`: ホスト一覧をスクロール（ホスト選択モードでないとき）。ホスト選択モードでは `n`（次） と `p`（前） を使用して選択を移動。選択が表示領域を超えると一覧がスクロールして選択を視界に保ちます
- `H`: ヘルプ表示（任意のキーで閉じる）
- `ESC`: フルスクリーングラフを終了
- `q`: 終了

#### タイムライン / スパークライン凡例
- `.` 成功
- `!` 遅延（RTT >= `--slow-threshold`）
- `x` 失敗 / タイムアウト
- 色付き表示が有効な場合: 白=成功、黄=遅延、赤=失敗

### 注意事項
- ICMP は特権操作です。Linux では capability ベースの `ping_helper` を利用することで通常ユーザ権限で実行できますが、補助バイナリが使えない環境では管理者権限が必要です。
- ASN の取得は `whois.cymru.com` を利用します。ネットワーク側でブロックされている場合、ASN 情報は取得できません。
- IPv6 アドレスは指定可能ですが、ping は失敗する可能性があります（ping_helper は IPv4 のみサポート）。ホスト名が IPv4 と IPv6 の両方に解決される場合、IPv4 が自動的に優先されます。
- 各ホストに対してワーカースレッドを 1 スレッド起動し、128 ホストの上限を設けています。上限を超えるとエラーで終了します。
- サマリーパネルを上／下に配置した場合、利用可能な空き行を使って表示を拡張します。
- サマリーパネルを上／下に配置した場合、端末幅が十分であれば全フィールドを表示します。

### パフォーマンスとスケーラビリティ

#### 現行アーキテクチャ
ParaPing は「1 ping = 1 ヘルパープロセス」のモデルを採用しています。これは以下を優先しています：
- **セキュリティ**: capability ベースのアクセス制御による最小権限の分離
- **シンプルさ**: 各ヘルパーは独立しており、共有状態がない
- **信頼性**: プロセス分離により、1 つの失敗した ping が他に影響しない

#### マルチホスト性能
現在のアーキテクチャは **中規模の同時ホスト監視**（最大 128 ホスト）に最適化されています：
- 各ホストは独立したワーカースレッドと ping プロセスを持つ
- 接続済みソケットと ICMP フィルタでプロセスごとのパケットファンアウトを低減
- 256KB 受信バッファで高 ICMP ボリューム下のパケットドロップを最小化

#### スケーラビリティに関する考慮事項
高ボリュームやバッチシナリオ（数百ホスト、サブ秒間隔）の場合：
- **プロセスオーバーヘッド**: プロセス生成により ping ごとに約 1-5ms の遅延が追加される
- **システム制限**: 各 ping が生ソケットを作成するため、ファイルディスクリプタ制限（`ulimit -n`）を確認
- **カーネル負荷**: 高い ping レートでは、ソケットバッファサイズや ICMP レート制限のチューニングが必要な場合がある

#### 将来の拡張
大規模展開向けの潜在的な最適化（現在は実装されていません）：
- **バッチモード**: 単一のヘルパープロセスで複数ホストを処理し、プロセス生成オーバーヘッドを削減
- **永続ワーカー**: 複数の ping リクエストを受け入れる長寿命のヘルパープロセス
- **共有ソケットプール**: 同一宛先の ping 用に再利用可能な生ソケット

**注:** 現在の 1 プロセス per ping モデルは意図的なもので、典型的な監視ワークロード（1-128 ホスト、1 秒間隔）に対して最適なセキュリティ/信頼性のトレードオフを提供します。異なるワークロードの場合は、上記の最適化を検討してください。

### 貢献
貢献歓迎です。開発ガイドライン、コード品質基準、プルリクエストの提出方法については [CONTRIBUTING.md](docs/CONTRIBUTING.md) を参照してください。

コードベースのモジュール化、モジュール所有権の境界、テスト構成、およびカバレッジレポートについては、[MODULARIZATION.md](docs/MODULARIZATION.md) を参照してください。

### 開発と検証

このセクションでは、プルリクエストを提出する前にローカルで変更を検証するための正確なコマンドを提供します。これらのコマンドは CI パイプライン設定と一致しており、PR をマージするためにはこれらをパスする必要があります。

#### プロジェクトのビルド

**ICMP ヘルパーバイナリをビルド:**
```bash
make build
```

**capabilities を設定（Linux のみ、sudo が必要）:**
```bash
sudo make setcap
```

**プラットフォーム注記:**
- **Linux**: `setcap` を使用して `ping_helper` バイナリに `cap_net_raw` を付与します。これは Python を root で実行するよりも安全です。
- **macOS/BSD**: `setcap` コマンドは利用できません。setuid ビット（`sudo chown root:wheel bin/ping_helper && sudo chmod u+s bin/ping_helper`）を使用できますが、セキュリティ上の理由で推奨されません。
- **セキュリティ**: `/usr/bin/python3` などの汎用インタプリタに `cap_net_raw` や他の capabilities を付与しないでください。特定の `ping_helper` バイナリのみに最小限の必要な権限を付与してください。

#### Linting

CI パイプラインは厳格な linting 基準を適用します。PR を提出する前に、これらのコマンドをローカルで実行してください：

**1. Flake8（厳格 - 必須パス）:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```
これは Python 構文エラーと未定義名をチェックします。ゼロエラーが必須です。

**2. Flake8（スタイル - 情報提供）:**
```bash
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```
これはスタイル違反（行長、複雑さ、PEP 8）を報告します。現在は情報提供のみですが、これらの問題を修正することが推奨されます。

**3. Pylint（コード品質 - 必須パス）:**
```bash
pylint . --fail-under=9.0
```
これはコード品質をチェックし、パスするには少なくとも 9.0/10 のスコアが必要です。

**4. Mypy（型チェック - 必須パス）:**
```bash
mypy
```
これは `pyproject.toml` の厳格な型チェック設定を適用します。

**すべての lint チェックを一度に実行:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics && \
pylint . --fail-under=9.0 && \
mypy
```

#### テスト

**カバレッジ付きですべてのテストを実行（CI と一致）:**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

**詳細分析用の HTML カバレッジレポートを生成:**
```bash
pytest tests/ -v --cov=. --cov-report=html
# レポートを表示: ブラウザで htmlcov/index.html を開く
```

**特定のテストファイルを実行:**
```bash
pytest tests/test_main.py -v
```

**モジュール別にカバレッジをチェック:**
```bash
pytest tests/ --cov=. --cov-report=term
```

**最小カバレッジ閾値でテストを実行:**
```bash
pytest tests/ --cov=. --cov-report=term --cov-fail-under=80
```

すべてのテストは PR を提出する前にパスする必要があります。新機能にはテストを追加してください。

#### PR 前検証チェックリスト

プルリクエストを開く前に、以下を確認してください：
1. ✅ プロジェクトをビルド: `make build`（Linux）またはヘルパーがコンパイルされることを確認
2. ✅ lint チェックを実行: 上記の 3 つの flake8/pylint コマンドすべてがパスする必要があります
3. ✅ mypy 型チェックを実行: `mypy`
4. ✅ テストを実行: `pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml`
5. ✅ 動作が変更された場合はドキュメントを更新
6. ✅ AI 支援を使用する場合は [LLM PR ポリシー](.github/workflows/copilot-instructions.md) に従ってください（ライセンスヘッダー、LLM 帰属、および PR 説明に検証コマンドを含める）

完全なコントリビューションガイドラインについては、[CONTRIBUTING.md](docs/CONTRIBUTING.md) を参照してください。

## 補足: ASN ルックアップメカニズム

Team Cymru の whois サービスを介した ASN ルックアップは、効率性と責任あるリソース使用を保証するために以下のメカニズムを使用します：

- **キャッシング**: 成功したルックアップはプログラムセッション中キャッシュされ、同一 IP への冗長なクエリを排除します
- **TTL によるリトライ**: 失敗したルックアップは 5 分後に再試行され、過剰なリクエストを防ぎます
- **スレッド管理**: 単一のワーカースレッドがリクエストを順次処理し、サービスの過負荷を回避します

## 補足: rDNS 結果のキャッシング動作

IP アドレスの逆引き DNS（rDNS）結果は最初の試行時にキャッシュされます：名前解決が成功した場合、ホスト名が保存され常に再利用されます；失敗した場合、None が保存され再利用されます。初回の解決が完了すると、自動的な再試行や再ルックアップは行われません。

### ライセンス
Apache License 2.0 — 詳細は [LICENSE](LICENSE) を参照してください。
