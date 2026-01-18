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

ParaPing is an interactive, terminal-based ICMP monitor that pings many hosts in parallel and visualizes results as a live timeline or sparkline. It provides operator controls for sorting, filtering, pausing, snapshots, and per-host RTT inspection to aid rapid network triage.

> 日本語版 README: [README.ja.md](README.ja.md)

## Features
- Concurrent ICMP ping to multiple hosts (capability-based helper binary).
- Live timeline or sparkline visualization with success/slow/fail markers.
- Animated activity indicator (Knight Rider-style) while pings are running.
- Summary panel with host statistics, RTT jitter/standard deviation, aggregate counts, and TTL display.
- Boxed panel layout for ping results, summaries, and the status line.
- Summary host ordering matches the current ping result sort order.
- Sort and filter results by failures, streaks, latency, or host name.
- Toggle display name mode: IP, reverse DNS, or alias.
- Optional ASN display (fetched from Team Cymru) with auto-retry.
- Optional colored output for success/slow/fail states.
- Pause modes: freeze display only or pause ping + display.
- Snapshot export to a timestamped text file.
- Fullscreen ASCII RTT graph per host with axis labels and scale, including X-axis seconds-ago labels (selectable via TUI).
- Configurable timezone for timestamps and snapshot naming.
- Input file support for host lists (one per line in `IP,alias` format; comments allowed).

## Requirements
- Python 3.9 or newer.
- The `ping_helper` binary built with `cap_net_raw` (Linux) to run without `sudo`.
- Root/administrator privileges if you cannot use the helper (non-Linux platforms).
- Network access for optional ASN lookups.
- IPv4-only support (hosts must resolve to IPv4 addresses).

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
# Build the helper binary
make build

# Set capabilities (requires sudo)
sudo make setcap

# Test the helper
python3 ping_wrapper.py google.com
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

**Note for macOS/BSD users:** The `setcap` command is Linux-specific and not available on macOS or BSD systems. On these platforms, you would need to use the setuid bit instead (e.g., `sudo chown root:wheel ping_helper && sudo chmod u+s ping_helper`), but this is less secure and not recommended. Follow platform best practices for granting minimal privilege.

**Security Note:** Never grant `cap_net_raw` or any capabilities to `/usr/bin/python3` or other general-purpose interpreters. Only grant the minimal required privilege to the specific `ping_helper` binary.

## Installation

### Standard Installation (Editable Mode)

Install ParaPing in editable mode for development or local use:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install the package in editable mode
pip install -e .

# Build the privileged ICMP helper (Linux only)
make build
sudo make setcap

# Now you can run 'paraping' from anywhere
paraping --help
```

### Legacy Installation (Without Package Installation)

If you prefer to run ParaPing without installing it as a package:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping
python -m pip install -r requirements.txt

# Build the privileged ICMP helper (Linux only)
make build
sudo make setcap

# Run directly from the repository
./main.py --help
```

**Note:** When using `pip install -e .`, the `paraping` command becomes available system-wide (in your current Python environment). The native `ping_helper` binary must still be built separately using `make build` and configured with capabilities using `sudo make setcap` (Linux only).

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
- `-i`, `--interval`: Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0).
- `-s`, `--slow-threshold`: RTT threshold (seconds) to mark a ping as slow (default: 0.5).
- `-v`, `--verbose`: Print raw per-packet output (non-UI).
- `-f`, `--input`: Read hosts from a file (one per line; format: `IP,alias`; `#` comments supported).
- `-P`, `--panel-position`: Summary panel position (`right|left|top|bottom|none`).
- `-m`, `--pause-mode`: Pause behavior (`display|ping`).
- `-z`, `--timezone`: IANA timezone name for on-screen timestamps.
- `-Z`, `--snapshot-timezone`: Timezone for snapshot filenames (`utc|display`).
- `-F`, `--flash-on-fail`: Flash screen (invert colors) when a ping fails to draw attention.
- `-B`, `--bell-on-fail`: Ring terminal bell when a ping fails to draw attention.
- `-C`, `--color`: Enable colored output (blue=success, yellow=slow, red=fail).
- `-H`, `--ping-helper`: Path to the `ping_helper` binary (default: `./ping_helper`).

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
- `p`: Pause/resume (display only or ping + display).
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
- When `--color` is enabled: white=success, yellow=slow, red=failure.

## Notes
- ICMP requires elevated privileges (run with `sudo` or Administrator on Windows) unless using the capability-based helper on Linux.
- ASN lookups use `whois.cymru.com`; blocked networks will show blank ASN values.
- IPv6 is not supported; use IPv4 addresses or hostnames that resolve to IPv4.
- The monitor starts one worker thread per host and enforces a hard limit of 128 hosts. It exits with an error if exceeded.
- When the summary panel is positioned at the top/bottom, it expands to use available empty rows.
- When the summary panel is positioned at the top/bottom, it shows all summary fields if the width allows.

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
Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, code quality standards, and how to submit pull requests.

For information about the codebase modularization, module ownership boundaries, test organization, and coverage reporting, see [MODULARIZATION.md](MODULARIZATION.md).

## Development & Validation

This section provides exact commands for validating your changes locally before submitting a pull request. These commands match the CI pipeline configuration and must pass for PRs to be merged.

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
- **macOS/BSD**: The `setcap` command is not available. You can use the setuid bit (`sudo chown root:wheel ping_helper && sudo chmod u+s ping_helper`), but this is not recommended for security reasons.
- **Security**: Never grant `cap_net_raw` or any capabilities to general-purpose interpreters like `/usr/bin/python3`. Only grant the minimal required privilege to the specific `ping_helper` binary.

### Linting

The CI pipeline enforces strict linting standards. Run these commands locally before submitting a PR:

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

**Run all lint checks at once:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics && \
pylint . --fail-under=9.0
```

### Testing

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

### Pre-PR Validation Checklist

Before opening a pull request, ensure you:
1. ✅ Build the project: `make build` (Linux) or verify the helper compiles
2. ✅ Run lint checks: all three flake8/pylint commands above must pass
3. ✅ Run tests: `pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml`
4. ✅ Update documentation if behavior changed
5. ✅ Follow the [LLM PR policy](.github/workflows/copilot-instructions.md) if using AI assistance (include license headers, LLM attribution, and validation commands in your PR description)

For complete contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License
Apache License 2.0. See [LICENSE](LICENSE).
