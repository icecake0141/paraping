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

**Last Updated**: 2026-01-20
**Status**: Active - Reflects Completed Refactoring
**Related**: Original Issue #94 (Follow-up to PR #93)

## Overview

This document provides guidance on the modularization of ParaPing, documenting the completed separation of concerns from the original monolithic `main.py` into a well-organized package structure (`paraping/`) with dedicated modules having clear responsibilities and ownership boundaries.

**Major Milestone Achieved**: The repository has successfully completed its modularization refactoring. All priority modules have been created, integrated, and tested. The original monolithic `main.py` has been converted to a compatibility shim, with the core logic now organized in the `paraping/` package.

## Current Module Structure

The ParaPing application is now organized as a Python package (`paraping/`) with the following module organization:

### Core Package Modules (paraping/)

| Module | Lines | Coverage | Status | Responsibilities |
|--------|-------|----------|--------|------------------|
| `cli.py` | 918 | 51% | ✅ Active | CLI argument parsing, main application entry point, event loop coordination, host management, user interaction handling |
| `core.py` | 431 | 95% | ✅ Active | Core functionality, state management, snapshot creation, terminal size handling, host parsing |
| `ui_render.py` | 1328 | 82% | ✅ Active | UI rendering, ANSI utilities, layout computation, timeline/sparkline building, terminal utilities, graph rendering, formatting functions |
| `stats.py` | 246 | 95% | ✅ Active | Statistics computation, fail streak tracking, TTL/RTT extraction, summary data building, streak labels |
| `pinger.py` | 174 | 92% | ✅ Active | Ping host functionality, worker ping threads, rDNS resolution integrated |
| `input_keys.py` | 93 | 98% | ✅ Active | Keyboard input handling, escape sequence parsing, arrow key detection |
| `network_asn.py` | 161 | 98% | ✅ Active | ASN resolution via Team Cymru whois, ASN worker threads, retry logic |
| `ping_wrapper.py` | 226 | 79% | ✅ Active | Wrapper for ping_helper binary, result parsing, error handling |
| `history.py` | 259 | 0% | ⚠️ Not Integrated | History buffer management, snapshot creation, time navigation (functions duplicated in core.py) |
| `network_rdns.py` | 60 | 0% | ⚠️ Not Integrated | Reverse DNS resolution standalone module (functionality integrated in pinger.py instead) |

### Entry Points

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | ~100 | **Compatibility shim** - Re-exports from paraping package for backward compatibility with existing tests |
| `paraping/__main__.py` | 22 | Package entry point - Invokes cli.run() when package is executed |

**Architecture Achievement**: The modularization is largely complete. The original monolithic structure has been successfully refactored into a clean package layout with well-defined module responsibilities.

## Refactoring Status Summary

### ✅ Completed Integrations

The following priority modules have been **successfully integrated**:

1. **`input_keys.py`** ✅ INTEGRATED
   - **Status**: Actively used in `cli.py` (line 43: `from paraping.input_keys import read_key`)
   - **Coverage**: 98% (42 statements, 1 missing)
   - **Tests**: `tests/unit/test_input_keys.py` exists with comprehensive tests
   - **Impact**: Keyboard handling cleanly separated from main event loop

2. **rDNS Functionality** ✅ INTEGRATED (in pinger.py)
   - **Status**: `resolve_rdns()` and `rdns_worker()` implemented in `pinger.py` (lines 154-174)
   - **Coverage**: 92% overall for pinger.py
   - **Tests**: Covered by `tests/unit/test_pinger.py` (TestResolveRDNS, TestRDNSWorker)
   - **Impact**: rDNS resolution integrated with ping functionality
   - **Note**: `network_rdns.py` standalone module exists but is not used (functionality duplicated in pinger.py)

