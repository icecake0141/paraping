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

# Arrow Key Debugging Guide

## Problem Overview

This guide explains how to use the debugging features implemented to troubleshoot arrow key non-responsiveness in ParaPing. These debugging features capture detailed diagnostic information about keyboard input for LLM-based root cause analysis.

**NOTE:** These debugging features are temporary and will be removed once the arrow key issue is resolved.

## Quick Start

### Enable Debug Mode

Run ParaPing with the `--debug-keys` flag:

```bash
python3 main.py --debug-keys localhost
```

Or with a host file:

```bash
python3 main.py --debug-keys -f hosts.txt
```

### What Happens in Debug Mode

1. **Startup Message**: You'll see a notification that debug mode is enabled
2. **Prompt Messages**: The status line will display instructions to test arrow keys
3. **Key Logging**: All key presses are logged to `paraping_debug_keys.log`
4. **Test Completion**: The prompt updates as you test each arrow key
5. **Exit Message**: On exit, you'll see where the debug log was saved

### Test Procedure

1. Start ParaPing with `--debug-keys`
2. Follow the on-screen prompts to press each arrow key:
   - Press Up Arrow (↑)
   - Press Down Arrow (↓)
   - Press Left Arrow (←)
   - Press Right Arrow (→)
3. Also test some regular keys (letters, numbers)
4. Exit ParaPing (press 'q')
5. Review the debug log file

## Debug Log Format

The debug log (`paraping_debug_keys.log`) contains JSON-formatted events, one per line.

### Event Types

#### SESSION_START
Captures initial environment and terminal state:
```json
{
  "event_type": "SESSION_START",
  "timestamp_utc": "2025-01-21T09:30:00.123456+00:00",
  "platform": "linux",
  "terminal_type": "xterm-256color",
  "ssh_session": false,
  "terminal_state": {
    "iflag": 9216,
    "lflag": 35387
  }
}
```

