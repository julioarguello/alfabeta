"""Spec 010: the Gmail adapter against an invented mailbox that answers like Gmail. No request leaves the test."""

from __future__ import annotations

import json
import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from alfabeta import mail
from alfabeta.google import gmail
from alfabeta.google.transport import Response

PLAN = mail.plan("1º ESO", ("Mates", "Lengua"), "{grade}. {subject}. {topic}")
# FR-008's list: method and path, nothing else (SC-004).
ALLOWED = {
    ("GET", "/labels"),
    ("POST", "/labels"),
    ("GET", "/settings/filters"),
    ("POST", "/settings/filters"),
    ("GET", "/messages"),
    ("POST", "/messages/batchModify"),
}
PREFIX = "/gmail/v1/users/me"


@dataclass
class FakeGmail:
    """Labels, filters and messages kept like Gmail keeps them; records every request."""

    labels: dict[str, str] = field(default_factory=lambda: {"INBOX": "INBOX"})  # id -> name
    filters: list[dict[str, Any]] = field(default_factory=lambda: [])
    # message id -> (the plan's query it matches, its label ids)
    messages: dict[str, tuple[str, set[str]]] = field(default_factory=lambda: {})
    calls: list[tuple[str, str]] = field(default_factory=lambda: [])
    page: int = 2
    conflict_on: str = ""

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
    ) -> Response:
        parsed = urllib.parse.urlparse(url)
        assert parsed.path.startswith(PREFIX + "/"), "every path is under users/me"
        path = parsed.path.removeprefix(PREFIX)
        self.calls.append((method, path))
        assert (headers or {}).get("Authorization") == "Bearer acceso"
        data: dict[str, Any] = json.loads(body) if body else {}
        if (method, path) == ("GET", "/labels"):
            return self._ok({"labels": [{"id": i, "name": n} for i, n in self.labels.items()]})
        if (method, path) == ("POST", "/labels"):
            if data["name"] == self.conflict_on:
                self.labels[f"L{len(self.labels)}"] = data["name"]
                return Response(409, b"{}")
            if data["name"].casefold() in {n.casefold() for n in self.labels.values()}:
                return Response(409, b"{}")
            new = f"L{len(self.labels)}"
            self.labels[new] = data["name"]
            return self._ok({"id": new, "name": data["name"]})
        if (method, path) == ("GET", "/settings/filters"):
            return self._ok({"filter": self.filters} if self.filters else {})
        if (method, path) == ("POST", "/settings/filters"):
            self.filters.append({"id": f"F{len(self.filters)}", **data})
            return self._ok(self.filters[-1])
        if (method, path) == ("GET", "/messages"):
            return self._list(urllib.parse.parse_qs(parsed.query))
        if (method, path) == ("POST", "/messages/batchModify"):
            assert len(data["ids"]) <= gmail.MODIFY_BATCH
            for mid in data["ids"]:
                labels = self.messages[mid][1]
                labels |= set(data["addLabelIds"])
                labels -= set(data["removeLabelIds"])
            return Response(204)
        raise AssertionError(f"unexpected request {method} {path}")

    def _list(self, params: dict[str, list[str]]) -> Response:
        query = params["q"][0]
        inbox_only = query.endswith(" in:inbox")
        base = query.removesuffix(" in:inbox")
        found = sorted(m for m, (q, ls) in self.messages.items() if q == base and (not inbox_only or "INBOX" in ls))
        start = int(params.get("pageToken", ["0"])[0])
        chunk = found[start : start + self.page]
        page: dict[str, Any] = {"messages": [{"id": m} for m in chunk]} if chunk else {}
        if start + self.page < len(found):
            page["nextPageToken"] = str(start + self.page)
        return self._ok(page)

    @staticmethod
    def _ok(data: dict[str, Any]) -> Response:
        return Response(200, json.dumps(data).encode())


def _client(box: FakeGmail) -> gmail.GmailClient:
    return gmail.GmailClient(box, "acceso", frozenset(PLAN.labels))


def _statuses(rows: list[dict[str, str]]) -> list[str]:
    return [r["status"] for r in rows]


def test_apply_creates_labels_parents_first_and_one_filter_per_subject():
    box = FakeGmail()
    report = gmail.apply(_client(box), PLAN)
    assert [r["name"] for r in report.labels] == list(PLAN.labels)
    assert _statuses(report.labels) == ["created"] * 4
    assert list(box.labels.values())[1:] == list(PLAN.labels)
    assert _statuses(report.filters) == ["created", "created"]
    by_label = {box.labels[f["action"]["addLabelIds"][0]]: f for f in box.filters}
    for spec in PLAN.filters:
        assert by_label[spec.label]["criteria"] == {"query": spec.query}
        assert by_label[spec.label]["action"]["removeLabelIds"] == ["INBOX"]
    assert report.existing_mail == [
        {"subject": "Mates", "matched": 0, "in_inbox": 0},
        {"subject": "Lengua", "matched": 0, "in_inbox": 0},
    ]


def test_a_second_apply_creates_nothing():
    box = FakeGmail()
    gmail.apply(_client(box), PLAN)
    before = (dict(box.labels), list(box.filters))
    report = gmail.apply(_client(box), PLAN)
    assert _statuses(report.labels) == ["existing"] * 4
    assert _statuses(report.filters) == ["existing", "existing"]
    assert (box.labels, box.filters) == before


