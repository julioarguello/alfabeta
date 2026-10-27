"""Personal-data guardrail (constitution II and III; spec 001 FR-005, research R13).

It looks for personal data in what is about to be committed (`--staged`), in every tracked file
(`--all`), or in everything ever published (`--history`). A finding names the file, the line and
the detector, never the value. Before scanning, it plants one known defect per generic detector in
memory and refuses to report "clean" if any detector misses it.
"""

from __future__ import annotations

import base64
import binascii
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_NOTHING_CHECKED = 2
EXIT_BLIND = 3

# Dependency lock files carry hashes and package ids that look like identifiers.
EXCLUDED_FILES = frozenset({"uv.lock", "package-lock.json", ".guardrail-allow"})

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")  # "pkg@0.16.11" is not an address
_ALLOWED_EMAIL_DOMAINS = ("example.org", "example.com")
# Top-level domains RFC 2606 reserves for examples and tests.
_RESERVED_TLDS = (".example", ".test", ".invalid")
# Invented values that reached the published history before the guardrail existed; see the file.
ALLOW_FILE = ".guardrail-allow"
_USER_PATH = re.compile(r"/(?:Users|home)/(?!<)(?!changeme\b)([A-Za-z0-9._-]+)/")
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
# A Drive file id: 28-44 URL-safe characters, starting with "1", mixing upper case, lower case and
# digits. snake_case and camelCase code identifiers do not have that mix.
_DRIVE_ID = re.compile(r"(?<![A-Za-z0-9_-])1[A-Za-z0-9_-]{27,43}(?![A-Za-z0-9_-])")
# Classroom shows its numeric ids base64-encoded in URLs (research R3, S3).
_B64_TOKEN = re.compile(
    r"(?<![A-Za-z0-9+=_-])[A-Za-z0-9+_-]{12,24}={0,2}(?![A-Za-z0-9+=_-])"
)  # "/" separates URL parts
_NUMERIC_ID = re.compile(r"(?<![0-9A-Za-z.])[0-9]{11,15}(?![0-9A-Za-z.])")
# `<student>`, `<school account>`, `<YYYYMMDD>`: letters, digits, spaces, "-" and "_" only, so an HTML tag
# such as `<span class="…">` is never taken for a placeholder and stays scanned.
_PLACEHOLDER = re.compile(r"<[A-Za-z][A-Za-z0-9 _-]{0,58}>|\bsynth-\d+\b")

# Keys whose values identify the student or their accounts in a real configuration. `drive.root` is not
# one: since spec 004 it is a folder name inside My Drive ("alfabeta"), and it would match every file here.
_IDENTIFYING_KEYS = frozenset(
    {
        "id",
        "display_name",
        "name",
        "account",
        "address",
        "base",
        "mirrors",
        "classroom_class",
        "school",
        "drive",
        "owner",  # notebook.owner (spec 005); named values match the leaf key
    }
)
_MIN_NAMED_LENGTH = 4


@dataclass(frozen=True)
class Finding:
    """One hit: where, and which detector. The value is never kept."""

    path: str
    line: int
    detector: str

    def __str__(self) -> str:
        """`file:line: detector`, the only form a finding is shown in."""
        return f"{self.path}:{self.line}: {self.detector}"


def _strip_placeholders(line: str) -> str:
    return _PLACEHOLDER.sub(" ", line)


def _emails(line: str, allowed: frozenset[str] = frozenset()) -> bool:
    for match in _EMAIL.finditer(line):
        local, _, domain = match.group(0).partition("@")
        if local.lower() == "changeme" or match.group(0).lower() in allowed:
            continue
        if domain.lower().endswith(_RESERVED_TLDS):
            continue
        if any(domain.lower() == d or domain.lower().endswith("." + d) for d in _ALLOWED_EMAIL_DOMAINS):
            continue
        return True
    return False


def _user_path(line: str) -> bool:
    return _USER_PATH.search(line) is not None


def _uuid(line: str) -> bool:
    return _UUID.search(line) is not None


def _drive_id(line: str) -> bool:
    for match in _DRIVE_ID.finditer(line):
        token = match.group(0)
        if re.search(r"[a-z]", token) and re.search(r"[A-Z]", token) and re.search(r"[0-9]", token[1:]):
            return True
    return False


def _classroom_id(line: str) -> bool:
    if _NUMERIC_ID.search(line):
        return True
    for match in _B64_TOKEN.finditer(line):
        token = match.group(0)
        padded = token.replace("-", "+").replace("_", "/") + "=" * (-len(token.rstrip("=")) % 4)
        try:
            decoded = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            continue
        if 10 <= len(decoded) <= 15 and decoded.isdigit():
            return True
    return False


GENERIC: dict[str, Callable[[str], bool]] = {
    "email": _emails,
    "user-path": _user_path,
    "notebook-id": _uuid,
    "drive-id": _drive_id,
    "classroom-id": _classroom_id,
}

