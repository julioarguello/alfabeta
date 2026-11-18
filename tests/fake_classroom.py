"""A local fake of Google's sign-in and of Classroom, for `docker/classroom/read.py` (spec 006 T004).

Never Google: one `ThreadingHTTPServer` on 127.0.0.1 serves invented sign-in pages and the
synthetic Classroom pages of `tests/fixtures/classroom/pages` (with their `<base>` removed, so no
link resolves to the real Classroom). The mode chooses what the sign-in answers.

Modes: `ok`, `readonly` (the password field cannot be filled), `redirect` (an allowed page
redirects outside), `captcha` (an image captcha after the account), `rejected`, `second_factor`,
`other_sign_in` (the account's own sign-in elsewhere), `other_account` (Classroom shows another
account), `expire_mid` (the third class's pages leave for another origin, as an expired session
does). A stale cookie `fakestale` sends the identifier page to an account chooser, so the test can
prove the read clears the cookies first. Class `synth-73` is unreadable (`unexpected_ui`).
"""

from __future__ import annotations

import http.server
import re
import threading
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

PAGES = Path(__file__).parent / "fixtures" / "classroom" / "pages"
ACCOUNT = "alumno@example.test"
OTHER = "otro@example.test"
PASSWORD = "contraseña-inventada-123"
UNREADABLE = "synth-73"
EXPIRING = "synth-74"

IDENTIFIER = """<html><body><h1>Inicia sesión</h1>
<form onsubmit="event.preventDefault(); location.href = NEXT;"><input type=email id=identifierId></form>
<script>const NEXT = {next!r};</script></body></html>"""
PASSWORD_PAGE = """<html><body><h1>Te damos la bienvenida</h1>{error}
<form onsubmit="event.preventDefault(); location.href = '/v3/signin/check?p=' + encodeURIComponent(document.querySelector('input').value);">
<input type=password name=Passwd {readonly}></form></body></html>"""
CAPTCHA = """<html><body><h1>Inicia sesión</h1><input type=email id=identifierId>
<img id=captchaimg src="/captcha.png"><p>Escribe el texto que escuches o veas</p></body></html>"""
GENERIC = "<html><body><h1>{title}</h1></body></html>"
# Planted on the home page: a press, a form submit, a form host and a page outside FR-007's pages.
PLANTED = """<button id=planted>x</button><form id=plantedform></form>
<img src="http://forms.invalid/planted"><iframe src="/u/5/outside"></iframe><iframe src="{other}/third-party"></iframe>
<a href="http://forms.invalid/quiz">quiz</a>{redirect}
<div aria-label="Cuenta de Google: Persona Inventada ({email})"></div>
<script>window.addEventListener('load', () => {{ document.getElementById('planted').click();
document.getElementById('plantedform').submit(); }});</script>"""
ROUTES = [
    (r"^/u/5/w/[^/]+/t/all$", "classwork.html"),
    (r"^/u/5/c/[^/]+/a/[^/]+/details$", "assignment-detail.html"),
    (r"^/u/5/c/[^/]+/m/[^/]+/details$", "material-detail.html"),
    (r"^/u/5/c/[^/]+/mc/[^/]+/details$", "question-detail.html"),
    (r"^/u/5/c/[^/]+$", "stream.html"),
]


def _page(name: str) -> bytes:
    return re.sub(rb"<base [^>]*>", b"", (PAGES / name).read_bytes())


class FakeGoogle(http.server.ThreadingHTTPServer):
    """The server, its mode, and what it saw (typed passwords are never kept)."""

    daemon_threads = True

    def __init__(self, mode: str) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.mode = mode
        self.password_attempts = 0
        self.served: list[str] = []
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"

    @property
    def other_origin(self) -> str:
        return f"http://localhost:{self.server_address[1]}"

    def __enter__(self) -> FakeGoogle:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.shutdown()
        self.server_close()


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    @property
    def fake(self) -> FakeGoogle:
        return cast("FakeGoogle", self.server)

    def _send(self, body: str | bytes, code: int = 200, location: str | None = None, cookie: str | None = None) -> None:
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def _signed_in(self) -> bool:
        return "fakesid=ok" in (self.headers.get("Cookie") or "")

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        mode = self.fake.mode
        self.fake.served.append(url.path)
        if url.path == "/v3/signin/identifier":
            if "fakestale=1" in (self.headers.get("Cookie") or ""):
                return self._send("", 302, "/v3/signin/accountchooser")
            nxt = {
                "captcha": "/v3/signin/identifier/captcha",
                "rejected": "/signin/rejected",
                "other_sign_in": f"{self.fake.other_origin}/school-sign-in",
            }.get(mode, "/v3/signin/challenge/pwd")
            return self._send(IDENTIFIER.format(next=nxt))
        if url.path == "/v3/signin/identifier/captcha":
            return self._send(CAPTCHA)
        if url.path == "/v3/signin/challenge/pwd":
            return self._send(PASSWORD_PAGE.format(error="", readonly="readonly" if mode == "readonly" else ""))
        if url.path == "/v3/signin/check":
            self.fake.password_attempts += 1
            if parse_qs(url.query).get("p", [""])[0] != PASSWORD:
                return self._send(PASSWORD_PAGE.format(error="<p>Contraseña incorrecta</p>", readonly=""))
            if mode == "second_factor":
                return self._send("", 302, "/v3/signin/challenge/totp")
            return self._send("", 302, "/u/5/h", cookie="fakesid=ok; Path=/; Max-Age=3600")
        if url.path.startswith(("/v3/", "/signin/")):
            return self._send(GENERIC.format(title="Página de Google"))
        if url.path == "/u/5/h":
            if not self._signed_in():
                return self._send("", 302, "/v3/signin/identifier")
            email = OTHER if mode == "other_account" else ACCOUNT
            redirect = '<iframe src="/u/5/c/redirme"></iframe>' if mode == "redirect" else ""
            planted = PLANTED.format(email=email, other=self.fake.other_origin, redirect=redirect)
            home = _page("home.html").replace(b"</body>", planted.encode() + b"</body>", 1)
            return self._send(home)
        if url.path == "/u/5/c/redirme":
            return self._send("", 302, "/u/5/outside")
        if url.path == "/u/5/outside":
            return self._send(GENERIC.format(title="fuera"))
        if not self._signed_in():
            return self._send("", 302, "/v3/signin/identifier")
        if UNREADABLE in url.path:
            # Ready for the extractor (a row), but without «Trabajo de clase»: unexpected_ui at once.
            return self._send(
                '<html><body><ul><li data-stream-item-type="1" data-stream-item-id="1"></li></ul></body></html>'
            )
        if mode == "expire_mid" and EXPIRING in url.path:
            return self._send("", 302, f"{self.fake.other_origin}/v3/signin/identifier")
        for pattern, name in ROUTES:
            if re.match(pattern, url.path):
                return self._send(_page(name))
        return self._send("no", 404)
