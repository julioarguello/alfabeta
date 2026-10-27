"""Google sign-in for an installed app: loopback redirect with PKCE (spec 004 research R2).

No `login_hint` is ever sent: it would put the account's address in a URL (constitution III).
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from alfabeta.google.transport import HttpTransport

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Google reports these short scopes with their long names in a token response.
_SCOPE_ALIASES = {"email": "https://www.googleapis.com/auth/userinfo.email"}


class OAuthError(Exception):
    """Google refused the request; `reason` is a stable code for the CLI."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Client:
    """The app's Desktop OAuth client."""

    client_id: str
    client_secret: str


@dataclass(frozen=True)
class Grant:
    """What a code exchange returns."""

    refresh_token: str
    access_token: str
    scopes: frozenset[str]
    email: str | None


def normalise_scopes(scopes: list[str] | tuple[str, ...] | frozenset[str]) -> frozenset[str]:
    """Scopes as Google reports them in a token response."""
    return frozenset(_SCOPE_ALIASES.get(scope, scope) for scope in scopes)


def pkce_pair() -> tuple[str, str]:
    """A PKCE verifier and its S256 challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def authorisation_url(client: Client, redirect_uri: str, scopes: tuple[str, ...], challenge: str, state: str) -> str:
    """Google's authorisation URL for this request; it never names the account."""
    query = {
        "client_id": client.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(query)}"


def email_from_id_token(id_token: str) -> str | None:
    """The `email` claim of an id_token.

    The token comes straight from Google's token endpoint over TLS, so its signature need not be
    checked (Google's OpenID Connect guide says so for tokens obtained that way).
    """
    try:
        payload = id_token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        claims = cast("dict[str, Any]", json.loads(base64.urlsafe_b64decode(padded)))
    except (IndexError, ValueError):
        return None
    email = claims.get("email")
    return email if isinstance(email, str) else None


def _post_form(transport: HttpTransport, url: str, form: dict[str, str]) -> tuple[int, dict[str, Any]]:
    body = urllib.parse.urlencode(form).encode()
    resp = transport.request("POST", url, headers={"Content-Type": "application/x-www-form-urlencoded"}, body=body)
    try:
        data = cast("dict[str, Any]", json.loads(resp.body or b"{}"))
    except ValueError:
        data = {}
    return resp.status, data


def exchange_code(transport: HttpTransport, client: Client, code: str, verifier: str, redirect_uri: str) -> Grant:
    """Exchange an authorisation code for tokens."""
    status, data = _post_form(
        transport,
        TOKEN_URL,
        {
            "code": code,
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    if status != 200 or "refresh_token" not in data:
        raise OAuthError("denied")
    id_token = data.get("id_token")
    return Grant(
        refresh_token=str(data["refresh_token"]),
        access_token=str(data.get("access_token", "")),
        scopes=frozenset(str(data.get("scope", "")).split()),
        email=email_from_id_token(id_token) if isinstance(id_token, str) else None,
    )


def refresh_access_token(transport: HttpTransport, client: Client, refresh_token: str) -> str:
    """A fresh access token, or OAuthError with reason `expired` or `revoked`."""
    status, data = _post_form(
        transport,
        TOKEN_URL,
        {
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    if status == 200 and "access_token" in data:
        return str(data["access_token"])
    if data.get("error") == "invalid_grant":
        description = str(data.get("error_description", "")).lower()
        raise OAuthError("revoked" if "revoked" in description and "expired" not in description else "expired")
    raise OAuthError(f"http_{status}")


def revoke(transport: HttpTransport, token: str) -> None:
    """Revoke a token at Google; an already-invalid token is fine."""
    _post_form(transport, REVOKE_URL, {"token": token})


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: dict[str, str]
    done: threading.Event

    def do_GET(self) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in query or "error" in query:
            self.result.update({key: values[0] for key, values in query.items()})
            self.done.set()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<p>alfabeta: puedes cerrar esta pestaña.</p>".encode())

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default log: the request line carries the code."""


def receive_code(
    open_browser: Any, client: Client, scopes: tuple[str, ...], timeout: float = 900.0
) -> tuple[str, str, str]:
    """Open Google's sign-in and wait for the redirect. Returns (code, verifier, redirect_uri).

    The wait allows 15 minutes: a supervised account needs a parent to approve the sign-in first.
    """
    done = threading.Event()
    result: dict[str, str] = {}
    handler = type("Handler", (_CallbackHandler,), {"result": result, "done": done})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    redirect_uri = f"http://127.0.0.1:{server.server_address[1]}"
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(24)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        open_browser(authorisation_url(client, redirect_uri, scopes, challenge, state))
        if not done.wait(timeout):
            raise OAuthError("timeout")
    finally:
        server.shutdown()
        server.server_close()
    if result.get("state") != state:
        raise OAuthError("bad_state")
    if "error" in result or "code" not in result:
        raise OAuthError("denied")
    return result["code"], verifier, redirect_uri
