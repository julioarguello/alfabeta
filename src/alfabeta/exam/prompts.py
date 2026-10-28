"""The exam sheets' fixed prompts, read from the study-pack skill's `prompts.md` (spec 002 FR-029).

The prompts are texts of the repository, measured in Spanish; this module only finds them and fills
their `{placeholders}`. A placeholder left without a value is a bug, never a prompt sent half-filled,
and a value is never read again for placeholders: an announcement may hold braces of its own.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

PROMPTS = Path(__file__).resolve().parents[3] / "skills" / "study-pack" / "prompts.md"
THEORY = "Theory sheet — for an exam"
PROBLEMS = "Problems sheet — for an exam"
START_NOTE = "Start note — for an exam"

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


def language_words(code: str) -> str:
    """A subject's `language` code in words, `eu` → `euskera`."""
    try:
        return LANGUAGES[code]
    except KeyError:
        raise PromptError(f"no words for the language code {code!r}") from None


def weekday(day: dt.date) -> str:
    """`jueves`."""
    return WEEKDAYS[day.weekday()]


def day_month(day: dt.date) -> str:
    """`8 de mayo`."""
    return f"{day.day} de {MONTHS[day.month - 1]}"


def exam_day(day: dt.date) -> str:
    """`martes 12 de mayo`."""
    return f"{weekday(day)} {day_month(day)}"


def short_day(day: dt.date) -> str:
    """`29 oct`, as the printed sheets' names carry the exam's date."""
    return f"{day.day} {MONTHS[day.month - 1][:3]}"
