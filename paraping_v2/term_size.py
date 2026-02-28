"""Terminal-size normalization and layout width extraction helpers for v2."""

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, Optional

TIMELINE_LABEL_ESTIMATE_WIDTH = 15


def build_term_size_v2(columns_value: Any, lines_value: Any) -> Optional[SimpleNamespace]:
    """Build a terminal size namespace from column/line values."""
    try:
        columns = int(columns_value)
        lines = int(lines_value)
    except (ValueError, TypeError):
        return None
    if columns <= 0 or lines <= 0:
        return None
    return SimpleNamespace(columns=columns, lines=lines)


def normalize_term_size_v2(term_size: Any) -> Optional[SimpleNamespace]:
    """Normalize terminal size to an object with .columns/.lines attributes."""
    if term_size is None:
        return None
    if hasattr(term_size, "columns") and hasattr(term_size, "lines"):
        return build_term_size_v2(term_size.columns, term_size.lines)
    if isinstance(term_size, dict):
        return build_term_size_v2(term_size.get("columns"), term_size.get("lines"))
    if isinstance(term_size, Sequence) and not isinstance(term_size, (str, bytes)):
        if len(term_size) >= 2:
            try:
                return build_term_size_v2(term_size[0], term_size[1])
            except TypeError:
                return None
    return None


def extract_timeline_width_from_layout_v2(layout: Any, main_width: int) -> int:
    """Defensively extract timeline width from layout result."""
    timeline_width = None
    if isinstance(layout, (tuple, list)) and len(layout) > 2:
        try:
            timeline_width = layout[2]
        except (TypeError, IndexError):
            timeline_width = None
    if timeline_width is None:
        timeline_width = getattr(layout, "timeline_width", None)
    if timeline_width is None:
        timeline_width = max(1, main_width - TIMELINE_LABEL_ESTIMATE_WIDTH)
    try:
        timeline_width = int(timeline_width)
    except (TypeError, ValueError):
        timeline_width = max(1, main_width - TIMELINE_LABEL_ESTIMATE_WIDTH)
    return max(1, timeline_width)
