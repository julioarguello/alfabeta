import threading
import urllib.parse
import urllib.request
from collections.abc import Callable

import pytest

from alfabeta.google import oauth
from tests.conftest import STUDENT_ADDRESS, FakeTransport, id_token, json_response

CLIENT = oauth.Client("id-inventado", "secreto-inventado")
SCOPES = ("https://www.googleapis.com/auth/calendar.events", "openid", "email")


def test_authorisation_url_has_pkce_offline_consent_and_no_login_hint():
    url = oauth.authorisation_url(CLIENT, "http://127.0.0.1:5555", SCOPES, "reto", "estado")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == ["reto"]
    assert query["state"] == ["estado"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["scope"] == [" ".join(SCOPES)]
    assert "login_hint" not in query
    assert "@" not in url


def test_email_from_id_token():
    assert oauth.email_from_id_token(id_token(STUDENT_ADDRESS)) == STUDENT_ADDRESS
    assert oauth.email_from_id_token("no-es-un-token") is None


def test_exchange_reads_scopes_and_email():
    t = FakeTransport(
        [
            json_response(
                200,
                {
                    "refresh_token": "r",
                    "access_token": "a",
                    "scope": "openid email",
                    "id_token": id_token(STUDENT_ADDRESS),
                },
            )
        ]
    )
    grant = oauth.exchange_code(t, CLIENT, "codigo", "verificador", "http://127.0.0.1:1")
    assert grant.email == STUDENT_ADDRESS
    assert grant.scopes == {"openid", "email"}
    body = urllib.parse.parse_qs((t.calls[0][3] or b"").decode())
    assert body["code_verifier"] == ["verificador"] and body["grant_type"] == ["authorization_code"]


def test_exchange_without_refresh_token_is_denied():
    t = FakeTransport([json_response(200, {"access_token": "a"})])
    with pytest.raises(oauth.OAuthError) as err:
        oauth.exchange_code(t, CLIENT, "c", "v", "http://127.0.0.1:1")
    assert err.value.reason == "denied"


@pytest.mark.parametrize(
    ("description", "reason"),
    [
        ("Token has been expired or revoked.", "expired"),
        ("Token has been revoked.", "revoked"),
        ("Bad Request", "expired"),
    ],
)
def test_refresh_invalid_grant(description: str, reason: str):
    t = FakeTransport([json_response(400, {"error": "invalid_grant", "error_description": description})])
    with pytest.raises(oauth.OAuthError) as err:
        oauth.refresh_access_token(t, CLIENT, "r")
    assert err.value.reason == reason


def test_refresh_ok():
    t = FakeTransport([json_response(200, {"access_token": "nuevo"})])
    assert oauth.refresh_access_token(t, CLIENT, "r") == "nuevo"


def _visit(redirect_query: dict[str, str]) -> Callable[[str], None]:
    """A fake browser: follows the authorisation URL's redirect_uri with the given query."""

    def open_browser(url: str) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        params = dict(redirect_query)
        if params.get("state") == "<same>":
            params["state"] = query["state"][0]
        target = f"{query['redirect_uri'][0]}/?{urllib.parse.urlencode(params)}"

        def visit() -> None:
            with urllib.request.urlopen(target, timeout=5) as resp:
                resp.read()

        threading.Thread(target=visit, daemon=True).start()

    return open_browser


def test_receive_code_happy_path():
    code, verifier, redirect = oauth.receive_code(_visit({"code": "abc", "state": "<same>"}), CLIENT, SCOPES, timeout=5)
    assert code == "abc" and verifier and redirect.startswith("http://127.0.0.1:")


def test_receive_code_rejects_a_wrong_state():
    with pytest.raises(oauth.OAuthError) as err:
        oauth.receive_code(_visit({"code": "abc", "state": "otro"}), CLIENT, SCOPES, timeout=5)
    assert err.value.reason == "bad_state"


def test_receive_code_access_denied():
    with pytest.raises(oauth.OAuthError) as err:
        oauth.receive_code(_visit({"error": "access_denied", "state": "<same>"}), CLIENT, SCOPES, timeout=5)
    assert err.value.reason == "denied"
