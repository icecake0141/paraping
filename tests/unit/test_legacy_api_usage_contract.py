"""Contract test: removed legacy history APIs are not called from paraping package."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PARAPING_DIR = REPO_ROOT / "paraping"


def _py_files_under(path: Path) -> list[Path]:
    return [p for p in path.rglob("*.py") if p.is_file()]


def _legacy_hits(content: str) -> bool:
    return any(
        token in content
        for token in (
            "create_state_snapshot(",
            "update_history_buffer(",
            "resolve_render_state(",
        )
    )


def test_legacy_history_api_calls_absent_from_paraping_package() -> None:
    offenders: list[str] = []
    for py_file in _py_files_under(PARAPING_DIR):
        content = py_file.read_text(encoding="utf-8")
        if _legacy_hits(content):
            offenders.append(str(py_file.relative_to(REPO_ROOT)))

    assert offenders == []
