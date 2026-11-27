"""A local fake of Google's sign-in and of Classroom, for `docker/classroom/read.py` (spec 006 T004).

Never Google: one `ThreadingHTTPServer` on 127.0.0.1 serves invented sign-in pages and the
synthetic Classroom pages of `tests/fixtures/classroom/pages` (with their `<base>` removed, so no
link resolves to the real Classroom). The mode chooses what the sign-in answers.

Modes: `ok`, `readonly` (the password field cannot be filled), `redirect` (an allowed page
redirects outside), `captcha` (an image captcha after the account), `rejected`, `second_factor`,
`other_sign_in` (the account's own sign-in elsewhere), `other_account` (Classroom shows another
account), `no_account` (Classroom names no account), `slow_list` (the class cards appear 1.5 s
after the page, as right after a sign-in), `expire_mid` (the third class's pages leave for another origin, as an expired session
does), `long_stream` (the stream loads older posts on scroll, see LONG_STREAM), `boxed_stream` (on its inner box's scroll, see BOXED_STREAM), `more` (a topic of «Trabajo de clase» shows «Ver más publicaciones», see MORE_TOPIC). A stale cookie `fakestale` sends the identifier page to an account chooser, so the test can
prove the read clears the cookies first. Class `synth-73` is unreadable (`unexpected_ui`).

Attachments (R4's routes, served for any mode at `other_origin`, so the download host is not the
sign-in's): `/download?id=<id>&export=download` and `/document/d/<id>/export`. Without a session
cookie of their own they redirect to `origin`'s `/ServiceLogin`, as Google's export did (spike S10c,
2026-11-24): with `origin`'s session it redirects back through `/accounts/SetOSID`, which sets
`other_origin`'s cookie and returns to the file; without it, or in mode `sso_refused`, it serves the
sign-in page. `doc-1`'s export answers 307 to `/content/doc-1`, as Google's to its content host. By id: `f-pdf` a PDF, `f-hop` a redirect to
`f-pdf` on the same host, `f-away` a redirect to another host, `f-html` an HTML page, `f-gone` 404,
`f-signin` a redirect straight to the sign-in's identifier page, `f-userinfo` one to `/ServiceLogin` with a
user in the address, `f-gzip` the PDF compressed (its Content-Length the packed size), `f-scheme` a redirect to `https` on
the same host, `f-nolen` the PDF with no Content-Length.
"""

from __future__ import annotations