def test_an_added_subject_creates_only_its_own():
    box = FakeGmail()
    gmail.apply(_client(box), PLAN)
    wider = mail.plan("1º ESO", ("Mates", "Lengua", "Bio"), "{grade}. {subject}. {topic}")
    report = gmail.apply(gmail.GmailClient(box, "acceso", frozenset(wider.labels)), wider)
    assert _statuses(report.labels) == ["existing"] * 4 + ["created"]
    assert _statuses(report.filters) == ["existing", "existing", "created"]


def test_a_label_in_another_case_is_reused():
    box = FakeGmail(labels={"INBOX": "INBOX", "X1": "alfabeta"})
    report = gmail.apply(_client(box), PLAN)
    assert report.labels[0] == {"name": "Alfabeta", "status": "existing"}
    assert list(box.labels.values()).count("alfabeta") == 1
    assert "Alfabeta" not in box.labels.values()


def test_a_409_on_create_lists_again_and_reuses():
    box = FakeGmail(conflict_on="Alfabeta/1º ESO")
    report = gmail.apply(_client(box), PLAN)
    assert report.labels[1] == {"name": "Alfabeta/1º ESO", "status": "existing"}
    assert list(box.labels.values()).count("Alfabeta/1º ESO") == 1


def test_a_filter_with_another_query_differs_and_is_left_alone():
    box = FakeGmail()
    gmail.apply(_client(box), PLAN)
    box.filters[0]["criteria"]["query"] = "from:someone subject:otra"
    kept = json.dumps(box.filters)
    report = gmail.apply(_client(box), PLAN)
    assert _statuses(report.filters) == ["differs", "existing"]
    assert json.dumps(box.filters) == kept


def test_the_same_query_up_to_spaces_and_case_is_existing():
    box = FakeGmail()
    gmail.apply(_client(box), PLAN)
    box.filters[1]["criteria"]["query"] = "  " + box.filters[1]["criteria"]["query"].upper().replace(" ", "  ")
    assert _statuses(gmail.apply(_client(box), PLAN).filters) == ["existing", "existing"]


def test_existing_notices_get_their_label_and_leave_the_inbox_in_pages_and_batches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(gmail, "MODIFY_BATCH", 2)
    mates, lengua = PLAN.filters
    box = FakeGmail()
    box.messages = {f"m{i}": (mates.query, {"INBOX"}) for i in range(5)}
    box.messages["archived"] = (mates.query, set())
    box.messages["l0"] = (lengua.query, {"INBOX", "STARRED"})
    box.messages["other"] = ("from:someone", {"INBOX"})
    report = gmail.apply(_client(box), PLAN)
    assert report.existing_mail == [
        {"subject": "Mates", "matched": 6, "in_inbox": 5},
        {"subject": "Lengua", "matched": 1, "in_inbox": 1},
    ]
    names = dict(box.labels)
    for mid, (query, labels) in box.messages.items():
        if mid == "other":
            assert labels == {"INBOX"}
            continue
        assert "INBOX" not in labels
        assert {names[i] for i in labels if i in names} == {mates.label if query == mates.query else lengua.label}
    assert "STARRED" in box.messages["l0"][1]
    again = gmail.apply(_client(box), PLAN)
    assert again.existing_mail == [
        {"subject": "Mates", "matched": 6, "in_inbox": 0},
        {"subject": "Lengua", "matched": 1, "in_inbox": 0},
    ]


def test_every_request_is_on_the_allowed_list():
    box = FakeGmail()
    box.messages = {"m0": (PLAN.filters[0].query, {"INBOX"})}
    gmail.apply(_client(box), PLAN)
    assert box.calls
    assert set(box.calls) <= ALLOWED


OFF_THE_LIST: dict[str, Callable[[gmail.GmailClient], object]] = {
    "no sender clause": lambda c: c.message_ids('subject:"1º ESO. Mates."'),
    "other senders": lambda c: c.message_ids("from:(GeminiNotebook-noreply@x.example) is:unread"),
    "filter without senders": lambda c: c.create_filter('subject:"x"', "L1"),
    "label outside the plan": lambda c: c.create_label("Personal"),
    "add the inbox": lambda c: c.move(["m0"], "INBOX"),
    "add a label not ours": lambda c: c.move(["m0"], "L-not-ours"),
}


@pytest.mark.parametrize("case", sorted(OFF_THE_LIST))
def test_a_request_off_the_list_raises_before_anything_is_sent(case: str):
    box = FakeGmail()
    client = _client(box)
    client.labels()
    sent = len(box.calls)
    with pytest.raises(gmail.GuardError):
        OFF_THE_LIST[case](client)
    assert len(box.calls) == sent


def test_the_client_has_no_way_to_read_a_message():
    public = {name for name in dir(gmail.GmailClient) if not name.startswith("_")}
    assert public == {"labels", "create_label", "filters", "create_filter", "message_ids", "move"}
    assert not re.search(r"/messages/\{|/threads|/history|/attachments", Path(gmail.__file__).read_text())


def test_an_api_error_is_raised_with_its_status():
    class Denied:
        def request(self, method: str, url: str, **_: Any) -> Response:
            return Response(403, b"{}")

    with pytest.raises(gmail.GmailError) as err:
        gmail.apply(gmail.GmailClient(Denied(), "acceso", frozenset(PLAN.labels)), PLAN)
    assert err.value.status == 403
