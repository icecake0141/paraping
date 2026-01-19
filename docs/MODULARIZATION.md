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

# ParaPing Modularization Guide

**Last Updated**: 2026-01-17
**Status**: Active
**Related**: Issue #94 (Follow-up to PR #93)

## Overview

This document provides guidance on the modularization of ParaPing, tracking the separation of concerns from the original monolithic `main.py` into dedicated modules with clear responsibilities and ownership boundaries.

## Current Module Structure

### Completed Extractions

| Module | Lines | Coverage | Status | Responsibilities |
|--------|-------|----------|--------|------------------|
| `ui_render.py` | 653 | 82% | ✅ Complete | UI rendering, ANSI utilities, layout computation, timeline/sparkline building, terminal utilities, graph rendering, formatting functions |
| `stats.py` | 93 | 95% | ✅ Complete | Statistics computation, fail streak tracking, TTL/RTT extraction, summary data building, streak labels |
| `network_asn.py` | 57 | 98% | ✅ Complete | ASN resolution via Team Cymru whois, ASN worker threads, retry logic |
| `ping_wrapper.py` | 79 | 78% | ✅ Complete | Wrapper for ping_helper binary, result parsing, error handling |

### Modules Awaiting Integration/Usage

| Module | Lines | Coverage | Status | Responsibilities |
|--------|-------|----------|--------|------------------|
| `network_rdns.py` | 19 | 0% | ⚠️ Created, not used | Reverse DNS resolution, rDNS worker threads |
| `input_keys.py` | 42 | 0% | ⚠️ Created, not used | Keyboard input handling, escape sequence parsing, arrow key detection |
| `history.py` | 55 | 0% | ⚠️ Created, not used | History buffer management, snapshot creation, time navigation |

### Main Application

| Module | Lines | Coverage | Status | Responsibilities |
|--------|-------|----------|--------|------------------|
| `main.py` | 677 | 58% | 🔄 In progress | Application entry point, main event loop, host management, state coordination, CLI argument parsing |

**Note**: Modules with 0% coverage exist but are not yet integrated into the main application. These represent extraction work in progress.

## Next Extraction Targets

### Priority 1: Complete Integration of Existing Modules

The following modules have been created but are not yet actively used by `main.py`:

1. **`network_rdns.py`** (19 lines, 0% coverage)
   - **Status**: Module exists with `resolve_rdns()` and `rdns_worker()` functions
   - **Action Required**: Integrate into main.py to replace inline rDNS logic
   - **Expected Impact**: Reduce main.py by ~15-20 lines, improve testability
   - **Test Location**: Create `tests/test_network_rdns.py` following pattern in `tests/test_network_asn.py`

2. **`input_keys.py`** (42 lines, 0% coverage)
   - **Status**: Module exists with `read_key()` and `parse_escape_sequence()` functions
   - **Action Required**: Integrate into main.py to replace inline keyboard handling
   - **Expected Impact**: Reduce main.py by ~30-40 lines, improve testability
   - **Test Location**: Create `tests/test_input_keys.py` for arrow key and escape sequence parsing

3. **`history.py`** (55 lines, 0% coverage)
   - **Status**: Module exists with history buffer and navigation logic
   - **Action Required**: Integrate into main.py to replace inline history management
   - **Expected Impact**: Reduce main.py by ~40-50 lines, improve testability
   - **Test Location**: Create `tests/test_history.py` for buffer operations and navigation

### Priority 2: Additional Extractions from main.py

After integrating existing modules, consider these additional extractions:

4. **Display Names and Host Information** (~50-80 lines)
   - **Extraction Target**: Functions like `format_display_name()`, `build_display_names()`, `build_host_infos()`
   - **Suggested Module**: `host_display.py` or merge into `ui_render.py`
   - **Rationale**: Separates host display logic from core application flow
   - **Test Location**: `tests/test_host_display.py` or extend `tests/test_main.py`

5. **Snapshot and Export** (~30-50 lines)
   - **Extraction Target**: Snapshot creation, file writing, timestamp formatting for snapshots
   - **Suggested Module**: `snapshot.py` or `export.py`
   - **Rationale**: Isolates file I/O and snapshot logic
   - **Test Location**: `tests/test_snapshot.py`

6. **Application State Management** (~60-100 lines)
   - **Extraction Target**: State dictionaries, state transitions, configuration
   - **Suggested Module**: `app_state.py` or `config.py`
   - **Rationale**: Centralizes state management, reduces main.py complexity
   - **Test Location**: `tests/test_app_state.py`

## Module Ownership and Responsibilities

### Principle: Single Responsibility

Each module should have one clear area of responsibility:

