"""Unit tests for host helpers in paraping_v2.hosts."""

from unittest.mock import patch

from paraping_v2.hosts import build_host_infos_v2, parse_host_file_line_v2, read_input_file_v2


class _LoggerStub:
    def __init__(self) -> None:
        self.warnings = []
        self.errors = []

    def warning(self, msg, *args) -> None:
        self.warnings.append(msg % args if args else msg)

    def error(self, msg, *args) -> None:
        self.errors.append(msg % args if args else msg)


def test_parse_host_file_line_v2_parses_valid_entry() -> None:
    logger = _LoggerStub()
    result = parse_host_file_line_v2("192.0.2.1,alias", 1, "hosts.txt", logger)
    assert result == {"host": "192.0.2.1", "alias": "alias", "ip": "192.0.2.1"}
    assert logger.warnings == []


def test_read_input_file_v2_returns_empty_for_missing_file() -> None:
    logger = _LoggerStub()
    result = read_input_file_v2("/tmp/does-not-exist-v2-hosts.txt", logger)
    assert result == []
    assert logger.errors


@patch("socket.getaddrinfo")
def test_build_host_infos_v2_prefers_ipv4(mock_getaddrinfo) -> None:
    logger = _LoggerStub()
    mock_getaddrinfo.return_value = [
        (2, 3, 0, "", ("198.51.100.10", 0)),  # AF_INET
        (10, 3, 0, "", ("2001:db8::10", 0, 0, 0)),  # AF_INET6
    ]
    host_infos, host_map = build_host_infos_v2(["example.com"], logger)
    assert host_infos[0]["ip"] == "198.51.100.10"
    assert "example.com" in host_map
