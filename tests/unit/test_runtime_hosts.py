"""Unit tests for host helpers in paraping.runtime.hosts."""

from unittest.mock import patch

from paraping.runtime.hosts import (
    HostInputReport,
    build_host_infos,
    parse_host_file_line,
    read_input_file,
    read_input_file_with_report,
)


class _LoggerStub:
    def __init__(self) -> None:
        self.warnings = []
        self.errors = []

    def warning(self, msg, *args) -> None:
        self.warnings.append(msg % args if args else msg)

    def error(self, msg, *args) -> None:
        self.errors.append(msg % args if args else msg)


def test_parse_host_file_line_parses_valid_entry() -> None:
    logger = _LoggerStub()
    result = parse_host_file_line("192.0.2.1,alias", 1, "hosts.txt", logger)
    assert result == {"host": "192.0.2.1", "alias": "alias", "ip": "192.0.2.1"}
    assert logger.warnings == []


def test_read_input_file_returns_empty_for_missing_file() -> None:
    logger = _LoggerStub()
    result = read_input_file("/tmp/does-not-exist-runtime-hosts.txt", logger)
    assert result == []
    assert logger.errors


def test_parse_host_file_line_parses_extended_entry() -> None:
    logger = _LoggerStub()
    result = parse_host_file_line("192.0.2.2,alias-a,Tokyo,core;prod", 1, "hosts.txt", logger)
    assert result is not None
    assert result["site"] == "Tokyo"
    assert result["tags"] == ["core", "prod"]


def test_parse_host_file_line_skips_header_row() -> None:
    logger = _LoggerStub()
    result = parse_host_file_line("host,alias,site,tags", 1, "hosts.txt", logger)
    assert result is None


def test_read_input_file_with_report_collects_format_errors() -> None:
    logger = _LoggerStub()
    with patch(
        "builtins.open",
        create=True,
    ) as mock_open_fn:
        mock_open_fn.return_value.__enter__.return_value = iter(
            [
                "192.0.2.10,ok-a\n",
                "bad line\n",
                "192.0.2.11,\n",
                "999.999.999.999,bad-ip\n",
                "192.0.2.12,ok-b\n",
            ]
        )
        entries, report = read_input_file_with_report("hosts.txt", logger)

    assert len(entries) == 2
    assert isinstance(report, HostInputReport)
    assert report.has_errors is True
    assert report.error_count == 3
    assert report.warning_count == 0
    assert [issue.line_number for issue in report.issues] == [2, 3, 4]
    assert report.issues[0].raw_line == "bad line"
    assert "Expected format" in report.issues[0].reason


@patch("socket.getaddrinfo")
def test_build_host_infos_prefers_ipv4(mock_getaddrinfo) -> None:
    logger = _LoggerStub()
    mock_getaddrinfo.return_value = [
        (2, 3, 0, "", ("198.51.100.10", 0)),  # AF_INET
        (10, 3, 0, "", ("2001:db8::10", 0, 0, 0)),  # AF_INET6
    ]
    host_infos, host_map = build_host_infos(["example.com"], logger)
    assert host_infos[0]["ip"] == "198.51.100.10"
    assert "example.com" in host_map