- **UI Modules** (`ui_render.py`): Rendering, formatting, layout - no network or state logic
- **Network Modules** (`network_*.py`): Network operations only - no UI or display logic
- **Utility Modules** (`stats.py`, `input_keys.py`): Pure functions with no side effects where possible
- **Application Module** (`main.py`): Coordinates all modules, manages lifecycle, handles main event loop

### Dependency Flow

```
main.py
  ├── ui_render.py (depends on stats.py)
  ├── stats.py (pure utility functions)
  ├── network_asn.py (depends on network utilities)
  ├── network_rdns.py (depends on network utilities)
  ├── input_keys.py (depends on system I/O)
  ├── history.py (depends on data structures)
  └── ping_wrapper.py (depends on subprocess)
```

**Rule**: Modules should not have circular dependencies. Lower-level utilities (stats, input_keys) should not import from higher-level modules (ui_render, main).

## Test Organization

### Current Test Structure

```
tests/
  ├── test_main.py           # Main application, UI rendering, integration tests
  ├── test_network_asn.py    # ASN resolution tests
  ├── test_ping_wrapper.py   # Ping wrapper tests
  └── test_ping_helper_contract.py  # C binary contract tests
```

### Recommended Test Organization

As modules are extracted or integrated, tests should follow this pattern:

| Module | Test File | Test Focus |
|--------|-----------|------------|
| `main.py` | `tests/test_main.py` | CLI parsing, integration tests, main loop behavior |
| `ui_render.py` | `tests/test_ui_render.py` or keep in `test_main.py` | Rendering functions, layout computation, formatting |
| `stats.py` | `tests/test_stats.py` or keep in `test_main.py` | Statistics computation, streak tracking |
| `network_asn.py` | `tests/test_network_asn.py` | ✅ Already exists |
| `network_rdns.py` | `tests/test_network_rdns.py` | ⚠️ **Need to create** |
| `input_keys.py` | `tests/test_input_keys.py` | ⚠️ **Need to create** |
| `history.py` | `tests/test_history.py` | ⚠️ **Need to create** |
| `ping_wrapper.py` | `tests/test_ping_wrapper.py` | ✅ Already exists |

### Test Ownership Guidelines

1. **Module-Specific Tests**: When creating a new module, create a corresponding test file (e.g., `module.py` → `tests/test_module.py`)

2. **Test Migration**: When extracting code from `main.py`:
   - Move relevant tests from `test_main.py` to the new module's test file
   - Keep integration tests that span multiple modules in `test_main.py`
   - Update test names to reflect new module ownership

3. **Coverage Requirements**:
   - Aim for >90% coverage for utility modules (stats, input_keys, network_*)
   - Aim for >80% coverage for UI modules (ui_render)
   - Aim for >60% coverage for main application (main.py)
   - Integration tests in main.py may have lower individual coverage but should cover critical paths

4. **Test Naming Convention**:
   ```python
   # tests/test_<module_name>.py
   class Test<FeatureName>:
       def test_<specific_behavior>(self):
           ...
   ```

## Coverage Reporting

### Current Coverage Status (as of 2026-01-17)

**Overall Coverage**: 80% (2953 statements, 598 missing)

**By Module**:
- `ui_render.py`: 82% (653 statements, 115 missing)
- `stats.py`: 95% (93 statements, 5 missing)
- `network_asn.py`: 98% (57 statements, 1 missing)
- `ping_wrapper.py`: 78% (79 statements, 17 missing)
- `main.py`: 58% (677 statements, 281 missing)
- `network_rdns.py`: 0% (19 statements, 19 missing) - ⚠️ Not integrated
- `input_keys.py`: 0% (42 statements, 42 missing) - ⚠️ Not integrated
- `history.py`: 0% (55 statements, 55 missing) - ⚠️ Not integrated

### Local Coverage Commands

Run these commands locally to check coverage:

```bash
# Install development dependencies (includes pytest-cov)
pip install -r requirements-dev.txt

# Run tests with coverage report
pytest tests/ -v --cov=. --cov-report=term-missing

# Generate HTML coverage report for detailed analysis
pytest tests/ -v --cov=. --cov-report=html
# View report: open htmlcov/index.html in browser

# Run coverage for a specific module
pytest tests/ -v --cov=ui_render --cov-report=term-missing

# Check coverage with minimum threshold (fails if below 80%)
pytest tests/ -v --cov=. --cov-report=term --cov-fail-under=80
```

### CI Coverage Reporting

The CI pipeline (`.github/workflows/ci.yml`) already includes coverage reporting:

```yaml
- name: Run tests with pytest
  run: |
    pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml

- name: Upload coverage reports
  if: matrix.python-version == '3.10'
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage.xml
    fail_ci_if_error: false
  continue-on-error: true
```

