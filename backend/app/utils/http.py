"""HTTP client utilities with optional SOCKS proxy."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("finkg.http")


def get_proxies() -> dict[str, str] | None:
    """Returns SOCKS5 proxy dict if FINKG_USE_PROXY=true."""
    if os.getenv("FINKG_USE_PROXY", "").lower() != "true":
        return None
    host = os.getenv("SOCKS_PROXY_HOST", "127.0.0.1").strip()
    port = os.getenv("SOCKS_PROXY_PORT", "9674").strip()
    if host and port:
        proxy_url = f"socks5://{host}:{port}"
        return {"http": proxy_url, "https": proxy_url}
    return None


def create_session() -> "requests.Session":
    """Create a requests Session with appropriate headers and optional proxy."""
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    proxies = get_proxies()
    if proxies:
        session.proxies.update(proxies)
    return session
