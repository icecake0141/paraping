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

# Arrow Key Input Debugging - Test Plan

## Problem Statement
Arrow keys are non-responsive in the ParaPing tool's input UI. This document outlines the test plan for debugging features designed to capture sufficient diagnostic information for LLM-based root cause analysis.

## Objectives
1. Capture detailed key input event data for all key presses, especially arrow keys
2. Guide users to perform specific key input actions through clear prompts
3. Enable LLM analysis of captured data to identify root causes
4. Ensure debugging features can be cleanly removed after issue resolution

## Test Scenarios

### TS-1: Key Input Event Capture
**Purpose**: Verify that all key input events are logged with sufficient detail

**Test Steps**:
1. Launch ParaPing with debug mode enabled: `python3 main.py --debug-keys <hostfile>`
2. Observe initial prompt message guiding user to test key inputs
3. Press the following keys in sequence:
   - Regular character keys: 'a', 'b', 'q'
   - Arrow keys: Up, Down, Left, Right
   - Escape key alone
   - Control sequences: Ctrl+C (if safe to capture)
4. Examine debug log output

**Expected Results**:
- Each key press generates a log entry
- Log entries include:
  - Timestamp (monotonic and wall clock)
  - Raw bytes received (hex representation)
  - Character/sequence read by `read_key()`
  - Parsed result from `parse_escape_sequence()` (if applicable)
  - Terminal state information (tty mode, stdin ready status)
  - Timing information (select timeout, sequence completion time)

**Success Criteria**:
- All key presses are captured in logs
- Raw byte sequences for arrow keys are visible
- Timing information shows if there are delays in sequence reception
- Log format is structured for easy LLM parsing (JSON or consistent key-value pairs)

### TS-2: Cross-Platform Arrow Key Detection
**Purpose**: Verify arrow key logging works across different terminal types

**Test Steps**:
1. Run debug mode on different terminals:
   - Standard Linux terminal (xterm, gnome-terminal)
   - SSH session (local and remote)
   - macOS Terminal.app (if available)
   - tmux/screen multiplexer
2. Press all four arrow keys in each environment
3. Compare logged escape sequences

**Expected Results**:
- Arrow key sequences are captured in each environment
- Variations in escape sequences are visible (e.g., `ESC[A` vs `ESC OA`)
- Logs clearly show which sequences are recognized vs unrecognized

**Success Criteria**:
- Debug logs reveal terminal-specific differences
- Unrecognized sequences are logged with raw bytes for analysis
- LLM can identify which sequence types are failing to parse

### TS-3: Prompt Message Functionality
**Purpose**: Verify user guidance prompts are clear and actionable

**Test Steps**:
1. Launch ParaPing in debug mode
2. Observe initial prompt message
3. Follow prompt instructions to test specific keys
4. Verify prompts update based on actions

**Expected Results**:
- Initial prompt explains debug mode and instructs user to press arrow keys
- Prompts are clearly visible (not obscured by other UI elements)
- User can understand what actions to perform without external documentation
- Prompts guide through systematic testing (e.g., "Press Up Arrow", "Press Down Arrow")

**Success Criteria**:
- Prompts are actionable and clear
- Users can complete debug test sequence without confusion
- Prompts confirm which keys have been tested

### TS-4: Timing and Sequence Completion Analysis
**Purpose**: Capture timing data to identify if arrow key issues are timeout-related

**Test Steps**:
1. Enable debug mode with verbose timing
2. Press arrow keys with different speeds:
   - Quick single press
   - Press and hold
   - Rapid repeated presses
3. Test in both local and remote (SSH) sessions

**Expected Results**:
- Logs show time between ESC reception and final character
- Timeout events are logged if escape sequence is incomplete
- Delays between bytes in multi-byte sequences are visible

**Success Criteria**:
- Timing data reveals if ARROW_KEY_READ_TIMEOUT is adequate
- Incomplete sequences due to timeout are clearly identified
- LLM can determine if timeout adjustment is needed

### TS-5: Terminal State Logging
**Purpose**: Capture terminal mode and configuration affecting input

**Test Steps**:
1. Launch debug mode and capture initial terminal state
2. Log TTY mode, termios settings (relevant flags)
3. Log stdin file descriptor state
4. Test arrow keys and capture state during key reading

