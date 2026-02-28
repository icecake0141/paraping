"""Contract test: no remaining usage of removed legacy history helpers on main."""

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"

LEGACY_ATTRS = {
    "create_state_snapshot",
    "update_history_buffer",
    "resolve_render_state",
}


def _uses_main_legacy_history_attr(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "main" and node.attr in LEGACY_ATTRS:
                return True
    return False


def test_main_legacy_history_helpers_not_used_anywhere() -> None:
    offenders: list[str] = []
    for py_file in TESTS_DIR.rglob("test_*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        if _uses_main_legacy_history_attr(tree):
            offenders.append(str(py_file.relative_to(REPO_ROOT)))

    assert offenders == []