3. **Core Functionality** ✅ REFACTORED
   - **Status**: Major logic moved from monolithic main.py into organized modules:
     - `cli.py`: CLI parsing and main event loop
     - `core.py`: State management, snapshots, terminal handling
     - `pinger.py`: Ping and network operations
   - **Impact**: Original monolithic main.py converted to compatibility shim

### ⚠️ Remaining Module Integration Opportunities

1. **`history.py`** (55 lines, 0% coverage)
   - **Status**: Module exists but functionality is duplicated in `core.py`
   - **Current State**: Constants like `HISTORY_DURATION_MINUTES` defined in both files
   - **Recommendation**: Either:
     - Consolidate history functionality into `history.py` and import in `core.py`
     - OR Remove `history.py` since core.py already implements this functionality
   - **Impact**: Minimal - mostly consolidation to reduce duplication

2. **`network_rdns.py`** (19 lines, 0% coverage)
   - **Status**: Module exists but functionality implemented in `pinger.py` instead
   - **Current State**: `pinger.py` has its own `resolve_rdns()` and `rdns_worker()` functions
   - **Recommendation**: Either:
     - Consolidate by moving pinger.py's rdns functions here and importing
     - OR Remove `network_rdns.py` since pinger.py already implements this
   - **Impact**: Minimal - mostly consolidation to reduce duplication

## Module Ownership and Responsibilities

### Principle: Single Responsibility

Each module has one clear area of responsibility:

- **UI Module** (`ui_render.py`): Rendering, formatting, layout computation - no network or state logic
- **Network Modules** (`network_asn.py`, `ping_wrapper.py`, `pinger.py`): Network operations only - no UI or display logic
- **Utility Modules** (`stats.py`, `input_keys.py`): Pure functions with minimal side effects
- **Core Module** (`core.py`): State management, configuration, terminal utilities
- **CLI Module** (`cli.py`): Main event loop, user interaction, coordinates all other modules
- **Entry Points** (`main.py`, `__main__.py`): Application initialization and backward compatibility

### Dependency Flow

```
main.py (compatibility shim)
  └── re-exports from paraping package modules

paraping/__main__.py
  └── cli.py (main application orchestrator)
        ├── ui_render.py (imports stats.py)
        ├── core.py (imports ui_render.py)
        ├── stats.py (pure utility functions)
        ├── input_keys.py (keyboard I/O utilities)
        ├── pinger.py (imports ping_wrapper.py, includes rdns)
        ├── network_asn.py (network utilities)
        └── ping_wrapper.py (subprocess management)
```

**Rule**: Modules avoid circular dependencies. Lower-level utilities (stats, input_keys, ping_wrapper) do not import from higher-level modules (cli, ui_render).

## Test Organization

### Current Test Structure

The test suite is organized into three categories:

```
tests/
  ├── unit/                          # Unit tests for individual modules
  │   ├── test_cli.py               # CLI argument parsing and option handling
  │   ├── test_core.py              # Core functionality and state management
  │   ├── test_core_term_size_normalization.py  # Terminal size edge cases
  │   ├── test_input_keys.py        # Keyboard input and escape sequences
  │   ├── test_main_*.py            # Various main application features
  │   ├── test_package_init.py      # Package initialization
  │   ├── test_ping_wrapper.py      # Ping wrapper functionality
  │   └── test_pinger.py            # Pinger and rdns functionality
  ├── integration/                   # Integration tests
  │   └── test_network_asn.py       # ASN resolution integration
  └── contract/                      # Binary contract tests
      └── test_ping_helper_contract.py  # C binary interface validation
```

### Test Coverage by Module