**Expected Results**:
- Initial terminal configuration is logged
- TTY mode (raw vs cooked) is captured
- stdin blocking/non-blocking state is logged
- select() readiness states are logged

**Success Criteria**:
- Terminal state data is sufficient to identify configuration issues
- LLM can determine if terminal is in correct mode for arrow key reading
- Any state changes during operation are visible

### TS-6: Integration with Existing Key Handling
**Purpose**: Verify debug mode doesn't interfere with normal operation

**Test Steps**:
1. Run ParaPing in debug mode with active pinging
2. Test all existing key commands while debug logging is active:
   - 'm' (mode switch)
   - 's' (sort)
   - 'f' (filter)
   - Arrow keys (history navigation and scrolling)
3. Verify both logging and normal functionality work

**Expected Results**:
- Debug logs are written without blocking UI updates
- Normal key commands still function correctly
- Arrow key navigation works (or logged reasons for failure are visible)
- Performance is acceptable (minimal lag from logging)

**Success Criteria**:
- All non-debug functionality remains operational
- Debug logs don't cause UI rendering delays
- Logs can be written to file without blocking input processing

## Data Sufficiency for LLM Analysis

The debugging features must capture enough information for an LLM to answer:

1. **What sequences are being received?**
   - Raw byte sequences in hex format
   - Complete escape sequences or partial/incomplete ones

2. **How are sequences being parsed?**
   - Input to `parse_escape_sequence()`
   - Output from `parse_escape_sequence()`
   - Fallback behavior when sequences don't match

3. **What is the timing behavior?**
   - Time from ESC to final character
   - Whether timeouts are occurring
   - select() wait times and readiness

4. **What is the terminal configuration?**
   - TTY mode settings
   - Terminal type (from $TERM)
   - stdin state
   - Local vs remote session (SSH detection)

5. **Where is the failure occurring?**
   - Sequences not arriving (select() timeout)
   - Sequences arriving but not parsed correctly
   - Sequences parsed but not acted upon in CLI
   - Different behavior in different terminal types

## Implementation Notes

### Code Structure
- All debug code in separate module: `paraping/debug_logger.py`
- Debug mode activated via CLI flag: `--debug-keys`
- Conditional imports and execution (minimal overhead when disabled)
- Clear markers for code removal: `# DEBUG: Remove after arrow key issue resolved`

### Log Format
- Structured JSON or consistent key-value format
- Each log entry is parseable by LLM
- Timestamps in both monotonic (for intervals) and UTC (for correlation)
- Clear event types: KEY_PRESS, ESCAPE_START, ESCAPE_COMPLETE, PARSE_RESULT, etc.

### Prompt Design
- Non-intrusive: displayed in status area or dedicated prompt line
- Progressive: guides through systematic testing
- Confirmatory: acknowledges successful key captures
- Example prompts:
  - "DEBUG MODE: Press arrow keys to test. Logs written to paraping_debug.log"
  - "Testing Up Arrow... [OK] Down Arrow... [Waiting]"
  - "Arrow key test complete. Review paraping_debug.log for analysis"

## Validation Criteria

The debugging implementation is complete when:

- [ ] All test scenarios (TS-1 through TS-6) pass
- [ ] An LLM provided with debug logs can answer the 5 key questions listed above
- [ ] Debug mode can be enabled/disabled via CLI flag without code changes
- [ ] Logs are written to a file (not just console) for later analysis
- [ ] Documentation clearly explains how to use debug mode
- [ ] Code is marked for easy removal after issue resolution
- [ ] Unit tests cover debug logger functionality
- [ ] Integration test demonstrates end-to-end debug workflow

## Out of Scope

This test plan focuses on diagnostic data collection, NOT on:
- Fixing the arrow key issue itself (that comes after diagnosis)
- Performance optimization of debug logging
- Long-term retention of debug features
- Debug features for other input types (only arrow keys)

## Success Definition

This debugging feature is successful if:
1. A user experiencing arrow key issues can run debug mode
2. The generated logs contain sufficient information
3. An LLM analyzing the logs can identify the root cause
4. The identified root cause leads to a successful fix
5. Debug code can be cleanly removed after fix is verified
