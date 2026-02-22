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

# Keyboard Input Migration to readchar

## Overview

As of version 1.x, ParaPing migrated keyboard input handling to the [`readchar`](https://github.com/magmax/python-readchar)
library for cross-platform key definitions, while continuing to read directly from `sys.stdin` to avoid flushing buffered
input on some terminals.

## Changes

### What Changed

**Before (Custom Implementation):**
- Manual parsing of ANSI escape sequences
- Platform-specific handling using `select.select()` and `sys.stdin.read()`
- Custom timeout logic with `time.monotonic()`
- All code in `paraping/input_keys.py`

**After (readchar-assisted Implementation):**
- Reads input via `sys.stdin.read(1)` with `select.select()` for non-blocking behavior
- Uses `readchar` key constants and `parse_escape_sequence()` for consistent arrow-key mapping
- Preserves the public API and escape-sequence compatibility

### API Compatibility

The public API remains **fully compatible**. No changes are required for existing code:

- `read_key()` - Returns arrow key names ('arrow_up', 'arrow_down', etc.), characters, or None
- `parse_escape_sequence(seq)` - Still available for parsing custom sequences

### Benefits

1. **Cross-platform Support**: readchar handles platform differences (Linux, macOS, Windows) internally
2. **Maintainability**: Less custom code to maintain
3. **Reliability**: Well-tested library used by many projects
4. **Future Features**: Easier to add support for more special keys (F1-F12, etc.)

## Technical Details

### Implementation Strategy

The migration preserves the original non-blocking behavior by:

1. Using `select.select()` with zero timeout to check if input is available
2. Reading single bytes directly from `sys.stdin` once input is ready
3. Mapping arrow key sequences with `parse_escape_sequence()` (and `readchar` constants for compatibility)

### Sequence Handling

readchar provides key constants that map to escape sequences (e.g., `readchar.key.UP` is `"\x1b[A"`). The
`_map_readchar_key()` helper:

1. Maps readchar's standard constants (UP, DOWN, LEFT, RIGHT) to arrow key names
2. Falls back to `parse_escape_sequence()` for non-standard sequences
3. Supports modified keys (Ctrl+Arrow, Shift+Arrow, etc.)
4. Returns original value for unrecognized input

### Fallback Behavior

If readchar is not available, arrow-key constants are unavailable, but direct stdin reads still work for single-byte
input.

## Testing

All original tests were updated to work with the readchar-assisted implementation:

- 9 tests for `parse_escape_sequence()` - unchanged
- 11 tests for `read_key()` - updated to mock `sys.stdin.read()`
- Added test for exception handling and direct-read behavior

Run tests with:
```bash
make test
# or
pytest tests/unit/test_input_keys.py -v
```

## Dependencies

### New Dependency

- **readchar** >= 4.2.1 (Apache-2.0 license)
  - No known security vulnerabilities
  - Cross-platform support (Linux, macOS, Windows)
  - Active maintenance

### Installation

The dependency is automatically installed via:
```bash
make dev  # For development
# or
pip install -r requirements.txt  # For production
```

## Migration Notes for Maintainers

### If You Need to Debug Input Issues

1. Check if readchar is available: `READCHAR_AVAILABLE` flag
2. Test with different terminal emulators (xterm, iTerm2, Windows Terminal, etc.)
3. Use the unit tests as a reference for expected behavior
4. Remember: `select.select()` handles the non-blocking part, readchar handles the parsing

### Known Limitations

1. **Timeout Behavior**: Reading escape sequences relies on `select.select()` for timeouts
2. **No Input Simulation**: Can't easily simulate keypresses without mocking (tests use mocks)
3. **Terminal Requirements**: Still requires a TTY (checked via `sys.stdin.isatty()`)

### Compatibility Notes

- **Windows**: readchar uses `msvcrt` module on Windows
- **Unix/Linux/macOS**: readchar uses `termios` and `tty` modules
- **SSH/Remote Sessions**: Works, but may have increased latency (see ARROW_KEY_READ_TIMEOUT)

## Future Improvements

Potential enhancements enabled by readchar:

1. Support for function keys (F1-F12)
2. Support for Home/End/PageUp/PageDown
3. Better handling of modifier key combinations
4. Improved Windows console support

## References

- [readchar GitHub Repository](https://github.com/magmax/python-readchar)
- [ParaPing Issue Tracker](https://github.com/icecake0141/paraping/issues)
- Original implementation: commit before this migration

---

**Last Updated**: 2026-01-26
**Author**: ParaPing Team (with LLM assistance)
**License**: Apache-2.0