# One planted defect per generic detector, built at run time so this file never trips itself.
_PLANTED: dict[str, str] = {
    "email": "contact: " + "persona.inventada" + "@" + "dominio-real.es",
    "user-path": "/" + "Users" + "/" + "alguien" + "/Documents/x",
    "notebook-id": "6dcaafd0" + "-1141-4beb-b81b-" + "d5b8b86b9d2d",
    "drive-id": "1" + "AbCdEfGhIjKlMnOpQrStUvWxYz012345",
    "classroom-id": "/c/" + base64.b64encode(("8770" + "02155075").encode()).decode() + "/details",
}


def self_test() -> list[str]:
    """Detectors that miss their own planted defect (empty when all fire)."""
    return [name for name, detect in GENERIC.items() if not detect(_PLANTED[name])]


def _walk_values(data: Any, key: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(data, dict):
        for k, v in cast("dict[str, Any]", data).items():
            yield from _walk_values(v, k)
    elif isinstance(data, list):
        for item in cast("list[Any]", data):
            yield from _walk_values(item, key)
    elif isinstance(data, str):
        yield key, data


def named_values(home: Path) -> list[str]:
    """Identifying values of the real configurations under `home`, longest first."""
    values: set[str] = set()
    if not home.is_dir():
        return []
    for config in sorted(home.glob("*/config.toml")):
        try:
            data = tomllib.loads(config.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if len(config.parent.name) >= _MIN_NAMED_LENGTH:
            values.add(config.parent.name)
        for key, value in _walk_values(data):
            if key in _IDENTIFYING_KEYS and len(value) >= _MIN_NAMED_LENGTH and "changeme" not in value:
                values.add(value)
    return sorted(values, key=len, reverse=True)


def load_allowed(repo: Path) -> frozenset[str]:
    """Exact invented values listed in the allow file, one per line; `#` starts a comment."""
    path = repo / ALLOW_FILE
    if not path.is_file():
        return frozenset()
    entries = (line.split("#", 1)[0].strip().lower() for line in path.read_text().splitlines())
    return frozenset(e for e in entries if e)


def scan_lines(
    path: str, lines: Iterable[tuple[int, str]], named: list[str], allowed: frozenset[str] = frozenset()
) -> list[Finding]:
    """Run every detector over numbered lines of one file."""
    findings: list[Finding] = []
    lowered_named = [v.lower() for v in named]
    for number, raw in lines:
        line = _strip_placeholders(raw)
        for name, detect in GENERIC.items():
            if _emails(line, allowed) if name == "email" else detect(line):
                findings.append(Finding(path, number, name))
        low = raw.lower()
        if any(value in low for value in lowered_named):
            findings.append(Finding(path, number, "configured-value"))
    return findings


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _readable(text: str) -> bool:
    return "\x00" not in text


def _files(repo: Path, staged: bool) -> Iterator[tuple[str, str]]:
    if staged:
        names = _git(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], repo).split("\0")
        reader: Callable[[str], str] = lambda name: _git(["show", f":{name}"], repo)  # noqa: E731
    else:
        names = _git(["ls-files", "-z"], repo).split("\0")
        reader = lambda name: (repo / name).read_text(errors="replace")  # noqa: E731
    for name in names:
        if not name or Path(name).name in EXCLUDED_FILES:
            continue
        try:
            text = reader(name)
        except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
            continue
        if _readable(text):
            yield name, text


def _history(repo: Path) -> Iterator[tuple[str, int, str]]:
    """Added lines of every commit on every ref, as (file, line in the patch, text)."""
    log = _git(["log", "--all", "-p", "--no-color", "--format=commit %H"], repo)
    current = ""
    for number, line in enumerate(log.splitlines(), start=1):
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and Path(current).name not in EXCLUDED_FILES:
            yield current, number, line[1:]


def run(repo: Path, home: Path, mode: str, out: Callable[[str], None] = print) -> int:
    """Run the guardrail in `staged`, `all` or `history` mode and return its exit code."""
    blind = self_test()
    if blind:
        print(f"alfabeta: guardrail detectors are blind: {', '.join(blind)}", file=sys.stderr)
        return EXIT_BLIND
    named = named_values(home)
    allowed = load_allowed(repo)
    if not named:
        print("alfabeta: no local configuration found; only the generic detectors run", file=sys.stderr)
    findings: list[Finding] = []
    checked = 0
    if mode == "history":
        by_file: dict[str, list[tuple[int, str]]] = {}
        for name, number, text in _history(repo):
            by_file.setdefault(name, []).append((number, text))
        for name, lines in by_file.items():
            checked += 1
            findings.extend(scan_lines(f"history:{name}", lines, named, allowed))
    else:
        for name, text in _files(repo, staged=mode == "staged"):
            checked += 1
            findings.extend(scan_lines(name, enumerate(text.splitlines(), start=1), named, allowed))
    for finding in findings:
        out(str(finding))
    if findings:
        return EXIT_FINDING
    if checked == 0:
        if mode == "staged":
            print("alfabeta: guardrail: no staged file to check", file=sys.stderr)
            return EXIT_CLEAN
        print("alfabeta: guardrail checked no file", file=sys.stderr)
        return EXIT_NOTHING_CHECKED
    return EXIT_CLEAN
