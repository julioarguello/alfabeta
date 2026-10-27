"""Synthetic pages from real Classroom pages (spec 001 T016, research R8; constitution III and IV).

The output keeps the tags, the CSS classes, the hierarchy and the interface labels of the
allowlist recorded in research R8, and invents everything else with stable values: texts, other
attribute values, dates, and the ids inside URLs as `synth-<n>` in the same position. Scripts are
emptied, because they carry the page's data. Nothing is written if any input text outside the
allowlist survives, or if the personal-data guardrail finds something in the result.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import TYPE_CHECKING

from alfabeta import guardrail

if TYPE_CHECKING:
    from pathlib import Path

# Research R8, «Label allowlist (from S3)», observed 2026-10-25 with the interface in Spanish.
LABELS = frozenset(
    {
        "Trabajo de clase",
        "Tablón",
        "Personas",
        "Ver tu trabajo",
        "Tarea",
        "Material",
        "Pregunta",
        "Sin tema",
        "Fecha de entrega",
        "Sin fecha de entrega",
        "Publicado",
        "Última modificación",
        "Tu trabajo",
        "Asignado",
        "Entregado",
        "Sin entregar",
        "Añadir o crear",
        "Marcar como completado",
        "Entregar",
        "Tu respuesta",
        "puntos",
        "Comentarios de la clase",
        "Comentarios privados",
        "Próximas entregas",
        "Ver todo",
        "ha publicado",
        "publicado una nueva tarea",
        "Hoy",
    }
)
_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic")
_DATE = re.compile(r"(?:\d{1,2} (?:" + "|".join(_MONTHS) + r")(?:, \d{1,2}:\d{2})?|\d{1,2}:\d{2})")
_LABELLED = re.compile(
    r"^(" + "|".join(re.escape(label) for label in sorted(LABELS, key=len, reverse=True)) + r")(: ?)(.+)$"
)
# Route words of Classroom, Drive and YouTube URLs stay; every other path segment becomes an id.
_ROUTES = frozenset(
    {
        "u",
        "c",
        "a",
        "m",
        "sa",
        "w",
        "t",
        "h",
        "r",
        "p",
        "s",
        "d",
        "details",
        "submissions",
        "view",
        "file",
        "folders",
        "drive",
        "document",
        "presentation",
        "spreadsheets",
        "forms",
        "edit",
        "preview",
        "watch",
        "embed",
        "open",
        "all",
        "not-turned-in",
        "missing",
        "done",
    }
)
_HOSTS = frozenset({"classroom.google.com", "drive.google.com", "docs.google.com", "www.youtube.com", "youtu.be"})
_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
)
_SUFFIXED = re.compile(
    r"^(.+?) (" + "|".join(re.escape(label) for label in sorted(LABELS, key=len, reverse=True)) + r")$"
)
# An opaque id in an attribute (`data-id`): no spaces, at least 8 characters, letters and digits.
_ID_TOKEN = re.compile(r"(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{8,}={0,2}")
_MIN_CHECKED = 4
_ID_IN_NAME = re.compile(r"\d{3,}|[0-9a-f]{8}-[0-9a-f]{4}", re.IGNORECASE)


class AnonymizeError(Exception):
    """The synthetic page would leak something; nothing was written."""


@dataclass
class _Inventor:
    """Stable invented values: the same input always gets the same output within a page."""

    texts: dict[str, str] = field(default_factory=dict[str, str])
    ids: dict[str, str] = field(default_factory=dict[str, str])
    dates: dict[str, str] = field(default_factory=dict[str, str])

    def text(self, original: str) -> str:
        return self.texts.setdefault(original, f"texto {len(self.texts) + 1}")

    def ident(self, original: str) -> str:
        return self.ids.setdefault(original, f"synth-{len(self.ids) + 1}")

    def date(self, original: str) -> str:
        if original not in self.dates:
            n = len(self.dates)
            time = ", 8:00" if "," in original else ""
            self.dates[original] = f"{n % 28 + 1} {_MONTHS[(n // 28 + 8) % 12]}{time}"
        return self.dates[original]

    def url(self, original: str) -> str:
        scheme, sep, rest = original.partition("://")
        if not sep:
            scheme, rest = "", original
        host, slash, path = rest.partition("/") if sep else ("", "/", rest.lstrip("/"))
        path = path.split("?", 1)[0].split("#", 1)[0]
        parts = [part if (not part or part in _ROUTES) else self.ident(part) for part in path.split("/")]
        if sep:
            return f"{scheme}://{host if host in _HOSTS else 'example.org'}{slash}{'/'.join(parts)}"
        return ("/" if original.startswith("/") else "") + "/".join(parts)

    def value(self, original: str) -> str:
        """Any text: kept if it is a label, shaped if it is a date or a labelled date, else invented."""
        stripped = original.strip()
        if not stripped or _is_label(stripped):
            return original
        if _DATE.fullmatch(stripped):
            return original.replace(stripped, self.date(stripped))
        if _ID_TOKEN.fullmatch(stripped):
            return original.replace(stripped, self.ident(stripped))
        suffixed = _SUFFIXED.match(stripped)
        if suffixed:
            return original.replace(stripped, f"{self.value(suffixed.group(1))} {suffixed.group(2)}")
        labelled = _LABELLED.match(stripped)
        if labelled:
            label, colon, rest = labelled.groups()
            return original.replace(stripped, f"{label}{colon}{self.value(rest)}")
        return original.replace(stripped, self.text(stripped))


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://", "//")) or (value.startswith("/") and " " not in value)


def _is_label(text: str) -> bool:
    return text in LABELS or text.rstrip(":").rstrip() in LABELS


class _Rewriter(HTMLParser):
    def __init__(self, inventor: _Inventor) -> None:
        super().__init__(convert_charrefs=True)
        self.inventor = inventor
        self.out: list[str] = []
        self.seen: set[str] = set()
        # What this page says in texts and attribute values; tags, attribute names and classes are structure.
        self.emitted: list[str] = []
        self._in_script = False

    def _attrs(self, attrs: list[tuple[str, str | None]]) -> str:
        rendered: list[str] = []
        for original_name, value in attrs:
            # An attribute name is structure, unless it carries an id (`data-<uuid>`).
            name = f"data-{self.inventor.ident(original_name)}" if _ID_IN_NAME.search(original_name) else original_name
            if value is None:
                rendered.append(f" {name}")
                continue
            if name == "class":
                kept = value
            elif _looks_like_url(value):
                kept = self.inventor.url(value)
                if kept != value:  # unchanged = only allowed hosts and route words, nothing to hide
                    self.seen.add(value)
                    self.emitted.append(kept)
            else:
                self.seen.add(value)
                kept = self.inventor.value(value)
                self.emitted.append(kept)
            rendered.append(f' {name}="{html.escape(kept, quote=True)}"')
        return "".join(rendered)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.out.append(f"<{tag}{self._attrs(attrs)}>")
        self._in_script = tag == "script"

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.out.append(f"<{tag}{self._attrs(attrs)}/>")

    def handle_endtag(self, tag: str) -> None:
        if tag not in _VOID:
            self.out.append(f"</{tag}>")
        self._in_script = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            return  # dropped: a script carries the page's data and never reaches the result
        last = self.out[-1] if self.out else ""
        if last.startswith("<style"):
            self.out.append(data)
            return
        self.seen.add(data)
        invented = self.inventor.value(data)
        self.emitted.append(invented)
        self.out.append(html.escape(invented, quote=False))

    def handle_decl(self, decl: str) -> None:
        self.out.append(f"<!{decl}>")


def _pieces(text: str) -> set[str]:
    """The parts of an input text that must not reach the output: neither labels nor date shapes."""
    found: set[str] = set()
    for chunk in re.split(r"[\n\t\"<>]+", text):
        stripped = chunk.strip()
        labelled = _LABELLED.match(stripped)
        if labelled:
            stripped = labelled.group(3).strip()
        allowed = _is_label(stripped) or _DATE.fullmatch(stripped) or stripped in _ROUTES
        if len(stripped) >= _MIN_CHECKED and not allowed:
            found.add(stripped)
    return found


def anonymize(source: str, named: list[str] | None = None) -> str:
    """The synthetic page for `source`; AnonymizeError if a text of the input or personal data survives."""
    rewriter = _Rewriter(_Inventor())
    rewriter.feed(source)
    rewriter.close()
    result = "".join(rewriter.out)
    said = "\n".join(rewriter.emitted)
    survivors = [piece for value in rewriter.seen for piece in _pieces(value) if piece in said]
    if survivors:
        raise AnonymizeError(f"{len(survivors)} input texts survive outside the allowlist")
    findings = guardrail.scan_lines("<output>", enumerate(result.splitlines(), start=1), named or [])
    if findings:
        detectors = sorted({f.detector for f in findings})
        raise AnonymizeError(f"the guardrail finds {', '.join(detectors)} in the result")
    return result


def run(input_path: Path, output_path: Path, home: Path) -> str:
    """Anonymize one saved page into `output_path`; writes nothing on failure."""
    result = anonymize(input_path.read_text(errors="replace"), guardrail.named_values(home))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result)
    return str(output_path)
