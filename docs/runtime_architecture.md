# ParaPing Runtime Architecture

This document describes the current runtime layout after the package cleanup.

## Source Of Truth

- CLI entrypoint and event loop: `paraping.cli`
- Runtime state engine: `paraping.runtime.engine`
- Runtime domain objects: `paraping.runtime.domain`
- History snapshots: `paraping.runtime.history`
- Render-state selection: `paraping.runtime.render_state`
- Render projection for UI functions: `paraping.runtime.render_projection`
- Host parsing and host-info construction: `paraping.runtime.hosts`
- Scheduler and rate limits: `paraping.runtime.scheduler`, `paraping.runtime.rate_limit`
- Sequence tracking: `paraping.runtime.sequence_tracker`
- Terminal sizing and history paging: `paraping.runtime.term_size`, `paraping.runtime.paging`

## Entry Points

- Installed command: `paraping = "paraping.cli:main"`
- Module execution: `python -m paraping`

Top-level script shims have been removed. New code should import from `paraping.*`
or `paraping.runtime.*` directly.

## Runtime Flow

1. `paraping.cli` loads hosts, config, scheduler, and runtime state.
2. Ping workers emit normalized events.
3. Events are mirrored into `MonitorState`.
4. `paraping.runtime.history.update_history_buffer` records bounded snapshots.
5. `paraping.runtime.render_state.resolve_render_state` selects live or historical state.
6. `paraping.runtime.render_projection.project_render_state` builds the render buffers consumed by `paraping.ui_render`.

## Testing

Run the complete suite after structural changes:

```bash
pytest
```

Focused runtime routes:

```bash
pytest tests/unit/test_runtime_engine.py tests/unit/test_runtime_history.py tests/unit/test_runtime_render_state.py -v
pytest tests/unit/test_runtime_hosts.py tests/unit/test_runtime_paging.py tests/unit/test_runtime_term_size.py -v
pytest tests/unit/test_scheduler.py tests/unit/test_scheduler_integration.py tests/unit/test_rate_limit.py -v
```
