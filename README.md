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

> 日本語版 README: [README.ja.md](docs/README.ja.md)

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

ParaPing supports multiple installation methods to suit different workflows and user preferences. Choose the method that works best for you.

### Quick Start (Recommended)

For most users, we recommend the **user-level installation** which installs to `~/.local` and doesn't require sudo:

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Install for current user (no sudo needed)
make install-user

# Build the privileged ICMP helper (Linux only)
make build
sudo make setcap

# Run paraping
paraping --help
```

**PATH Configuration:** If `paraping` command is not found, add `~/.local/bin` to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Installation Methods Comparison

| Method | Use Case | Requires sudo | PATH | Dependency Management |
|--------|----------|--------------|------|----------------------|
| `make install-user` | **Recommended** for most users | No (except setcap) | `~/.local/bin` | pip handles it |
| `make install-system` | System-wide, all users | Yes | `/usr/local/bin` | pip handles it |
| `make install-wrapper` | Minimal, no pip install | Yes | `/usr/local/bin` | Manual PYTHONPATH |
| `pipx install .` | Isolated environment | No | `~/.local/bin` | pipx handles it |
| `pip install -e .` | Development/editable | No | Current venv | pip handles it |

### Detailed Installation Instructions

#### 1. User-Level Installation (Recommended)

Installs to `~/.local` for the current user only. No sudo needed, clean uninstall, doesn't affect system Python.

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

**Note:** ParaPing has no external Python dependencies (all stdlib), so `requirements.txt` is minimal.

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
- IPv6 addresses can be specified but pinging will likely fail (ping_helper only supports IPv4). When hostnames resolve to both IPv4 and IPv6, IPv4 is automatically preferred.
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
Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines, code quality standards, and how to submit pull requests.

For information about the codebase modularization, module ownership boundaries, test organization, and coverage reporting, see [MODULARIZATION.md](docs/MODULARIZATION.md).

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

For complete contribution guidelines, see [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License
Apache License 2.0. See [LICENSE](LICENSE).
