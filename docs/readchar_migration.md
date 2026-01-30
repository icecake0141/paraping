# Keyboard Input Migration to readchar

## Overview

As of version 1.x, ParaPing has migrated its keyboard input handling from a custom implementation using `select` and `sys.stdin` to the [`readchar`](https://github.com/magmax/python-readchar) library for improved cross-platform reliability and maintainability.

## Changes

### What Changed

**Before (Custom Implementation):**
- Manual parsing of ANSI escape sequences
- Platform-specific handling using `select.select()` and `sys.stdin.read()`
- Custom timeout logic with `time.monotonic()`
- All code in `paraping/input_keys.py`

**After (readchar-based Implementation):**
- Uses `readchar.readkey()` for reading keyboard input
- Still uses `select.select()` for non-blocking behavior
- Simplified escape sequence handling via readchar's built-in constants
- Maintains backward compatibility for all public APIs

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
2. Only calling `readchar.readkey()` when input is ready
3. Mapping readchar's key constants to ParaPing's naming convention

### Sequence Handling

readchar returns full escape sequences as strings (e.g., `"\x1b[A"` for up arrow). The `_map_readchar_key()` function:

1. Maps readchar's standard constants (UP, DOWN, LEFT, RIGHT) to arrow key names
2. Falls back to `parse_escape_sequence()` for non-standard sequences
3. Supports modified keys (Ctrl+Arrow, Shift+Arrow, etc.)
4. Returns original value for unrecognized input

### Fallback Behavior

If readchar is not available:
- `READCHAR_AVAILABLE` flag is set to False
- Falls back to basic `sys.stdin.read(1)` for single character input
- Arrow keys won't be recognized in fallback mode

## Testing

All original tests were updated to work with the readchar implementation:

- 9 tests for `parse_escape_sequence()` - unchanged
- 11 tests for `read_key()` - updated to mock `readchar.readkey()`
- Added test for exception handling

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

1. **Timeout Behavior**: readchar itself is blocking, so we rely on `select.select()` for timeouts
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
