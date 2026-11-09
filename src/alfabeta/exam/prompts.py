"""The exam sheets' fixed prompts, read from the study-pack skill's `prompts.md` (spec 002 FR-029).

`language_values` also holds the values the skill's agent gives the pack prompts' language placeholders, which
`prompts.md`'s table quotes (#226); a test keeps the two in step.

The prompts are texts of the repository, measured in Spanish; this module only finds them and fills
their `{placeholders}`. A placeholder left without a value is a bug, never a prompt sent half-filled,
and a value is never read again for placeholders: an announcement may hold braces of its own.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

    from alfabeta.config import Rules

PROMPTS = Path(__file__).resolve().parents[3] / "skills" / "study-pack" / "prompts.md"
THEORY = "Theory sheet — for an exam"
PROBLEMS = "Problems sheet — for an exam"
START_NOTE = "Start note — for an exam"
# With no captured announcement, when the family named the topics (spec 007 FR-025 to FR-029).
THEORY_OPEN = "Theory sheet — for an exam with no announcement"
PROBLEMS_OPEN = "Problems sheet — for an exam with no announcement"
START_NOTE_OPEN = "Start note — for an exam with no announcement"
# How every sheet is laid out, added to each one before any rules (constitution XI, spec 002 FR-052, #229).
FORMAT = "Reading format — added to a prompt"
# The text a prompt gains when the student or the subject has standing rules (spec 009).
RULES = "Standing rules — added to a prompt"
RULES_LIMIT = 2000  # characters of `{rules}`; unmeasured (spec 009 research R5)
NO_DATE = "sin fecha"  # where the exam's date would go (spec 007 FR-028a)
# `{notes_corrections}` of an exam with no announcement, before the lines of `bloques.md` (spec 007 FR-027).
CORRECTIONS = (
    "Correcciones ya comprobadas en estos apuntes, que prevalecen sobre lo anterior aunque los apuntes insistan o las"
    " fuentes callen; en estos puntos no enseñes su versión y añade en esa sección o junto al problema «Corrige en tus"
    " apuntes: …»: "
)

# `{language}` in words, as the prompts were measured with it (prompts.md).
LANGUAGES = {
    "es": "castellano",
    "eu": "euskera",
    "en": "inglés",
    "fr": "francés",
    "de": "alemán",
    "ca": "catalán",
    "gl": "gallego",
}
SPANISH = "es"  # the language the student studies in: no translation, no term pairs (#224)
WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class PromptError(Exception):
    """A prompt is not in `prompts.md`, or a placeholder has no value."""


def template(heading: str, source: Path = PROMPTS) -> str:
    """The first `text` block of the `## <heading>` section of `prompts.md`, never of a later section."""
    sections = re.split(r"^(?=## )", source.read_text(), flags=re.MULTILINE)
    section = next((s for s in sections if s.split("\n", 1)[0] == f"## {heading}"), "")
    found = re.search(r"^```text\n(.*?)\n^```", section, flags=re.MULTILINE | re.DOTALL)
    if found is None:
        raise PromptError(f"prompts.md has no text block under «{heading}»")
    return found.group(1)


def fill(text: str, values: Mapping[str, str]) -> str:
    """`text` with each placeholder replaced in one pass; a placeholder without a value raises."""
    missing = sorted({name for name in _PLACEHOLDER.findall(text) if name not in values})
    if missing:
        raise PromptError(f"no value for {', '.join(missing)}")
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


class RulesTooLong(Exception):
    """A sheet's rules are over the limit: nothing is cut in silence (spec 009 FR-010)."""

    def __init__(self, kind: str, over: int) -> None:
        super().__init__(
            f"the standing rules of the {kind} sheet are {over} character{'s'[: over != 1]} over the limit"
        )


@dataclass(frozen=True)
class RulesUsed:
    """What a prompt gained, named and fingerprinted; it holds no word of the rules (spec 009 FR-008)."""

    used: tuple[str, ...]
    fingerprint: str

    def as_json(self) -> dict[str, Any]:
        """The shape of the command's result and of the pack's record."""
        return {"used": list(self.used), "fingerprint": self.fingerprint}


def with_format(prompt: str, language: Mapping[str, str]) -> str:
    """`prompt`, filled and right-stripped, with the reading format after it and one space (spec 002 FR-052).

    `language` is `language_values` of the subject. Read on every run, so a renamed heading refuses before
    anything is asked.
    """
    return f"{prompt} {fill(template(FORMAT), language)}"