#### KEY_INPUT
Captures each key press with full details:
```json
{
  "event_type": "KEY_INPUT",
  "timestamp_utc": "2025-01-21T09:30:05.234567+00:00",
  "timestamp_monotonic": 5.123456,
  "elapsed_seconds": 5.0,
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

**Important fields for diagnosis:**
- `raw_bytes_hex`: Hex representation of exactly what was received
- `char_read`: What `read_key()` returned
- `parsed_result`: Result from `parse_escape_sequence()`
- `timing.sequence_duration`: How long it took to read the sequence

#### ESCAPE_SEQUENCE
Details about escape sequence reading:
```json
{
  "event_type": "ESCAPE_SEQUENCE",
  "sequence": "[A",
  "sequence_hex": "5b41",
  "complete": true,
  "duration_seconds": 0.028,
  "timeout_occurred": false
}
```

#### PARSE_RESULT
Shows parsing logic decisions:
```json
{
  "event_type": "PARSE_RESULT",
  "input_sequence": "[A",
  "input_hex": "5b41",
  "parsed_result": "arrow_up",
  "success": true,
  "fallback_used": false
}
```

#### SELECT_CALL
Low-level stdin monitoring:
```json
{
  "event_type": "SELECT_CALL",
  "timeout_requested": 0.1,
  "stdin_ready": true,
  "duration_seconds": 0.001
}
```

## Interpreting the Logs

### Scenario 1: Arrow Keys Not Captured at All

**Symptoms in logs:**
- No `ESCAPE_SEQUENCE` events when you press arrow keys
- Only single-character `KEY_INPUT` events

**Likely cause:** 
- Terminal is not sending escape sequences
- Terminal mode issue (not in raw/cbreak mode)

**Check:**
- `terminal_state` in SESSION_START
- `raw_bytes_hex` - should start with `1b` (ESC) for arrow keys

### Scenario 2: Escape Sequences Timeout

**Symptoms in logs:**
- `ESCAPE_SEQUENCE` events with `timeout_occurred: true`
- `sequence` field is empty or incomplete

**Likely cause:**
- Bytes arriving too slowly
- `ARROW_KEY_READ_TIMEOUT` is too short for your environment

**Check:**
- `duration_seconds` in ESCAPE_SEQUENCE events
- Multiple SELECT_CALL events timing out

### Scenario 3: Sequences Captured But Not Parsed

**Symptoms in logs:**
- Complete `ESCAPE_SEQUENCE` events
- `PARSE_RESULT` shows `success: false`
- `char_read` returns ESC character instead of arrow key name

**Likely cause:**
- Unknown escape sequence format
- Sequence doesn't match expected patterns

**Check:**
- `sequence` and `sequence_hex` to see actual format
- Compare with expected patterns: `[A`, `[B`, `[C`, `[D`, `OA`, `OB`, etc.

### Scenario 4: Parsed But CLI Doesn't Respond

**Symptoms in logs:**
- `PARSE_RESULT` shows `success: true`
- `parsed_result` is correct (e.g., "arrow_up")
- Arrow keys still don't work in UI

**Likely cause:**
- Issue in CLI key handling logic (not in input_keys module)
- State prevents arrow key actions

**Check:**
- Test in different UI states (help screen, host selection, etc.)
- Verify arrow key handlers in cli.py are being reached

## Common Terminal Types

### Linux/xterm
Expected sequences: `ESC[A`, `ESC[B`, `ESC[C`, `ESC[D`

### SSH Sessions
May have slower byte arrival - check `duration_seconds`

### tmux/screen
May use application cursor mode: `ESCA`, `ESCB`, `ESCC`, `ESCD`

### macOS Terminal
Usually same as xterm, but check for variations

## Providing Logs for Analysis

When requesting help or analysis:

1. **Include the full log file** (`paraping_debug_keys.log`)
2. **Describe your environment:**
   - Operating system
   - Terminal emulator
   - SSH vs local
   - tmux/screen usage
3. **Describe the symptoms:**
   - Which arrow keys don't work
   - Which UI contexts (main view, help, history navigation)
   - Any error messages
4. **Test results:**
   - Did the debug prompt update as you pressed arrows?
   - What did the keys do (nothing, wrong action, ESC)?

## Files Added for Debugging

These files will be **removed** after the issue is resolved:

- `paraping/debug_logger.py` - Debug logging module
- `tests/unit/test_debug_logger.py` - Unit tests for logger
- `docs/DEBUG_KEY_INPUT_TEST_PLAN.md` - Test plan
- `docs/DEBUG_KEY_INPUT_USAGE.md` - This file

Modified files (debug code marked with `# DEBUG:` comments):
- `paraping/input_keys.py` - Added logging calls
- `paraping/cli.py` - Added `--debug-keys` flag and logger initialization

## Code Markers

All debug code is marked with comments:
```python
# DEBUG: Remove this after arrow key issue is resolved
```

Use these markers to easily identify and remove debug code once the issue is fixed.

## Troubleshooting Debug Mode Itself

### Debug Log Not Created

**Check:**
- File permissions in current directory
- Disk space
- Run with `ls -la paraping_debug_keys.log` after exiting

### No Events in Log

**Check:**
- Debug mode actually enabled (`--debug-keys` flag)
- Logger initialized (should see startup message)

### Incomplete Log

**Check:**
- Program exited cleanly (not killed with SIGKILL)
- SESSION_END event should be last line

## Example Analysis Workflow

1. Run: `python3 main.py --debug-keys localhost`
2. Press all four arrow keys
3. Press some letter keys
4. Exit with 'q'
5. View log: `cat paraping_debug_keys.log | python3 -m json.tool`
6. Check for patterns in failed parses
7. Compare working vs non-working keys
8. Identify where in the pipeline the issue occurs

## Next Steps After Diagnosis

Once the root cause is identified:

1. Fix the underlying issue
2. Test the fix thoroughly
3. Remove all debug code:
   - Delete debug files
   - Remove `# DEBUG:` sections from modified files
   - Remove `--debug-keys` CLI option
4. Verify existing tests still pass
5. Close the debugging branch
