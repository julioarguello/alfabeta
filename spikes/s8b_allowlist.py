"""Spike S8, second half (#267/#270), read-only: the read with only an allowlist of Classroom's calls let through.

read.py unchanged (its Guard, its extractor, its class calls) with one addition to the Guard's route, run first:
a batchexecute request naming any call outside ALLOW is aborted, and so is every request to the telemetry, push
and Google-bar hosts. Each abort is counted by call name or host in the end event's `blocked`. Usage inside the
read image: python /s8b.py <class id> [<class id>] with the read's request on stdin (signin false, no password).
Compare the captures in /out with the same session's refresh to see whether the allowlist is enough.
"""
import sys
from urllib.parse import parse_qs, urlsplit
sys.path.insert(0, "/app")
import read as R  # noqa: E402

# The names S8 saw carrying the capture's fields, plus the course queries every page sends (research S8).
ALLOW = frozenset({"dpT4Vd", "pONvgf", "tQShAc", "ZZFlc", "Zj93ge", "cCzVwf", "t51ITc", "gXtzob", "O1Xqee", "UG41I"})
# Run 1 (16:43) left UG41I out: the home page then listed no class (18 retries of it). Run 2 lets it through.
BLOCK_HOSTS = frozenset({"play.google.com", "signaler-pa.clients6.google.com", "ogads-pa.clients6.google.com"})

_route = R.Guard.route


def route(self, route, request):
    parts = urlsplit(request.url)
    host = parts.hostname or ""
    if host in BLOCK_HOSTS:
        self._count("host:" + host)
        route.abort()
        return
    if parts.path.endswith("/batchexecute"):
        names = [n for n in parse_qs(parts.query).get("rpcids", [""])[0].split(",") if n]
        outside = [n for n in names if n not in ALLOW]
        if not names or outside:
            for n in outside or ["(none)"]:
                self._count("call:" + n)
            route.abort()
            return
    _route(self, route, request)


R.Guard.route = route
R.ONLY = frozenset(sys.argv[1:])
sys.exit(R.main())
