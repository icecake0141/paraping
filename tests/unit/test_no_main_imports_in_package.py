"""Guardrail: package code should not depend on top-level main compatibility shim."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIRS = [REPO_ROOT / "paraping", REPO_ROOT / "paraping_v2"]
ALLOWED_IMPORTERS = {
    REPO_ROOT / "paraping" / "__main__.py",
}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for directory in PACKAGE_DIRS:
        files.extend(p for p in directory.rglob("*.py") if p.is_file())
    return files


def test_package_code_does_not_import_main_shim() -> None:
    offenders: list[str] = []
    for py_file in _python_files():
        if py_file in ALLOWED_IMPORTERS:
            continue
        content = py_file.read_text(encoding="utf-8")
        if "import main" in content or "from main import" in content:
            offenders.append(str(py_file.relative_to(REPO_ROOT)))
    assert offenders == []
