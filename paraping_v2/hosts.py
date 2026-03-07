"""Host parsing and host-info construction helpers for v2."""

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class HostInputIssue:
    """One parse issue discovered while reading a host input file."""

    line_number: int
    raw_line: str
    reason: str
    severity: str = "error"


@dataclass(frozen=True)
class HostInputReport:
    """Structured parse diagnostics for host input file loading."""

    issues: List[HostInputIssue]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0


def _is_header_row(parts: List[str]) -> bool:
    """Return True when parsed columns look like a CSV header row."""
    lowered = [part.strip().lower() for part in parts]
    if len(lowered) == 2:
        return lowered[0] in {"host", "ip"} and lowered[1] in {"alias", "name"}
    if len(lowered) == 4:
        return (
            lowered[0] in {"host", "ip"} and lowered[1] in {"alias", "name"} and lowered[2] == "site" and lowered[3] == "tags"
        )
    return False


def parse_host_file_line_v2(
    line: str,
    line_number: int,
    input_file: str,
    logger: Any,
) -> Optional[Dict[str, Any]]:
    """Parse a single line from the host input file."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) not in (2, 4):
        logger.warning(
            "Invalid host entry at %s:%d. Expected format 'IP,alias' or 'IP,alias,site,tags'.",
            input_file,
            line_number,
        )
        return None
    if _is_header_row(parts):
        return None
    ip_text, alias = parts[0], parts[1]
    site = parts[2] if len(parts) == 4 else ""
    tags_value = parts[3] if len(parts) == 4 else ""
    if not ip_text or not alias:
        logger.warning(
            "Invalid host entry at %s:%d. IP address and alias are required.",
            input_file,
            line_number,
        )
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        logger.warning(
            "Invalid IP address at %s:%d: '%s'.",
            input_file,
            line_number,
            ip_text,
        )
        return None
    if ip_obj.version != 4:
        logger.warning(
            "IPv6 address at %s:%d: '%s'. IPv6 is not supported by ping_helper; this entry will likely fail during ping.",
            input_file,
            line_number,
            ip_text,
        )
    entry: Dict[str, Any] = {"host": ip_text, "alias": alias, "ip": ip_text}
    if len(parts) == 4:
        entry["site"] = site
        entry["tags"] = [tag.strip() for tag in tags_value.split(";") if tag.strip()]
    return entry


def read_input_file_v2(input_file: str, logger: Any) -> List[Dict[str, Any]]:
    """Read and parse hosts from an input file."""
    host_list = []
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                entry = parse_host_file_line_v2(line, line_number, input_file, logger)
                if entry is not None:
                    host_list.append(entry)
    except FileNotFoundError:
        logger.error("Input file '%s' not found.", input_file)
        return []
    except PermissionError:
        logger.error("Permission denied reading file '%s'.", input_file)
        return []
    except (OSError, UnicodeDecodeError) as e:
        logger.error("Error reading input file '%s': %s", input_file, e)
        return []

    return host_list


def _parse_host_file_line_with_issue(
    line: str,
    line_number: int,
    input_file: str,
    logger: Any,
) -> tuple[Optional[Dict[str, Any]], Optional[HostInputIssue]]:
    """Parse one line and optionally return a structured issue."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None, None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) not in (2, 4):
        reason = "Expected format 'IP,alias' or 'IP,alias,site,tags'."
        logger.warning("Invalid host entry at %s:%d. %s", input_file, line_number, reason)
        return None, HostInputIssue(line_number=line_number, raw_line=stripped, reason=reason, severity="error")
    if _is_header_row(parts):
        return None, None
    ip_text, alias = parts[0], parts[1]
    site = parts[2] if len(parts) == 4 else ""
    tags_value = parts[3] if len(parts) == 4 else ""
    if not ip_text or not alias:
        reason = "IP address and alias are required."
        logger.warning("Invalid host entry at %s:%d. %s", input_file, line_number, reason)
        return None, HostInputIssue(line_number=line_number, raw_line=stripped, reason=reason, severity="error")
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        reason = f"Invalid IP address '{ip_text}'."
        logger.warning("Invalid IP address at %s:%d: '%s'.", input_file, line_number, ip_text)
        return None, HostInputIssue(line_number=line_number, raw_line=stripped, reason=reason, severity="error")

    entry: Dict[str, Any] = {"host": ip_text, "alias": alias, "ip": ip_text}
    if len(parts) == 4:
        entry["site"] = site
        entry["tags"] = [tag.strip() for tag in tags_value.split(";") if tag.strip()]

    if ip_obj.version != 4:
        logger.warning(
            "IPv6 address at %s:%d: '%s'. IPv6 is not supported by ping_helper; this entry will likely fail during ping.",
            input_file,
            line_number,
            ip_text,
        )
    return entry, None


