"""Classroom's date texts (spec 001 T022). Shapes taken from a real capture of 2026-10-26."""

from __future__ import annotations

import datetime as dt

import pytest

from alfabeta.dates import MADRID, DateError, DateResolver, Posting

# Tuesday 27 October 2026, 18:00 in Madrid.
CAPTURED = dt.datetime(2026, 10, 27, 18, 0, tzinfo=MADRID)
R = DateResolver("2026-2027", CAPTURED)


def at(y: int, m: int, d: int, hh: int, mm: int) -> dt.datetime:
    return dt.datetime(y, m, d, hh, mm, tzinfo=MADRID)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("13 oct", dt.date(2026, 10, 13)),
        ("14 ene", dt.date(2027, 1, 14)),
        ("3 sept", dt.date(2026, 9, 3)),
        ("31 ago", dt.date(2027, 8, 31)),
        ("13 oct 2025", dt.date(2025, 10, 13)),
        ("Hoy", dt.date(2026, 10, 27)),
        ("Ayer", dt.date(2026, 10, 26)),
        ("Mañana, 8:00", at(2026, 10, 28, 8, 0)),
        ("viernes", dt.date(2026, 10, 30)),
        ("martes, 8:00", at(2026, 11, 3, 8, 0)),  # today is Tuesday: «martes» is the next one
        ("Fecha de entrega: 19 oct, 8:00", at(2026, 10, 19, 8, 0)),
        ("Fecha de entrega: 9 nov", dt.date(2026, 11, 9)),
        ("Fecha de entrega: 23:59", at(2026, 10, 27, 23, 59)),  # a bare time is today
    ],
)
def test_resolve(text: str, expected: dt.date | dt.datetime):
    assert R.resolve(text) == expected


def test_relative_texts_follow_the_capture_not_the_day_it_is_applied():
    yesterday = DateResolver("2026-2027", CAPTURED - dt.timedelta(days=1))
    assert yesterday.resolve("Mañana, 8:00") == at(2026, 10, 27, 8, 0)
    assert yesterday.resolve("Hoy") == dt.date(2026, 10, 26)


def test_capture_near_midnight_uses_madrid_day():
    utc_late = dt.datetime(2026, 10, 27, 23, 30, tzinfo=dt.UTC)  # 00:30 on the 28th in Madrid
    assert DateResolver("2026-2027", utc_late).resolve("Hoy") == dt.date(2026, 10, 28)


def test_clock_changes():
    # Summer time ends on 25 October 2026 and starts on 28 March 2027.
    before_october = DateResolver("2026-2027", dt.datetime(2026, 10, 24, 18, 0, tzinfo=MADRID))
    sunday = before_october.resolve("Mañana, 8:00")
    assert sunday == at(2026, 10, 25, 8, 0)
    assert isinstance(sunday, dt.datetime) and sunday.utcoffset() == dt.timedelta(hours=1)
    assert at(2026, 10, 24, 8, 0).utcoffset() == dt.timedelta(hours=2)
    march = R.resolve("28 mar, 8:00")
    assert isinstance(march, dt.datetime) and march.utcoffset() == dt.timedelta(hours=2)
    assert R.resolve("27 mar, 8:00") == dt.datetime(2027, 3, 27, 7, 0, tzinfo=dt.UTC)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("13 sept", Posting(dt.date(2026, 9, 13), None)),
        ("13 sept (Última modificación: 14 oct)", Posting(dt.date(2026, 9, 13), dt.date(2026, 10, 14))),
        ("13 sept (Última modificación: 12:34)", Posting(dt.date(2026, 9, 13), dt.date(2026, 10, 27))),
    ],
)
def test_posting_never_takes_the_modification_as_posting(text: str, expected: Posting):
    assert R.posting(text) == expected


@pytest.mark.parametrize("text", ["13 octubrillo", "pronto", ""])
def test_unknown_shapes_fail(text: str):
    with pytest.raises(DateError):
        R.resolve(text)


def test_school_year_window():
    assert R.in_school_year(dt.date(2026, 9, 1)) and R.in_school_year(dt.date(2027, 8, 31))
    assert not R.in_school_year(dt.date(2026, 8, 31)) and not R.in_school_year(dt.date(2027, 9, 1))
    assert R.in_school_year(CAPTURED)


def test_capture_instant_needs_its_zone():
    with pytest.raises(ValueError, match="time zone"):
        DateResolver("2026-2027", dt.datetime(2026, 10, 27, 18, 0))
