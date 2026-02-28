# ParaPing v2 Migration Status

## Migration Summary
- Code-path migration is complete for current runtime:
  - CLI/runtime state flow is v2-based.
  - Legacy history helpers were removed from `main`, `paraping.core`, and `paraping_v2`.
  - Guardrail tests prevent reintroduction of removed APIs/modules.
- Remaining work is operational/documentation maintenance only.

## Current Source of Truth
- Event/state engine: `paraping_v2.engine`
- Scheduler: `paraping_v2.scheduler`
- Sequence tracking: `paraping_v2.sequence_tracker`
- Rate limit: `paraping_v2.rate_limit`
- Render-state resolution: `paraping_v2.render_state`
- History snapshots (new): `paraping_v2.history`
- Host parsing and host-info construction: `paraping_v2.hosts`
- History page-step caching: `paraping_v2.paging`
- Terminal-size normalization/layout width extraction: `paraping_v2.term_size`

## Compatibility Layers Still Exposed
- `paraping.core` keeps legacy function names and delegates to v2 helpers:
  - `validate_global_rate_limit`
  - `parse_host_file_line`
  - `read_input_file`
  - `build_host_infos`
  - `compute_history_page_step`
  - `get_cached_page_step`
  - `_normalize_term_size`
  - `_extract_timeline_width_from_layout`
- `main.py` keeps compatibility exports for tests and external callers, now wrapped over v2 implementations.
  - Legacy history helpers were removed from `main` (including non-`__all__` access).
- Legacy history helpers were also removed from `paraping.core`.
- `paraping_v2.legacy_history` was removed after compatibility-layer retirement.

### `main.py` Compatibility Surface Rule
- `main.__all__` is treated as the compatibility contract for the shim module.
- Lazy exports are resolved through `main._LAZY_EXPORTS` + `main.__getattr__`.
- Any symbol in `main._LAZY_EXPORTS` must also exist in `main.__all__`.
- New code should import from `paraping.*` / `paraping_v2.*` directly instead of `main`.

### Compatibility Quality Gates
- `tests/unit/test_main_public_api_surface.py`:
  validates `main.__all__` and lazy-export consistency.
- `tests/unit/test_main_test_usage_surface.py`:
  validates that every `from main import ...` used by tests is declared in `main.__all__`.
- `tests/unit/test_main_lazy_wrappers.py`:
  validates lazy wrappers and confirms removed legacy history helpers are absent.
- `tests/unit/test_main_legacy_history_usage_contract.py`:
  ensures no tests reference removed legacy history helpers on `main`.
- `tests/unit/test_cli_v2_no_legacy_history_refs.py`:
  ensures `paraping.cli` does not regress to importing/calling legacy history helpers.
- `tests/unit/test_legacy_api_usage_contract.py`:
  ensures removed legacy history APIs are not called from `paraping/*`.
- `tests/unit/test_public_api_surface.py`:
  validates export surfaces for `paraping.core` and `paraping_v2` (including non-reexport of legacy history helpers).
- `tests/unit/test_v2_legacy_module_removed.py`:
  ensures removed module `paraping_v2.legacy_history` is not importable.
- `tests/unit/test_no_main_imports_in_package.py`:
  ensures package code (`paraping/*`, `paraping_v2/*`) does not depend on `main.py` shim.
- `tests/unit/test_removed_legacy_symbol_imports.py`:
  ensures removed legacy symbols cannot be imported from `main` or `paraping.core`.

## Runtime Path Today
1. Ping results are applied to `state["v2_state"]`.
2. Render source is resolved from `v2_history_buffer` via `resolve_v2_render_state`.
3. A legacy-shaped render payload is projected from v2 state for existing UI functions.

## Remaining Migration Targets
- Periodic doc audit to remove stale historical references in non-critical docs.
- Optional cleanup: remove compatibility-focused tests once long-term API policy is finalized.

## Deprecation Policy (Current)
- Removed APIs:
  - `main.create_state_snapshot`
  - `main.update_history_buffer`
  - `main.resolve_render_state`
  - `paraping.core.create_state_snapshot`
  - `paraping.core.update_history_buffer`
  - `paraping.core.resolve_render_state`
- Current implementation should use:
  - `paraping_v2.history.create_state_snapshot_v2`
  - `paraping_v2.history.update_history_buffer_v2`
  - `paraping_v2.render_state.resolve_v2_render_state`