import base64
import gzip
import http.server
import json
import re
import threading
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, quote, urlsplit

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
<img src="http://forms.invalid/planted"><iframe src="/u/5/outside"></iframe><iframe src="http://third.invalid/frame"></iframe>
<a href="http://forms.invalid/quiz">quiz</a>{redirect}
<div aria-label="Cuenta de Google: Persona Inventada ({email})"></div>
<script>window.addEventListener('load', () => {{ document.getElementById('planted').click();
document.getElementById('plantedform').submit(); }});</script>"""
# Mode `more`: «Trabajo de clase» gains a topic of 10 rows that shows «Ver más publicaciones», as
# Classroom's did (spec 006 research S17); a press adds its last 2 rows and hides the button. The page
# also presses a button of its own there, which the guard still cancels.
MORE_TOPIC = (
    '<div role="region" data-topic-id="t-more"><h2>Tema largo</h2><ol id="more-list">{rows}</ol>'
    '<div class="Mvr5Ef"><div id="more-box" style=""><div><button id="more" jsname="t6Kl7b" '
    'aria-label="Ver más publicaciones"><span aria-hidden="true">Ver más</span></button></div></div></div></div>'
    '<button id="other-press">x</button>'
    "<script>document.getElementById('more').addEventListener('click', () => setTimeout(() => {{"
    "document.getElementById('more-list').insertAdjacentHTML('beforeend', {late});"
    "document.getElementById('more-box').setAttribute('style', 'display: none;'); }}, 200));"
    "document.getElementById('other-press').addEventListener('click', () => document.getElementById('more-list')"
    '.insertAdjacentHTML(\'beforeend\', \'<li data-stream-item-type="5" data-stream-item-id="9398">'
    '<span class="Vu2fZd">Si se ve, el guard falló</span></li>\'));'
    "window.addEventListener('load', () => document.getElementById('other-press').click());</script>"
)
# The saved page has a topic of 10 that shows «Ver más publicaciones» (2026-10-25), but not the items
# a press brought: here a press brings one invented row and hides the button, as Classroom did.
ANSWER_MORE = (
    "<script>for (const b of document.querySelectorAll('button[jsname=\"t6Kl7b\"]:not(#more)')) "
    "b.addEventListener('click', () => setTimeout(() => { const box = b.parentElement.parentElement; "
    "box.closest('[data-topic-id][role=region]').querySelector('ol').insertAdjacentHTML('beforeend', "
    '\'<li data-stream-item-type="5" data-stream-item-id="9399"><span class="Vu2fZd">Material 9399</span></li>\'); '
    "box.setAttribute('style', 'display: none;'); }, 100));</script>"
)
# Mode `long_stream`: the stream gains 3 posts and, each time it is scrolled near its bottom, 4 older
# ones, twice, as Classroom's did (spec 006 research S17, #293).
STREAM_POST = (
    '<div data-stream-item-id="{n}"><h2>Autor inventado</h2><div class="pco8Kc">Anuncio antiguo {n}</div>'
    "<div>Fecha de creación: 3 sept</div></div>"
)
LONG_STREAM = (
    '<div id="older">{posts}</div><div style="height: 3000px"></div>'
    "<script>let loads = 0, busy = false; const post = (n) => '<div data-stream-item-id=\"' + n + '\"><h2>Autor "
    "inventado</h2><div class=\"pco8Kc\">Anuncio antiguo ' + n + '</div><div>Fecha de creación: 3 sept</div></div>';"
    "window.addEventListener('scroll', () => {{ if (busy || loads >= 2) return;"
    " if (window.scrollY + window.innerHeight < document.documentElement.scrollHeight - 200) return;"
    " busy = true; setTimeout(() => {{ const first = 8203 + 4 * loads; loads += 1;"
    " for (let n = first; n < first + 4; n++) document.getElementById('older').insertAdjacentHTML('beforeend', post(n));"
    " busy = false; }}, 300); }});</script>"
)
# Mode `boxed_stream`: the same, but the posts sit in a box of their own that scrolls, and only that
# box's scroll loads older ones: which of the two Classroom reacts to was not measured (S10d/S10e
# scrolled both), so the extractor scrolls both and each is tested.
BOXED_STREAM = (
    '<div id="box" style="height: 600px; overflow: auto"><div id="older">{posts}</div>'
    '<div style="height: 3000px"></div></div>'
    "<script>let loads = 0, busy = false; const box = document.getElementById('box');"
    " const post = (n) => '<div data-stream-item-id=\"' + n + '\"><h2>Autor "
    "inventado</h2><div class=\"pco8Kc\">Anuncio antiguo ' + n + '</div><div>Fecha de creación: 3 sept</div></div>';"
    "box.addEventListener('scroll', () => {{ if (busy || loads >= 2) return;"
    " if (box.scrollTop + box.clientHeight < box.scrollHeight - 200) return;"
    " busy = true; setTimeout(() => {{ const first = 8203 + 4 * loads; loads += 1;"
    " for (let n = first; n < first + 4; n++) document.getElementById('older').insertAdjacentHTML('beforeend', post(n));"
    " busy = false; }}, 300); }});</script>"
)
MORE_ROW = '<li data-stream-item-type="5" data-stream-item-id="{n}"><span class="Vu2fZd">Material {n}</span></li>'
PDF = b"%PDF-1.4 fichero inventado\n"

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
        self.service_logins = 0
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

    def _send(
        self,
        body: str | bytes,
        code: int = 200,
        location: str | None = None,
        cookie: str | None = None,
        content_type: str = "text/html; charset=utf-8",
        encoding: str | None = None,
        length: bool = True,
    ) -> None:
        self.send_response(code)
        if encoding:
            self.send_header("Content-Encoding", encoding)
        if location:
            self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Type", content_type)
        if length:
            self.send_header("Content-Length", str(len(body.encode() if isinstance(body, str) else body)))
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def _signed_in(self) -> bool:
        return "fakesid=ok" in (self.headers.get("Cookie") or "")

    def _attachment(self, file_id: str) -> None:
        if not self._signed_in():
            back = quote(f"{self.fake.other_origin}{self.path}", safe="")
            return self._send("", 302, f"{self.fake.origin}/ServiceLogin?continue={back}")
        if file_id == "doc-1" and not self.path.startswith("/content/"):
            return self._send("", 307, "/content/doc-1")
        if file_id in ("f-pdf", "doc-1"):
            return self._send(PDF, content_type="application/pdf")
        if file_id == "f-hop":
            return self._send("", 302, "/download?id=f-pdf&export=download&authuser=5")
        if file_id == "f-gzip":
            return self._send(gzip.compress(PDF * 50), content_type="application/pdf", encoding="gzip")
        if file_id == "f-nolen":
            return self._send(PDF, content_type="application/pdf", length=False)
        if file_id == "f-scheme":
            return self._send("", 302, f"https://localhost:{self.fake.server_address[1]}/download?id=f-pdf")
        if file_id == "f-signin":  # straight to a sign-in page, not through /ServiceLogin
            return self._send("", 302, f"{self.fake.origin}/v3/signin/identifier")
        if file_id == "f-userinfo":
            return self._send("", 302, f"http://someone@127.0.0.1:{self.fake.server_address[1]}/ServiceLogin")
        if file_id == "f-away":
            return self._send("", 302, "http://third.invalid/file")
        if file_id == "f-html":
            return self._send(GENERIC.format(title="No se ha podido analizar el archivo"))
        return self._send("no", 404)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        mode = self.fake.mode
        self.fake.served.append(url.path)
        if url.path == "/download":
            return self._attachment(parse_qs(url.query).get("id", [""])[0])
        exported = re.match(r"^/document/d/([\w-]+)/export$", url.path) or re.match(r"^/content/([\w-]+)$", url.path)
        if exported:
            return self._attachment(exported.group(1))
        if url.path == "/ServiceLogin":
            self.fake.service_logins += 1
            back = parse_qs(url.query).get("continue", [""])[0]
            if self._signed_in() and mode != "sso_refused" and back.startswith(self.fake.other_origin + "/"):
                return self._send("", 302, f"{self.fake.other_origin}/accounts/SetOSID?continue={quote(back, safe='')}")
            return self._send(IDENTIFIER.format(next="/v3/signin/challenge/pwd"))
        if url.path == "/accounts/SetOSID":
            back = parse_qs(url.query).get("continue", [""])[0]
            if mode == "sso_no_cookie":
                return self._send("", 302, back)
            return self._send("", 302, back, cookie="fakesid=ok; Path=/; Max-Age=3600")
        if url.path == "/v3/signin/identifier":
            if "fakestale=1" in (self.headers.get("Cookie") or ""):
                return self._send("", 302, "/v3/signin/accountchooser")
            nxt = {
                "captcha": "/v3/signin/identifier/captcha",
                "rejected": "/signin/rejected",
                "other_sign_in": "http://school.invalid/sign-in",
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
            if mode == "no_account":
                planted = planted.replace(email, "nadie")
            home = _page("home.html")
            if mode == "slow_list":  # the cards come 1.5 s after the page; the account is there at once
                start = home.index(b">", home.index(b"<body")) + 1
                end = home.index(b"</body>")
                late = base64.b64encode(home[start:end]).decode()
                script = (
                    "<div id=late></div><script>setTimeout(() => { document.getElementById('late').outerHTML = "
                    f"new TextDecoder().decode(Uint8Array.from(atob('{late}'), (c) => c.charCodeAt(0))); }}, 1500);"
                    "</script>"
                )
                home = home[:start] + script.encode() + home[end:]
            home = home.replace(b"</body>", planted.encode() + b"</body>", 1)
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
        if mode == "redirect_in_class" and url.path.endswith("/details"):
            return self._send("", 302, url.path.replace("/c/", "/zz/", 1))
        if url.path.startswith("/u/5/zz/"):
            return self._send(_page("assignment-detail.html"))
        for pattern, name in ROUTES:
            if re.match(pattern, url.path):
                body = _page(name)
                if mode in ("long_stream", "boxed_stream") and name == "stream.html":
                    first = "".join(STREAM_POST.format(n=8200 + i) for i in range(3))
                    long = (LONG_STREAM if mode == "long_stream" else BOXED_STREAM).format(posts=first)
                    body = body.replace(b"</body>", long.encode() + b"</body>", 1)
                if name == "classwork.html":
                    body = body.replace(b"</body>", ANSWER_MORE.encode() + b"</body>", 1)
                if mode == "more" and name == "classwork.html":
                    rows = "".join(MORE_ROW.format(n=9300 + i) for i in range(10))
                    late = json.dumps("".join(MORE_ROW.format(n=9300 + i) for i in range(10, 12)))
                    body = body.replace(b"</body>", MORE_TOPIC.format(rows=rows, late=late).encode() + b"</body>", 1)
                return self._send(body)
        return self._send("no", 404)
