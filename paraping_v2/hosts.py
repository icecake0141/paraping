"""Host parsing and host-info construction helpers for v2."""

import ipaddress
import socket
from typing import Any, Dict, List, Optional, Union


def parse_host_file_line_v2(
    line: str,
    line_number: int,
    input_file: str,
    logger: Any,
) -> Optional[Dict[str, str]]:
    """Parse a single line from the host input file."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) != 2:
        logger.warning(
            "Invalid host entry at %s:%d. Expected format 'IP,alias'.",
            input_file,
            line_number,
        )
        return None
    ip_text, alias = parts
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
    return {"host": ip_text, "alias": alias, "ip": ip_text}


def read_input_file_v2(input_file: str, logger: Any) -> List[Dict[str, str]]:
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


def build_host_infos_v2(
    hosts: List[Union[str, Dict[str, str]]],
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
        else:
            host_value = entry.get("host") or entry.get("ip")
            if not host_value:
                entry_keys = ", ".join(sorted(entry.keys()))
                detail = f"Received keys: {entry_keys}" if entry_keys else "Received empty entry"
                raise ValueError(f"Invalid host entry: 'host' or 'ip' value must be non-empty. {detail}")
            host = host_value
            alias = entry.get("alias") or host
            ip_address = entry.get("ip")
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
        }
        host_infos.append(info)
        host_map.setdefault(host, []).append(info)
    return host_infos, host_map