def read_input_file_with_report_v2(input_file: str, logger: Any) -> tuple[List[Dict[str, Any]], HostInputReport]:
    """Read hosts from file and include structured parse diagnostics."""
    host_list: List[Dict[str, Any]] = []
    issues: List[HostInputIssue] = []
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                entry, issue = _parse_host_file_line_with_issue(line, line_number, input_file, logger)
                if entry is not None:
                    host_list.append(entry)
                if issue is not None:
                    issues.append(issue)
    except FileNotFoundError:
        logger.error("Input file '%s' not found.", input_file)
        issues.append(
            HostInputIssue(
                line_number=0,
                raw_line="",
                reason=f"Input file '{input_file}' not found.",
                severity="error",
            )
        )
    except PermissionError:
        logger.error("Permission denied reading file '%s'.", input_file)
        issues.append(
            HostInputIssue(
                line_number=0,
                raw_line="",
                reason=f"Permission denied reading file '{input_file}'.",
                severity="error",
            )
        )
    except (OSError, UnicodeDecodeError) as e:
        logger.error("Error reading input file '%s': %s", input_file, e)
        issues.append(
            HostInputIssue(
                line_number=0,
                raw_line="",
                reason=f"Error reading input file '{input_file}': {e}",
                severity="error",
            )
        )

    return host_list, HostInputReport(issues=issues)


def build_host_infos_v2(
    hosts: List[Union[str, Dict[str, Any]]],
    logger: Any,
) -> tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Build host information structures from a list of hosts."""
    host_infos = []
    host_map: Dict[str, List[Dict[str, Any]]] = {}

    def address_from_sockaddr(sockaddr: tuple[Any, ...]) -> str:
        """Extract a string address from a getaddrinfo sockaddr tuple."""
        address_value = sockaddr[0]
        if isinstance(address_value, str):
            return address_value
        return str(address_value)

    for index, entry in enumerate(hosts):
        if isinstance(entry, str):
            host = entry
            alias = entry
            ip_address: Optional[str] = None
            site: Optional[str] = None
            tags: List[str] = []
        else:
            host_value = entry.get("host") or entry.get("ip")
            if not host_value:
                entry_keys = ", ".join(sorted(entry.keys()))
                detail = f"Received keys: {entry_keys}" if entry_keys else "Received empty entry"
                raise ValueError(f"Invalid host entry: 'host' or 'ip' value must be non-empty. {detail}")
            host = host_value
            alias = entry.get("alias") or host
            ip_address = entry.get("ip")
            site = str(entry.get("site") or "").strip() or None
            raw_tags = entry.get("tags", [])
            if isinstance(raw_tags, str):
                tags = [tag.strip() for tag in raw_tags.split(";") if tag.strip()]
            elif isinstance(raw_tags, list):
                tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
            else:
                tags = []
        if not ip_address:
            try:
                addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_RAW)

                ipv4_addresses = []
                ipv6_addresses = []
                for family, _socktype, _proto, _canonname, sockaddr in addr_info:
                    if family == socket.AF_INET:
                        ipv4_addresses.append(address_from_sockaddr(sockaddr))
                    elif family == socket.AF_INET6:
                        ipv6_addresses.append(address_from_sockaddr(sockaddr))

                if ipv4_addresses:
                    ip_address = ipv4_addresses[0]
                elif ipv6_addresses:
                    ip_address = ipv6_addresses[0]
                    logger.warning(
                        "Host '%s' resolved to IPv6 address '%s'. IPv6 is not supported by ping_helper; "
                        "pinging will likely fail.",
                        host,
                        ip_address,
                    )
                else:
                    ip_address = host
            except (socket.gaierror, OSError):
                ip_address = host
        info = {
            "id": index,
            "host": host,
            "alias": alias,
            "ip": ip_address,
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
            "site": site,
            "tags": tags,
        }
        host_infos.append(info)
        host_map.setdefault(host, []).append(info)
    return host_infos, host_map
