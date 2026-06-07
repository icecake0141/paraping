# Unit Test File Organization

Large historical test files are split by the runtime boundary they exercise.
Keep new tests near the code path they protect instead of grouping them under
legacy entry-point names.

## CLI and Startup

### test_cli_options.py (221 lines, 18 tests)

CLI option parsing and file input reading.

**Test Classes:**
- `TestHandleOptions` - Command line option parsing
- `TestReadInputFile` - File input reading functionality

### test_cli_ping.py (363 lines, 11 tests)

Ping host behavior and CLI run-path validation.

**Test Classes:**
- `TestPingHost` - Ping host functionality
- `TestMain` - CLI run function tests

### test_cli_interaction.py (557 lines, 22 tests)

User interaction, keyboard handling, and CLI-controlled UI state.

**Test Classes:**
- `TestEscapeSequenceParsing` - Escape sequence parsing for arrow keys
- `TestPanelToggle` - Summary panel toggle behavior
- `TestQuitHotkey` - Quit hotkey functionality
- `TestFlashAndBell` - Flash and bell notification features
- `TestArrowKeyNavigation` - Arrow key navigation for history viewing

## UI Rendering

### test_ui_render.py (2760 lines, 224 tests)

Rendering help views, boxes, ASCII graphs, and broader render contracts.

**Test Classes:**
- `TestHelpView` - Help view rendering
- `TestBoxedRendering` - Box rendering helpers
- `TestAsciiGraph` - ASCII graph rendering helpers

### test_ui_layout.py (231 lines, 11 tests)

Layout computation and terminal size handling.

**Test Classes:**
- `TestLayoutComputation` - Layout computation functions
- `TestTerminalSize` - Terminal size retrieval function

### test_ui_display.py (723 lines, 36 tests)

Display formatting and summary data computation.

**Test Classes:**
- `TestDisplayNames` - Display name building functions
- `TestSummaryData` - Summary data computation
- `TestTimezoneFormatting` - Timezone handling functions
- `TestHostInfoBuilding` - Host info building functions
- `TestSparklineBuilding` - Sparkline building function
- `TestActivityIndicator` - Activity indicator behavior
- `TestColorOutput` - Colored output helpers
- `TestStatusLine` - Status line building function

### test_ui_features.py (201 lines, 14 tests)

TTL display behavior and host selection rendering.

**Test Classes:**
- `TestTTLFunctionality` - TTL capture and display functionality
- `TestHostSelectionView` - Host selection view rendering and interaction
- `TestHostSelectionKeyBindings` - n/p key bindings for host selection navigation

## Total

- **7 focused files**
- **5056 total lines**
- **336 tests**

## Benefits

1. **Easier navigation**: Find tests by feature area.
2. **Faster test execution**: Run specific feature tests independently.
3. **Better maintainability**: Changes to one boundary do not obscure another.
4. **Clearer ownership**: CLI, runtime, and UI tests match current package structure.