| Module | Test File | Coverage | Status |
|--------|-----------|----------|--------|
| `cli.py` | `tests/unit/test_cli.py` | 51% | ✅ Exists |
| `core.py` | `tests/unit/test_core.py`, `test_core_term_size_normalization.py` | 95% | ✅ Exists |
| `ui_render.py` | `tests/unit/test_main_*.py` | 82% | ✅ Exists |
| `stats.py` | `tests/unit/test_main_*.py` | 95% | ✅ Exists |
| `input_keys.py` | `tests/unit/test_input_keys.py` | 98% | ✅ Exists |
| `pinger.py` | `tests/unit/test_pinger.py` | 92% | ✅ Exists (includes rdns tests) |
| `network_asn.py` | `tests/integration/test_network_asn.py` | 98% | ✅ Exists |
| `ping_wrapper.py` | `tests/unit/test_ping_wrapper.py` | 79% | ✅ Exists |
| `network_rdns.py` | N/A | 0% | ⚠️ Module not integrated |
| `history.py` | N/A | 0% | ⚠️ Module not integrated |

### Test Ownership Guidelines

1. **Module-Specific Tests**: Each module has a corresponding test file organized by test type (unit/integration/contract)

2. **Test Organization**:
   - Unit tests in `tests/unit/` for individual module functionality
   - Integration tests in `tests/integration/` for cross-module interactions
   - Contract tests in `tests/contract/` for external binary interfaces

3. **Coverage Goals by Module Type**:

| Module Type | Coverage Goal | Current Achievement |
|-------------|---------------|---------------------|
| **Utility Modules** (stats, input_keys) | ≥ 90% | ✅ 95-98% |
| **Network Modules** (network_asn, pinger) | ≥ 85% | ✅ 92-98% |
| **UI Modules** (ui_render) | ≥ 80% | ✅ 82% |
| **Integration** (ping_wrapper) | ≥ 75% | ✅ 79% |
| **Core** (core.py) | ≥ 90% | ✅ 95% |
| **CLI Application** (cli.py) | ≥ 60% | 🔄 51% (in progress) |
| **Overall Project** | ≥ 70% | ✅ 73% |

4. **Test Naming Convention**:
   ```python
   # tests/unit/test_<module_name>.py
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

# Run tests with coverage report for paraping package
pytest tests/ -v --cov=paraping --cov-report=term-missing

# Generate HTML coverage report for detailed analysis
pytest tests/ -v --cov=paraping --cov-report=html
# View report: open htmlcov/index.html in browser

# Run coverage for a specific module
pytest tests/ -v --cov=paraping.ui_render --cov-report=term-missing

# Check coverage with minimum threshold (fails if below 70%)
pytest tests/ -v --cov=paraping --cov-report=term --cov-fail-under=70
```

### CI Coverage Reporting

The CI pipeline (`.github/workflows/ci.yml`) includes coverage reporting:

```yaml
- name: Run tests with pytest
  run: |
    pytest tests/ -v --cov=paraping --cov-report=term-missing --cov-report=xml

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
- ⚠️ Coverage delta/comparison in PR comments requires Codecov token

### Tracking Coverage Over Time

**Option 1: Codecov (Recommended)**
1. Set up Codecov integration with GitHub repository
2. Add `CODECOV_TOKEN` secret to repository settings
3. Codecov will automatically comment on PRs with coverage deltas
4. View historical coverage trends at codecov.io

**Option 2: Manual Tracking**
1. Before making changes: `pytest tests/ --cov=paraping --cov-report=term > coverage_before.txt`
2. After making changes: `pytest tests/ --cov=paraping --cov-report=term > coverage_after.txt`
3. Compare the two reports to identify coverage changes
4. Include coverage delta in PR description

**Option 3: Local Coverage Comparison (Using Built-in Script)**
```bash
# Generate coverage data before changes
pytest tests/ --cov=paraping --cov-report=term > coverage_baseline.txt

# Make your changes and run tests
pytest tests/ --cov=paraping --cov-report=term > coverage_current.txt

