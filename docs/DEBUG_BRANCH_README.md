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

# Debugging Branch: Arrow Key Input Troubleshooting

**Branch**: `copilot/add-debugging-for-key-input`

## Purpose

This branch implements temporary debugging features to diagnose and troubleshoot arrow key non-responsiveness in ParaPing's input UI.

## Quick Start

```bash
# Run ParaPing with debug logging enabled
python3 main.py --debug-keys localhost

# Or with a host file
python3 main.py --debug-keys -f hosts.txt

# Follow the on-screen prompts to test arrow keys
# Press q to exit
# Review the generated log file: paraping_debug_keys.log
```

## Features Added

### 1. Debug Logging Module (`paraping/debug_logger.py`)
- Captures all keyboard input events in structured JSON format
- Logs raw bytes, timing data, terminal state, and parsing results
- Provides progressive user guidance prompts

### 2. CLI Debug Flag (`--debug-keys`)
- Enables debug mode without affecting normal operation
- Shows helpful prompts in the status line
- Notifies user of log file location

### 3. Enhanced Input Instrumentation
- `paraping/input_keys.py` enhanced with debug hooks
- Zero overhead when debug mode is disabled
- Graceful fallback if debug logger unavailable

## Documentation

- **Test Plan**: [`docs/DEBUG_KEY_INPUT_TEST_PLAN.md`](docs/DEBUG_KEY_INPUT_TEST_PLAN.md)
  - 6 comprehensive test scenarios
  - Validation criteria for LLM analysis
  - Success metrics

- **Usage Guide**: [`docs/DEBUG_KEY_INPUT_USAGE.md`](docs/DEBUG_KEY_INPUT_USAGE.md)
  - Quick start instructions
  - Log format reference
  - Troubleshooting scenarios
  - Example analysis workflow

## Testing

```bash
# Run all debug-related tests
pytest tests/unit/test_debug_logger.py -v
pytest tests/integration/test_debug_logging.py -v

# Run all input-related tests
pytest tests/unit/test_input_keys.py -v

# Run all tests together (30 tests)
pytest tests/unit/test_input_keys.py tests/unit/test_debug_logger.py tests/integration/test_debug_logging.py -v
```

All tests passing: ✅ **30/30 (100%)**

## Code Quality

- ✅ Pylint score: 10.00/10
- ✅ Black formatting: Applied
- ✅ CodeQL security scan: 0 alerts
- ✅ All existing tests: Passing

## Files Added (Temporary)

These files will be **removed** after the arrow key issue is resolved:

```
paraping/debug_logger.py                      # Debug logging module
tests/unit/test_debug_logger.py               # Unit tests for logger
tests/integration/test_debug_logging.py       # Integration tests
docs/DEBUG_KEY_INPUT_TEST_PLAN.md            # Test plan
docs/DEBUG_KEY_INPUT_USAGE.md                # Usage guide
docs/DEBUG_BRANCH_README.md                  # This file
```

## Files Modified (Marked for Cleanup)

These files have debug code that will be **removed** after issue resolution:

```
paraping/input_keys.py                        # Debug logging hooks
paraping/cli.py                              # --debug-keys flag
.gitignore                                   # Debug log file pattern
```

All debug code is marked with:
```python
# DEBUG: Remove after arrow key issue is resolved
```

## Debug Log Format

The debug log (`paraping_debug_keys.log`) contains JSON events, one per line:

### Event Types

1. **SESSION_START**: Environment and terminal state at startup
2. **KEY_INPUT**: Complete details of each key press
3. **ESCAPE_SEQUENCE**: Escape sequence reading details
4. **PARSE_RESULT**: Parsing decisions and results
5. **SELECT_CALL**: Low-level stdin monitoring
6. **SESSION_END**: Session summary and cleanup

### Example Log Entry

```json
{
  "event_type": "KEY_INPUT",
  "timestamp_utc": "2025-01-21T10:30:00.123456+00:00",
  "raw_bytes_hex": "1b5b41",
  "raw_bytes_repr": "b'\\x1b[A'",
  "char_read": "arrow_up",
  "parsed_result": "arrow_up",
  "stdin_ready": true,
  "timing": {
    "sequence_duration": 0.035
  }
}
```

## Data Sufficiency for LLM Analysis

The debug logs capture enough information to answer:

1. ✅ What sequences are being received?
2. ✅ How are sequences being parsed?
3. ✅ What is the timing behavior?
4. ✅ What is the terminal configuration?
5. ✅ Where is the failure occurring?

## Workflow for Diagnosis

1. **Enable Debug Mode**: Run with `--debug-keys`
2. **Test Arrow Keys**: Press all four arrow keys as prompted
3. **Exit Cleanly**: Press 'q' to exit and finalize log
4. **Analyze Log**: Review `paraping_debug_keys.log`
5. **Identify Root Cause**: Use log data to determine issue
6. **Implement Fix**: Address the identified problem
7. **Clean Up**: Remove all debug code from this branch

## Removal Checklist

After the arrow key issue is fixed:

- [ ] Delete debug files:
  - `paraping/debug_logger.py`
  - `tests/unit/test_debug_logger.py`
  - `tests/integration/test_debug_logging.py`
  - `docs/DEBUG_KEY_INPUT_TEST_PLAN.md`
  - `docs/DEBUG_KEY_INPUT_USAGE.md`
  - `docs/DEBUG_BRANCH_README.md`

- [ ] Remove debug code from modified files:
  - `paraping/input_keys.py` (search for `# DEBUG:`)
  - `paraping/cli.py` (remove `--debug-keys` flag)
  - `.gitignore` (remove debug log pattern)

- [ ] Verify all tests still pass
- [ ] Run linter and formatter
- [ ] Update PR description
- [ ] Close debugging branch

## Support

For questions about using these debugging features, see:
- [`docs/DEBUG_KEY_INPUT_USAGE.md`](docs/DEBUG_KEY_INPUT_USAGE.md)

For questions about the implementation, see:
- [`docs/DEBUG_KEY_INPUT_TEST_PLAN.md`](docs/DEBUG_KEY_INPUT_TEST_PLAN.md)

---

**Status**: ✅ Ready for testing and diagnosis
**Next Step**: Use debug mode to capture arrow key behavior and identify root cause