**Current CI Capabilities**:
- ✅ Coverage runs on every PR and push to main/master
- ✅ Coverage uploaded to Codecov (if token configured)
- ✅ Coverage report shown in CI logs
- ⚠️ No coverage delta/comparison in PR comments (requires Codecov token)

### Tracking Coverage Over Time

**Option 1: Codecov (Recommended)**
1. Set up Codecov integration with GitHub repository
2. Add `CODECOV_TOKEN` secret to repository
3. Codecov will automatically comment on PRs with coverage deltas
4. View historical coverage trends at codecov.io

**Option 2: Manual Tracking**
1. Before making changes: `pytest tests/ --cov=. --cov-report=term > coverage_before.txt`
2. After making changes: `pytest tests/ --cov=. --cov-report=term > coverage_after.txt`
3. Compare the two reports to identify coverage changes
4. Include coverage delta in PR description

**Option 3: Local Coverage Comparison (Using Built-in Script)**
```bash
# Generate coverage data before changes
pytest tests/ --cov=. --cov-report=term > coverage_baseline.txt

# Make your changes and run tests
pytest tests/ --cov=. --cov-report=term > coverage_current.txt

# Compare coverage using the included script
python scripts/coverage_summary.py coverage_baseline.txt coverage_current.txt --compare
```

The `scripts/coverage_summary.py` script provides:
- Formatted coverage tables for easy reading
- Side-by-side baseline vs current comparison
- Delta calculation showing improvements or regressions
- Clear visual indicators (✅/⚠️) for coverage changes

### Coverage Goals by Module Type

| Module Type | Coverage Goal | Rationale |
|-------------|---------------|-----------|
| **Utility Modules** (stats, input_keys) | ≥ 90% | Pure functions, easy to test |
| **Network Modules** (network_asn, network_rdns) | ≥ 85% | Mostly testable with mocking |
| **UI Modules** (ui_render) | ≥ 80% | Some branches hard to test |
| **Integration** (ping_wrapper) | ≥ 75% | Depends on external binary |
| **Main Application** (main.py) | ≥ 60% | Contains event loop, hard to test all paths |
| **Overall Project** | ≥ 80% | Balanced quality bar |

## Migration Checklist for New Extractions

When extracting code from `main.py` into a new module, follow this checklist:

- [ ] **Create New Module**
  - [ ] Add Apache 2.0 license header with SPDX identifier
  - [ ] Add LLM attribution comment
  - [ ] Add module docstring describing responsibilities
  - [ ] Ensure no circular dependencies

- [ ] **Move Functions**
  - [ ] Move functions to new module
  - [ ] Update imports in main.py
  - [ ] Update any other files importing the moved functions
  - [ ] Verify no broken imports

- [ ] **Create/Update Tests**
  - [ ] Create `tests/test_<module>.py` if needed
  - [ ] Move relevant tests from test_main.py
  - [ ] Add new tests for edge cases
  - [ ] Verify coverage ≥ target for module type

- [ ] **Update Documentation**
  - [ ] Update this MODULARIZATION.md with new module
  - [ ] Update README.md if user-facing changes
  - [ ] Add docstrings to public functions
  - [ ] Update CODE_REVIEW.md if architectural changes

- [ ] **Validate Changes**
  - [ ] Run full test suite: `pytest tests/ -v`
  - [ ] Run coverage: `pytest tests/ --cov=. --cov-report=term-missing`
  - [ ] Run linters: `flake8 .` and `pylint .`
  - [ ] Manual smoke test of CLI functionality

## Future Considerations

### Long-Term Architecture

As ParaPing continues to grow, consider:

1. **Package Structure**: Move modules into a `paraping/` package directory
   ```
   paraping/
     __init__.py
     main.py
     ui/
       __init__.py
       render.py
       layout.py
     network/
       __init__.py
       asn.py
       rdns.py
       ping.py
     utils/
       stats.py
       input.py
   ```

2. **Plugin System**: Allow external modules to add features (e.g., custom exporters, data sources)

3. **Configuration File**: Support `.parapirc` or similar for default options

4. **API Stability**: As modules mature, define public APIs and deprecation policies

### Performance Considerations

When modularizing, be mindful of:
- **Import time**: Don't import heavy modules unless needed
- **Function call overhead**: Keep hot paths (ping loop) optimized
- **Memory usage**: Avoid duplicating large data structures across modules

## Questions or Suggestions?

For questions about modularization strategy or to suggest improvements to this guide, please:
1. Open an issue on GitHub
2. Reference this document in your issue
3. Tag with `refactor` or `architecture` label

---

**Document History**:
- 2026-01-17: Initial version created (Issue #94, follow-up to PR #93)
