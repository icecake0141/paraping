"""Guardrail: removed legacy symbols must remain unavailable from public shims."""

import pytest


@pytest.mark.parametrize(
    ("statement", "symbol"),
    [
        ("from main import create_state_snapshot", "create_state_snapshot"),
        ("from main import update_history_buffer", "update_history_buffer"),
        ("from main import resolve_render_state", "resolve_render_state"),
        ("from paraping.core import create_state_snapshot", "create_state_snapshot"),
        ("from paraping.core import update_history_buffer", "update_history_buffer"),
        ("from paraping.core import resolve_render_state", "resolve_render_state"),
    ],
)
def test_removed_legacy_symbols_not_importable(statement: str, symbol: str) -> None:
    with pytest.raises(ImportError, match=symbol):
        exec(statement, {})
