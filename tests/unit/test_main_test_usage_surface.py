"""Ensure test-side imports from main are covered by main.__all__."""

import ast
from pathlib import Path

import main


def _collect_imported_names_from_main(tests_dir: Path) -> set[str]:
    imported: set[str] = set()
    for py_file in tests_dir.rglob("test_*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "main":
                for alias in node.names:
                    # Ignore wildcard imports (not used in this repository).
                    if alias.name != "*":
                        imported.add(alias.name)
    return imported


def _collect_patched_names_on_main(tests_dir: Path) -> set[str]:
    patched: set[str] = set()
    for py_file in tests_dir.rglob("test_*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "patch" and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str) and first_arg.value.startswith("main."):
                    patched.add(first_arg.value.split(".", 1)[1])
    return patched


def test_all_test_imports_from_main_are_declared_in_all() -> None:
    tests_dir = Path(__file__).resolve().parents[1]
    imported = _collect_imported_names_from_main(tests_dir)
    exported = set(main.__all__)
    missing = sorted(imported - exported)
    assert missing == []


def test_all_patch_targets_on_main_exist() -> None:
    def has_dotted_attr(obj, dotted: str) -> bool:
        current = obj
        for part in dotted.split("."):
            if not hasattr(current, part):
                return False
            current = getattr(current, part)
        return True

    tests_dir = Path(__file__).resolve().parents[1]
    patched = _collect_patched_names_on_main(tests_dir)
    missing = sorted(name for name in patched if not has_dotted_attr(main, name))
    assert missing == []
