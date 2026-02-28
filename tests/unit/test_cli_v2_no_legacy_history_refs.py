"""Guardrails to keep CLI runtime on v2 history/render flow."""

import ast
from pathlib import Path


CLI_PATH = Path(__file__).resolve().parents[2] / "paraping" / "cli.py"


def _imported_names_from_core(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "paraping.core":
            names.update(alias.name for alias in node.names)
    return names


def test_cli_does_not_import_legacy_history_helpers_from_core() -> None:
    source = CLI_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CLI_PATH))
    imported = _imported_names_from_core(tree)
    forbidden = {"create_state_snapshot", "update_history_buffer", "resolve_render_state"}
    assert imported.isdisjoint(forbidden)


def test_cli_source_does_not_call_legacy_history_helpers() -> None:
    source = CLI_PATH.read_text(encoding="utf-8")
    assert "update_history_buffer(" not in source
    assert "resolve_render_state(" not in source
    assert "create_state_snapshot(" not in source
