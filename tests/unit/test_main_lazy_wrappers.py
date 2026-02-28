"""Tests for lazy compatibility wrappers in main.py."""

from unittest.mock import patch

import main


def test_handle_options_wrapper_delegates() -> None:
    with patch("paraping.cli.handle_options", return_value="opts") as mock_handle:
        assert main.handle_options() == "opts"
        mock_handle.assert_called_once_with()


def test_run_wrapper_delegates() -> None:
    with patch("paraping.cli.run", return_value=None) as mock_run:
        main.run("args")
        mock_run.assert_called_once_with("args")


def test_cli_main_wrapper_delegates() -> None:
    with patch("paraping.cli.main", return_value=None) as mock_main:
        main.cli_main()
        mock_main.assert_called_once_with()


def test_input_key_wrappers_delegate() -> None:
    with patch("paraping.input_keys.parse_escape_sequence", return_value="arrow_up") as mock_parse:
        assert main.parse_escape_sequence("[A") == "arrow_up"
        mock_parse.assert_called_once_with("[A")
    with patch("paraping.input_keys.read_key", return_value="k") as mock_read:
        assert main.read_key() == "k"
        mock_read.assert_called_once_with()


def test_main_legacy_history_helpers_removed() -> None:
    assert not hasattr(main, "create_state_snapshot")
    assert not hasattr(main, "update_history_buffer")
    assert not hasattr(main, "resolve_render_state")
