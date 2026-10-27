"""The only module that opens a network connection (spec 004 research R1, R8)."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Response:
    """An HTTP response: status, headers and raw body."""

    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=lambda: {})


class TransportError(Exception):
    """The request did not get an HTTP response (DNS, TLS, timeout)."""


class HttpTransport(Protocol):
    """Sends one HTTP request and returns its response, whatever its status."""

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
    ) -> Response:
        """Send the request."""
        ...


class UrllibTransport:
    """`HttpTransport` over `urllib.request`. Never logs URLs or bodies: they can carry tokens."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
    ) -> Response:
        """Send the request; a 4xx or 5xx is returned, not raised."""
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return Response(resp.status, resp.read(), dict(resp.headers.items()))
        except urllib.error.HTTPError as err:
            return Response(err.code, err.read(), dict(err.headers.items()))
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise TransportError(type(err).__name__) from None
