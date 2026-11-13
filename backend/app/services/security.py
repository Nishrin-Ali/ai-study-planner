"""Security utilities for safe file operations and SSRF-protected networking."""
import ipaddress
import logging
from pathlib import Path
import socket
from typing import List, Optional, Tuple, Union
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VTUStudentAssistant/1.0"
MAX_DOWNLOAD_SIZE = 25 * 1024 * 1024  # 25MB
DEFAULT_TIMEOUT = 12.0  # seconds

# Blocked hostnames (cloud metadata, internal aliases)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata.awsinternal",
}


class SSRFSecurityError(Exception):
    """Raised when an outbound URL violates SSRF safety boundaries."""
    pass


def is_ip_private_or_reserved(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Return True if IP address is private, loopback, link-local, multicast, or reserved."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    # Check IPv4-mapped IPv6
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return is_ip_private_or_reserved(ip.ipv4_mapped)
    return False


def validate_url_for_ssrf(url: str) -> Tuple[bool, str]:
    """Validate that a URL does not point to internal, private, loopback, or metadata services.

    Returns:
        (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid scheme '{parsed.scheme}': only http and https are permitted."

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False, "URL missing valid hostname."

    if hostname in BLOCKED_HOSTNAMES:
        return False, f"Access to host '{hostname}' is blocked."

    # First test if hostname is a literal IP
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if is_ip_private_or_reserved(ip_obj):
            return False, f"Access to private or reserved IP '{hostname}' is blocked."
    except ValueError:
        # Not a direct IP literal; resolve DNS
        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)
                if is_ip_private_or_reserved(ip_obj):
                    return False, f"Resolved IP '{ip_str}' for host '{hostname}' is private or reserved."
        except socket.gaierror as exc:
            return False, f"DNS resolution failed for '{hostname}': {exc}"
        except Exception as exc:
            return False, f"Error validating host '{hostname}': {exc}"

    return True, ""


async def safe_download_file(
    url: str,
    max_size: int = MAX_DOWNLOAD_SIZE,
    timeout: float = DEFAULT_TIMEOUT
) -> Tuple[Optional[bytes], Optional[str]]:
    """Safely download a file while strictly preventing SSRF and blocking oversized payloads.

    Returns:
        (file_bytes_or_none, error_reason_or_none)
    """
    current_url = url
    max_redirects = 3
    redirect_count = 0

    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        while redirect_count <= max_redirects:
            is_safe, reason = validate_url_for_ssrf(current_url)
            if not is_safe:
                return None, f"SSRF Protection: {reason}"

            try:
                resp = await client.get(current_url, headers=headers)
            except Exception as exc:
                return None, f"Network error downloading {current_url}: {exc}"

            # Handle redirects manually to check SSRF on each hop
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_url = resp.headers.get("Location")
                if not redirect_url:
                    return None, f"Redirect status {resp.status_code} with no Location header."
                # Resolve relative redirects
                from urllib.parse import urljoin
                current_url = urljoin(current_url, redirect_url)
                redirect_count += 1
                continue

            if resp.status_code != 200:
                return None, f"HTTP error {resp.status_code} fetching {current_url}"

            content = resp.content
            if len(content) > max_size:
                return None, f"Payload size ({len(content)} bytes) exceeds maximum limit ({max_size} bytes)."

            return content, None

    return None, "Too many redirects."


async def download_secure_pdf(
    url: str,
    max_size: int = MAX_DOWNLOAD_SIZE,
    timeout: float = DEFAULT_TIMEOUT
) -> bytes:
    """Download PDF bytes strictly with SSRF and size validations.

    Raises SSRFSecurityError if unsafe host/IP is targeted.
    Raises ValueError on download/HTTP error or size violations.
    """
    content, err = await safe_download_file(url, max_size=max_size, timeout=timeout)
    if err:
        if "SSRF Protection" in err:
            raise SSRFSecurityError(err)
        raise ValueError(err)
    if not content:
        raise ValueError("Empty response received from remote server.")
    return content


def is_safe_file_path(
    target_path: Union[str, Path],
    allowed_directories: List[Union[str, Path]]
) -> bool:
    """Check whether target_path strictly resolves inside one of allowed_directories.

    Protects against path traversal attacks (e.g., ../../etc/passwd or Windows equivalent).
    """
    try:
        resolved_target = Path(target_path).resolve()
    except Exception:
        return False

    for allowed in allowed_directories:
        try:
            resolved_allowed = Path(allowed).resolve()
            resolved_target.relative_to(resolved_allowed)
            return True
        except ValueError:
            continue

    return False
