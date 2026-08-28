"""URL helpers for HTTP services used by Information Units."""

from urllib.parse import urlsplit, urlunsplit


def normalise_service_url(raw_url: str | None, default_url: str, default_port: int = 8000) -> str:
    """Return an absolute service URL, adding the container port for bare hosts."""
    candidate = (raw_url or default_url).strip().rstrip("/")
    if not candidate:
        candidate = default_url.rstrip("/")

    if "://" in candidate:
        return candidate

    parsed = urlsplit(f"http://{candidate}")
    if parsed.port is not None:
        return urlunsplit(parsed)

    hostname = parsed.hostname or candidate
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = f"{hostname}:{default_port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))