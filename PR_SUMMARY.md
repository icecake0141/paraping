# Enhancement: Display ping square view as a time-series

## Summary
This PR enhances the square view in ParaPing to display results as a time-series, showing a horizontal sequence of colored squares for each host over time, similar to the timeline and sparkline views. Previously, the square view only showed the latest status as a single square per host.

## Visual Example
![Square View Demo](https://github.com/user-attachments/assets/87fac123-8731-478d-9ba1-cc10c301ab30)

**Before**: Single square showing only the latest status per host
**After**: 60+ squares showing historical status over time with time axis

## Changes Made

### Core Implementation
1. **Added `build_colored_square_timeline` function** (`paraping/ui_render.py`)
   - Generates a horizontal sequence of colored squares from timeline symbols
   - Uses green for OK (success/slow), red for fail, gray for pending
   - Intentionally uses different colors than timeline view (green vs white) for visual distinction

2. **Enhanced `render_square_view` function** (`paraping/ui_render.py`)
   - Added `interval_seconds` parameter to match timeline/sparkline views
   - Updated layout calculation to account for time axis line (header_lines + 1)
   - Calls `resize_buffers` to dynamically match timeline width
   - Renders horizontal sequence of squares instead of single square
   - Adds time axis at bottom showing time labels (10s, 20s, 30s, etc.)

3. **Updated `render_main_view` function** (`paraping/ui_render.py`)
   - Passes `interval_seconds` parameter to `render_square_view`

### Testing
4. **Updated test fixtures** (`tests/unit/test_main_rendering.py`)
   - Added complete buffer structure (rtt_history, time_history, ttl_history, categories)
   - Required for `resize_buffers` to work properly

5. **Added new tests**
   - `test_render_square_view_time_series`: Verifies multiple squares are rendered
   - `test_render_square_view_interval_seconds`: Verifies interval_seconds parameter works

## Benefits
✅ **Consistency**: All main result views (timeline, sparkline, square) now share time-series/scrolling behavior
✅ **Enhanced usefulness**: Users can visualize history of status for each host at a glance
✅ **Minimal disruption**: Reuses existing infrastructure (resize_buffers, build_time_axis, compute_main_layout)
✅ **Backward compatible**: Existing tests updated and passing, no breaking changes

## Testing Results
- ✅ All 255 unit tests pass
- ✅ New tests verify time-series behavior with multiple squares
- ✅ Linting: Code follows project style (pre-existing ruff issues not introduced by this PR)
- ✅ Security scan: No vulnerabilities found (CodeQL)
- ✅ Manual testing: Visual verification with demo script confirms correct rendering

## Code Review Feedback Addressed
1. ✅ Added comprehensive comment explaining color scheme differences between square and timeline views
2. ✅ Added test for `interval_seconds` parameter to verify it affects time axis rendering

## Security Summary
No security vulnerabilities were introduced or discovered by this change. CodeQL analysis found 0 alerts.

## License & Attribution
All modified files include proper Apache-2.0 license headers and LLM attribution as required by project policy.
