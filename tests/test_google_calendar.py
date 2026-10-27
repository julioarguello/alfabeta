import json
import re

import pytest

from alfabeta.google import calendar
from alfabeta.google.transport import Response
from tests.conftest import CALENDAR_ID, FakeTransport, json_response

SPEC = calendar.EventSpec("Entrega · Física · Prueba", "2026-10-28T16:00:00", "2026-10-28T16:30:00", (0, 1440))


def _client(t: FakeTransport) -> calendar.CalendarClient:
    return calendar.CalendarClient(t, "acceso", CALENDAR_ID)


def test_event_id_is_valid_base32hex_and_stable():
    eid = calendar.event_id("classroom:123")
    assert re.fullmatch(r"[a-v0-9]{5,1024}", eid)
    assert eid == calendar.event_id("classroom:123") != calendar.event_id("classroom:124")


def test_body_reminders_are_explicit_and_bounded():
    body = SPEC.body()
    assert body["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 0}, {"method": "popup", "minutes": 1440}],
    }
    assert body["start"]["timeZone"] == "Europe/Madrid"
    with pytest.raises(ValueError):
        calendar.EventSpec("x", SPEC.start, SPEC.end, (1, 2, 3, 4, 5, 6)).body()
    with pytest.raises(ValueError):
        calendar.EventSpec("x", SPEC.start, SPEC.end, (40321,)).body()


def test_upsert_creates_when_absent():
    t = FakeTransport([Response(404), json_response(200, {"id": "e"})])
    assert _client(t).upsert("eeeee", SPEC) == "created"
    assert t.calls[1][0] == "POST"
    assert json.loads(t.calls[1][3] or b"{}")["id"] == "eeeee"
    assert "%40" in t.calls[1][1]  # the calendar id is quoted, not passed raw


def test_upsert_unchanged_writes_nothing():
    current = {
        **SPEC.body(),
        "start": {"dateTime": "2026-10-28T16:00:00+01:00"},
        "end": {"dateTime": "2026-10-28T16:30:00+01:00"},
        "status": "confirmed",
    }
    t = FakeTransport([json_response(200, current)])
    assert _client(t).upsert("eeeee", SPEC) == "unchanged"
    assert len(t.calls) == 1


def test_upsert_updates_on_difference():
    current = {**SPEC.body(), "summary": "otro"}
    t = FakeTransport([json_response(200, current), json_response(200, {})])
    assert _client(t).upsert("eeeee", SPEC) == "updated"
    assert t.calls[1][0] == "PUT"
    assert json.loads(t.calls[1][3] or b"{}")["status"] == "confirmed"


def test_upsert_conflict_on_insert_revives_the_id():
    t = FakeTransport([Response(404), Response(409), json_response(200, {})])
    assert _client(t).upsert("eeeee", SPEC) == "updated"
    assert [c[0] for c in t.calls] == ["GET", "POST", "PUT"]


def test_delete_absent_is_fine():
    _client(FakeTransport([Response(410)])).delete("eeeee")
