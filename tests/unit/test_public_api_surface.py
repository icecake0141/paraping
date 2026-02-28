"""API surface tests for compatibility and v2 exports."""

import paraping.core as core
import paraping_v2 as v2


def test_core_all_exports_exist() -> None:
    for name in core.__all__:
        assert hasattr(core, name), f"paraping.core missing export: {name}"


def test_v2_all_exports_exist() -> None:
    for name in v2.__all__:
        assert hasattr(v2, name), f"paraping_v2 missing export: {name}"


def test_v2_expected_exports_subset() -> None:
    expected = {
        "MonitorState",
        "Scheduler",
        "SequenceTracker",
        "validate_global_rate_limit",
        "build_host_infos_v2",
        "compute_history_page_step_v2",
        "normalize_term_size_v2",
        "update_history_buffer_v2",
        "resolve_v2_render_state",
    }
    assert expected.issubset(set(v2.__all__))


def test_v2_legacy_history_helpers_not_reexported() -> None:
    removed = {
        "create_state_snapshot_legacy",
        "update_history_buffer_legacy",
        "resolve_render_state_legacy",
    }
    assert removed.isdisjoint(set(v2.__all__))


def test_core_legacy_history_helpers_removed() -> None:
    removed = {
        "create_state_snapshot",
        "update_history_buffer",
        "resolve_render_state",
    }
    assert removed.isdisjoint(set(core.__all__))
    for name in removed:
        assert not hasattr(core, name)
