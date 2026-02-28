"""Unit tests for terminal-size helpers in paraping_v2.term_size."""

from paraping_v2.term_size import extract_timeline_width_from_layout_v2, normalize_term_size_v2


def test_normalize_term_size_v2_accepts_tuple_and_dict() -> None:
    tuple_result = normalize_term_size_v2((80, 24))
    dict_result = normalize_term_size_v2({"columns": "100", "lines": "40"})
    assert tuple_result is not None
    assert tuple_result.columns == 80
    assert tuple_result.lines == 24
    assert dict_result is not None
    assert dict_result.columns == 100
    assert dict_result.lines == 40


def test_extract_timeline_width_from_layout_v2_fallbacks() -> None:
    assert extract_timeline_width_from_layout_v2((0, 0, 55, 0), 80) == 55

    class _Layout:
        timeline_width = 44

    assert extract_timeline_width_from_layout_v2(_Layout(), 80) == 44
    assert extract_timeline_width_from_layout_v2(object(), 20) >= 1
