import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings

BLOCKED_FILE_NAMES = {".env", "credentials.json", "id_rsa", "id_dsa"}


def ensure_safe_path(path_value: str, root: Path | None = None) -> Path:
    settings = get_settings()
    base = (root or settings.manus_workspace_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    candidate = (base / path_value).resolve()
    if base != candidate and base not in candidate.parents:
        raise ValueError("Path escapes the allowed workspace")
    if any(part in BLOCKED_FILE_NAMES for part in candidate.parts):
        raise ValueError("Access to sensitive files is blocked")
    return candidate


def safe_output_path(file_name: str, root: Path | None = None) -> Path:
    clean_name = Path(file_name).name.strip() or "output.txt"
    return ensure_safe_path(clean_name, root or get_settings().manus_output_dir)


def ensure_safe_url(url: str) -> str:
    settings = get_settings()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL hostname is required")
    if not settings.manus_allow_private_urls:
        try:
            addresses = socket.getaddrinfo(parsed.hostname, None)
            for address in addresses:
                ip = ipaddress.ip_address(address[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                    raise ValueError("Private, loopback, link-local, and multicast URLs are blocked")
        except socket.gaierror as exc:
            raise ValueError("URL hostname cannot be resolved") from exc
    return url
