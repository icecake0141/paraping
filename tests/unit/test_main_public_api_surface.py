"""API surface tests for main compatibility module."""

import main

EXPECTED_MAIN_EXPORTS = {
    "HISTORY_DURATION_MINUTES",
    "MAX_HOST_THREADS",
    "SNAPSHOT_INTERVAL_SECONDS",
    "asn_worker",
    "box_lines",
    "build_activity_indicator",
    "build_ascii_graph",
    "build_colored_sparkline",
    "build_colored_timeline",
    "build_display_entries",
    "build_display_lines",
    "build_display_names",
    "build_host_infos",
    "build_sparkline",
    "build_status_line",
    "build_status_metrics",
    "cli_main",
    "compute_history_page_step",
    "compute_main_layout",
    "compute_panel_sizes",
    "compute_summary_data",
    "cycle_panel_position",
    "flash_screen",
    "format_display_name",
    "format_timestamp",
    "format_timezone_label",
    "get_cached_page_step",
    "get_terminal_size",
    "handle_options",
    "latest_ttl_value",
    "main",
    "parse_escape_sequence",
    "parse_host_file_line",
    "ping_host",
    "read_input_file",
    "read_key",
    "render_display",
    "render_fullscreen_rtt_graph",
    "render_help_view",
    "render_host_selection_view",
    "render_square_view",
    "render_status_box",
    "render_summary_view",
    "resolve_asn",
    "ring_bell",
    "run",
    "should_flash_on_fail",
    "should_retry_asn",
    "toggle_panel_visibility",
}


def test_main_all_exports_exist() -> None:
    for name in main.__all__:
        assert hasattr(main, name), f"main missing export: {name}"


def test_main_dir_includes_lazy_exports() -> None:
    names = set(dir(main))
    # Spot-check lazy and non-lazy compatibility exports.
    expected = {
        "handle_options",
        "run",
        "cli_main",
        "build_display_entries",
        "ping_host",
        "resolve_asn",
    }
    assert expected.issubset(names)


def test_main_lazy_exports_match_all() -> None:
    lazy_keys = set(main._LAZY_EXPORTS.keys())  # pylint: disable=protected-access
    all_exports = set(main.__all__)

    # Every lazy export is part of the declared compatibility surface.
    assert lazy_keys.issubset(all_exports)

    # Every declared export should be resolvable either eagerly or lazily.
    unresolved = [name for name in main.__all__ if name not in main.__dict__ and name not in lazy_keys]
    assert unresolved == []


def test_main_all_has_no_duplicates() -> None:
    assert len(main.__all__) == len(set(main.__all__))


def test_main_export_contract_is_intentional() -> None:
    assert set(main.__all__) == EXPECTED_MAIN_EXPORTS


def test_legacy_history_helpers_removed_from_main() -> None:
    assert "create_state_snapshot" not in main.__all__
    assert "update_history_buffer" not in main.__all__
    assert "resolve_render_state" not in main.__all__
    assert not hasattr(main, "create_state_snapshot")
    assert not hasattr(main, "update_history_buffer")
    assert not hasattr(main, "resolve_render_state")
