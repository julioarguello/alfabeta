"""Classroom's Spanish date texts → dates in Europe/Madrid (spec 001 T023, research R3).

Classroom writes dates without a year («13 oct»), relative to the moment they are seen («Hoy»,
«Mañana», a weekday) or as a bare time for today («8:00»). The year comes from the school year
(September to December, its first year; January to August, its second) and every relative text is
resolved against the capture's instant, never against the moment it is applied.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

_MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}
_FULL_MONTHS = [
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
]
# Abbreviations Classroom writes («13 sept»), and the full names, to their month number.
_MONTH_WORDS = {**_MONTHS, "sept": 9, "set": 9} | {name: n for n, name in enumerate(_FULL_MONTHS, start=1)}
_WEEKDAYS = {"lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3, "viernes": 4, "sábado": 5, "domingo": 6}
_RELATIVE = {"ayer": -1, "hoy": 0, "mañana": 1}
_DUE_PREFIX = re.compile(r"^\s*fecha de entrega:\s*", re.IGNORECASE)
_MODIFIED = re.compile(r"\(\s*última modificación:\s*([^)]*)\)", re.IGNORECASE)
_DAY_MONTH = re.compile(r"(\d{1,2})\s+([a-záéíóú]+)\.?(?:\s+(\d{4}))?")
_TIME = re.compile(r"(\d{1,2}):(\d{2})")


class DateError(ValueError):
    """A text that is not one of Classroom's date shapes."""


@dataclass(frozen=True)
class Posting:
    """When an item was posted and, if Classroom says so, when it was last modified."""

    posted_at: dt.date
    modified_at: dt.date | None


@dataclass(frozen=True)
class DateResolver:
    """Resolves texts captured at `captured_at` for a student in `school_year` ("YYYY-YYYY")."""

    school_year: str
    captured_at: dt.datetime

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must carry its time zone")

    @property
    def _today(self) -> dt.date:
        return self.captured_at.astimezone(MADRID).date()

    @property
    def first_year(self) -> int:
        """The calendar year the school year starts in."""
        return int(self.school_year[:4])

    def in_school_year(self, moment: dt.datetime | dt.date) -> bool:
        """Whether `moment` falls between September of the first year and August of the second."""
        day = moment.astimezone(MADRID).date() if isinstance(moment, dt.datetime) else moment
        return dt.date(self.first_year, 9, 1) <= day <= dt.date(self.first_year + 1, 8, 31)

    def _day(self, text: str) -> dt.date | None:
        """The date part of a text, or None if it only carries a time."""
        lowered = text.strip().lower()
        for word, offset in _RELATIVE.items():
            if lowered.startswith(word):
                return self._today + dt.timedelta(days=offset)
        for word, weekday in _WEEKDAYS.items():
            if lowered.startswith(word):
                # A weekday is the next one after today: Classroom says «Hoy» for today.
                ahead = (weekday - self._today.weekday() - 1) % 7 + 1
                return self._today + dt.timedelta(days=ahead)
        match = _DAY_MONTH.match(lowered)
        if match:
            day, word, year = match.groups()
            month = _MONTH_WORDS.get(word)
            if month is None:
                raise DateError("unknown month")
            if year is None:
                year = str(self.first_year if month >= 9 else self.first_year + 1)
            return dt.date(int(year), month, int(day))
        if _TIME.fullmatch(lowered):
            return None
        raise DateError("not a Classroom date")

    def resolve(self, text: str) -> dt.datetime | dt.date:
        """A date, or a Madrid date-time when the text gives a time; a bare time is today."""
        body = _DUE_PREFIX.sub("", text).strip()
        day = self._day(body) or self._today
        time = _TIME.search(body)
        if time is None:
            return day
        hour, minute = int(time.group(1)), int(time.group(2))
        return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=MADRID)

    def posting(self, text: str) -> Posting:
        """«13 oct (Última modificación: 14 oct)» → posted 13 Oct, modified 14 Oct.

        The posting date is the text outside the parentheses; «Última modificación» is never taken
        as the posting date.
        """
        modified = _MODIFIED.search(text)
        posted_text = _MODIFIED.sub("", text).strip()
        posted = self.resolve(posted_text)
        changed = self.resolve(modified.group(1)) if modified else None
        return Posting(_as_date(posted), _as_date(changed) if changed is not None else None)


def _as_date(value: dt.datetime | dt.date) -> dt.date:
    return value.date() if isinstance(value, dt.datetime) else value
