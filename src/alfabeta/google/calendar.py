"""Events in the family calendar, written as a linked account (spec 004 FR-008a, research R5)."""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from alfabeta.google.transport import HttpTransport

API = "https://www.googleapis.com/calendar/v3"
TIME_ZONE = "Europe/Madrid"
MAX_REMINDERS = 5
MAX_REMINDER_MINUTES = 40320


class CalendarError(Exception):
    """The Calendar API answered with an error status."""

    def __init__(self, status: int) -> None:
        super().__init__(f"calendar API returned {status}")
        self.status = status


def event_id(key: str) -> str:
    """A deterministic event id: base32hex of the key's SHA-256, lowercase, 52 characters."""
    digest = hashlib.sha256(key.encode()).digest()
    return base64.b32hexencode(digest).decode().rstrip("=").lower()


@dataclass(frozen=True)
class EventSpec:
    """The fields alfabeta owns on an event."""

    summary: str
    start: str  # local date-time, e.g. "2026-10-28T16:00:00"
    end: str
    reminder_minutes: tuple[int, ...] = ()
    description: str = ""

    def body(self) -> dict[str, Any]:
        """The event's JSON body; reminders always explicit, never the calendar's defaults."""
        if len(self.reminder_minutes) > MAX_REMINDERS:
            raise ValueError(f"at most {MAX_REMINDERS} reminders per event")
        if any(not 0 <= m <= MAX_REMINDER_MINUTES for m in self.reminder_minutes):
            raise ValueError(f"reminder minutes must be between 0 and {MAX_REMINDER_MINUTES}")
        return {
            "summary": self.summary,
            "description": self.description,
            "start": {"dateTime": self.start, "timeZone": TIME_ZONE},
            "end": {"dateTime": self.end, "timeZone": TIME_ZONE},
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": m} for m in self.reminder_minutes],
            },
        }


class CalendarClient:
    """One calendar, one access token."""

    def __init__(self, transport: HttpTransport, token: str, calendar_id: str) -> None:
        self._transport = transport
        self._token = token
        self._base = f"{API}/calendars/{urllib.parse.quote(calendar_id, safe='')}/events"

    def _call(self, method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token}"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        resp = self._transport.request(method, url, headers=headers, body=data)
        if resp.status >= 400:
            raise CalendarError(resp.status)
        return cast("dict[str, Any]", json.loads(resp.body)) if resp.body else {}

    def get(self, eid: str) -> dict[str, Any] | None:
        """The event, or None if it does not exist."""
        try:
            return self._call("GET", f"{self._base}/{eid}")
        except CalendarError as err:
            if err.status == 404:
                return None
            raise

    def insert(self, eid: str, spec: EventSpec) -> dict[str, Any]:
        """Create the event with that id."""
        return self._call("POST", self._base, {"id": eid, **spec.body()})

    def update(self, eid: str, spec: EventSpec) -> dict[str, Any]:
        """Replace the event's owned fields, and confirm it if it was cancelled."""
        return self._call("PUT", f"{self._base}/{eid}", {**spec.body(), "status": "confirmed"})

    def delete(self, eid: str) -> None:
        """Delete the event; already gone is fine."""
        try:
            self._call("DELETE", f"{self._base}/{eid}")
        except CalendarError as err:
            if err.status not in (404, 410):
                raise

    def upsert(self, eid: str, spec: EventSpec) -> str:
        """Write the event only if an owned field differs. Returns `created`, `updated` or `unchanged`."""
        current = self.get(eid)
        if current is None:
            try:
                self.insert(eid, spec)
                return "created"
            except CalendarError as err:
                if err.status != 409:
                    raise
                # The id is taken by a cancelled event (research R5): bring it back.
                self.update(eid, spec)
                return "updated"
        if current.get("status") != "cancelled" and _owned(current) == _owned(spec.body()):
            return "unchanged"
        self.update(eid, spec)
        return "updated"


def _owned(event: dict[str, Any]) -> tuple[Any, ...]:
    reminders = cast("dict[str, Any]", event.get("reminders", {}))
    overrides = cast("list[dict[str, Any]]", reminders.get("overrides", []))
    start = cast("dict[str, Any]", event.get("start", {}))
    end = cast("dict[str, Any]", event.get("end", {}))
    return (
        event.get("summary"),
        event.get("description", ""),
        str(start.get("dateTime", ""))[:19],
        str(end.get("dateTime", ""))[:19],
        reminders.get("useDefault"),
        tuple(sorted(int(o.get("minutes", -1)) for o in overrides)),
    )
