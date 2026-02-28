"""History navigation page-step helpers for v2."""

from typing import Any, Dict, List, Optional, Protocol, Tuple

import paraping.ui_render
from paraping.ui_render import (
    build_display_entries,
    build_display_names,
    compute_main_layout,
    compute_panel_sizes,
    should_show_asn,
)
from paraping_v2.term_size import extract_timeline_width_from_layout_v2, normalize_term_size_v2


class TerminalSizeLike(Protocol):
    """Protocol for terminal size objects with columns/lines attributes."""

    @property
    def columns(self) -> int: ...

    @property
    def lines(self) -> int: ...


def compute_history_page_step_v2(
    host_infos: List[Dict[str, Any]],
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
    asn_width: int = 8,
    header_lines: int = 2,
) -> int:
    """Compute page step for history navigation from current layout."""
    term_size = paraping.ui_render.get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(term_width, panel_height, panel_position)
    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]

    layout_result = compute_main_layout(host_labels, main_width, main_height, header_lines)
    return extract_timeline_width_from_layout_v2(layout_result, main_width)


def get_cached_page_step_v2(
    cached_page_step: Optional[int],
    last_term_size: Optional[TerminalSizeLike],
    host_infos: List[Dict[str, Any]],
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
) -> Tuple[int, int, Optional[TerminalSizeLike]]:
    """Get page step with terminal-size based caching."""

    def should_recalculate_page_step(last_size: Optional[TerminalSizeLike], current_size: TerminalSizeLike) -> bool:
        if last_size is None:
            return True
        normalized_last = normalize_term_size_v2(last_size)
        if normalized_last is None:
            return True
        if current_size.columns != normalized_last.columns:
            return True
        if current_size.lines != normalized_last.lines:
            return True
        return False

    current_term_size = paraping.ui_render.get_terminal_size(fallback=(80, 24))
    if cached_page_step is None or should_recalculate_page_step(last_term_size, current_term_size):
        page_step = compute_history_page_step_v2(
            host_infos,
            buffers,
            stats,
            symbols,
            panel_position,
            mode_label,
            sort_mode,
            filter_mode,
            slow_threshold,
            show_asn,
        )
        return page_step, page_step, current_term_size

    return cached_page_step, cached_page_step, last_term_size