def with_rules(prompt: str, rules: Rules, kind: str) -> tuple[str, RulesUsed | None]:
    """`prompt`, filled, with the rules that speak to `kind` after it, and what it gained (spec 009 FR-003).

    The section is read even with no rules, so a renamed heading never goes unnoticed; `fill` makes one pass,
    so a rule's braces are never read as placeholders.
    """
    added = template(RULES)
    parts = rules.parts(kind)
    if not parts:
        return prompt, None
    levels = (
        (label, " ".join(text for name, text in parts if name.startswith(level)))
        for label, level in (("Del alumno", "student."), ("De la asignatura", "subject."))
    )
    words = " ".join(f"{label}: {text}" for label, text in levels if text)
    if len(words) > RULES_LIMIT:
        raise RulesTooLong(kind, len(words) - RULES_LIMIT)
    text = fill(added, {"rules": words})
    fingerprint = hashlib.sha256(text.encode()).hexdigest()[:8]
    return f"{prompt} {text}", RulesUsed(tuple(name for name, _ in parts), fingerprint)


def language_words(code: str) -> str:
    """A subject's `language` code in words, `eu` → `euskera`."""
    try:
        return LANGUAGES[code]
    except KeyError:
        raise PromptError(f"no words for the language code {code!r}") from None


def language_values(code: str) -> dict[str, str]:
    """The placeholders of `prompts.md` that hang on the subject's language: the exam sheets' and the pack's (#224, #226).

    The templates were written for a subject taught in another language to a student who studies in castellano;
    for a subject in castellano a translation or a term in two languages only repeats the same words.
    """
    words = language_words(code)
    if code == SPANISH:
        return {
            "language": words,
            "studies_in": "",
            "term_order": "Cada término va tal como lo escribe el material de clase; ",
            "statement": "su enunciado copiado tal cual",
            "bilingual_terms": "",
            "also_in": "",
            "term_columns": "término tal como aparece en el material de clase",
            "parent_lacks": "",
            "in_language": "",
            "translated": "",
            "in_spanish": "",
            "term_in_brackets": "",
            "languages_apart": "",
        }
    return {
        "language": words,
        "studies_in": " y estudia en castellano",
        "term_order": (
            f"Cada término va primero en {words}, tal como lo escribe el material de clase, y después en castellano; "
        ),
        "statement": "su enunciado copiado tal cual en su idioma, su traducción al castellano",
        "bilingual_terms": f"Cada término, primero en {words} y después en castellano. ",
        "also_in": f" también en {words}",
        "term_columns": f"término en {words} tal como aparece en el material de clase | castellano",
        "parent_lacks": f" y no sabe {words}",
        "in_language": f" en {words}",
        "translated": " traducido al castellano",
        "in_spanish": " en castellano y",
        "term_in_brackets": f" y el término en {words} entre paréntesis",
        "languages_apart": (
            " Cada frase va entera en un solo idioma."
            " Si el documento da un término también en otro idioma, aparece una sola vez por concepto y en el mismo"
            " sitio de la línea en todo el documento, o en su propia columna de una tabla, nunca traducido palabra a"
            " palabra dentro de una frase."
            " Un enunciado y su traducción van en dos bloques separados, uno debajo del otro, nunca frase a frase."
        ),
    }


def weekday(day: dt.date) -> str:
    """`jueves`."""
    return WEEKDAYS[day.weekday()]


def day_month(day: dt.date) -> str:
    """`8 de mayo`."""
    return f"{day.day} de {MONTHS[day.month - 1]}"


def exam_day(day: dt.date) -> str:
    """`martes 12 de mayo`."""
    return f"{weekday(day)} {day_month(day)}"


def exam_name(day: dt.date | None) -> str:
    """`Examen del martes 12 de mayo`, or `Examen sin fecha`."""
    return f"Examen del {exam_day(day)}" if day else f"Examen {NO_DATE}"


def notes_corrections(lines: list[str]) -> str:
    """`{notes_corrections}` of an exam with no announcement: empty, or the lines verbatim after their sentence."""
    return f"{CORRECTIONS}{' '.join(lines)} " if lines else ""


def short_day(day: dt.date) -> str:
    """`29 oct`, as the printed sheets' names carry the exam's date."""
    return f"{day.day} {MONTHS[day.month - 1][:3]}"
