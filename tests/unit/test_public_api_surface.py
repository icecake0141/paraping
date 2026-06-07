"""API surface tests for runtime exports."""

import paraping.core as core
import paraping.runtime as runtime


def test_core_all_exports_exist() -> None:
    for name in core.__all__:
        assert hasattr(core, name), f"paraping.core missing export: {name}"


def test_runtime_all_exports_exist() -> None:
    for name in runtime.__all__:
        assert hasattr(runtime, name), f"paraping.runtime missing export: {name}"


def test_runtime_expected_exports_subset() -> None:
    expected = {
        "MonitorState",
        "Scheduler",
        "SequenceTracker",
        "validate_global_rate_limit",
        "build_host_infos",
        "compute_history_page_step",
        "normalize_term_size",
        "update_history_buffer",
        "resolve_render_state",
    }
    assert expected.issubset(set(runtime.__all__))


def test_old_history_helpers_not_reexported() -> None:
    removed = {
        "create_state_snapshot_old",
        "update_history_buffer_old",
        "resolve_render_state_old",
    }
    assert removed.isdisjoint(set(runtime.__all__))


def test_core_history_helpers_not_exported() -> None:
    removed = {
        "create_state_snapshot",
        "update_history_buffer",
        "resolve_render_state",
    }
    assert removed.isdisjoint(set(core.__all__))
    for name in removed:
        assert not hasattr(core, name)