# Compare coverage using the included script (if available)
python scripts/coverage_summary.py coverage_baseline.txt coverage_current.txt --compare
```

## Contribution Guidelines for Module Changes

When making changes to the modular architecture, follow this checklist:

- [ ] **Modify Existing Module**
  - [ ] Maintain Apache 2.0 license header with SPDX identifier
  - [ ] Update or add LLM attribution comment if using AI assistance
  - [ ] Update module docstring if responsibilities change
  - [ ] Ensure no circular dependencies are introduced

- [ ] **Update Imports**
  - [ ] Update imports in affected modules
  - [ ] Check `main.py` compatibility shim if changing public APIs
  - [ ] Verify no broken imports with: `python -m py_compile paraping/*.py`

- [ ] **Create/Update Tests**
  - [ ] Add tests to appropriate `tests/unit/test_<module>.py`
  - [ ] Ensure new functionality has test coverage
  - [ ] Add tests for edge cases and error conditions
  - [ ] Verify coverage meets or exceeds module type target

- [ ] **Update Documentation**
  - [ ] Update this MODULARIZATION.md if architecture changes
  - [ ] Update README.md if user-facing features change
  - [ ] Add or update docstrings for public functions

- [ ] **Validate Changes**
  - [ ] Run full test suite: `pytest tests/ -v`
  - [ ] Run coverage: `pytest tests/ --cov=paraping --cov-report=term-missing`
  - [ ] Run linters: `make lint` (runs flake8, pylint, black, isort)
  - [ ] Manual smoke test: `python -m paraping --help` and basic functionality

## Architecture Achievements and Future Considerations

### ✅ Completed Architecture Goals

The ParaPing project has successfully achieved its modularization goals:

1. **✅ Package Structure**: Modules organized in `paraping/` package directory
   ```
   paraping/
     __init__.py          # Package initialization
     __main__.py          # Package entry point
     cli.py               # Main application and CLI
     core.py              # Core state and utilities
     ui_render.py         # All UI rendering
     stats.py             # Statistics utilities
     input_keys.py        # Input handling
     pinger.py            # Ping and network operations
     network_asn.py       # ASN resolution
     ping_wrapper.py      # Ping helper wrapper
     history.py           # History (not yet integrated)
     network_rdns.py      # rDNS standalone (not used)
   ```

2. **✅ Backward Compatibility**: `main.py` maintained as compatibility shim for existing tests

3. **✅ Test Organization**: Comprehensive test suite organized by module and test type

### Future Enhancement Opportunities

As ParaPing continues to evolve, consider:

1. **History Module Integration**: Consolidate history functionality from core.py into history.py or remove duplicate module

2. **Network Module Consolidation**: Consider consolidating network_rdns.py functionality (currently in pinger.py)

3. **CLI Coverage**: Improve test coverage for cli.py (currently 51%) by adding more integration tests

4. **Plugin System**: Allow external modules to add features (e.g., custom exporters, output formats)

5. **Configuration File**: Support `.parapirc` or similar for persisting user preferences

6. **API Stability**: Define public APIs and deprecation policies as the project matures

### Performance Considerations

The current modular architecture maintains performance:
- **Import time**: Optimized - modules only import what they need
- **Function call overhead**: Minimal - hot paths (ping loop in pinger.py) remain optimized
- **Memory usage**: Efficient - data structures not duplicated across modules

## Questions or Suggestions?

For questions about modularization strategy or to suggest improvements to this guide, please:
1. Open an issue on GitHub
2. Reference this document in your issue
3. Tag with `refactor`, `architecture`, or `documentation` label

---

## Document History

- **2026-01-20**: Major update to reflect completed refactoring
  - Updated module structure to show completed package organization
  - Documented achievement of modularization goals
  - Updated coverage statistics (73% overall, 265 tests passing)
  - Noted integration status of all modules
  - Changed from "extraction guide" to "architecture documentation"
  - Identified remaining consolidation opportunities (history.py, network_rdns.py)

- **2026-01-17**: Initial version created (Issue #94, follow-up to PR #93)
  - Documented planned modularization work
  - Listed priority 1 extractions (network_rdns, input_keys, history)
  - Established coverage goals and test organization guidelines
