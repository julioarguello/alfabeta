"""The student's Gmail, reached only for labels and filters (spec 010 FR-008).

The client makes four kinds of request and no other: list and create labels, list and create filters,
list message ids by one of the plan's queries, and change the labels of messages it listed.
It never fetches a message, a thread, an attachment or a history. Every guard raises before a request
is sent.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from alfabeta.mail import SENDER_CLAUSE

if TYPE_CHECKING:
    from alfabeta.google.transport import HttpTransport
    from alfabeta.mail import MailPlan

API = "https://gmail.googleapis.com/gmail/v1/users/me"
INBOX = "INBOX"
INBOX_ONLY = " in:inbox"  # the one suffix a planned query may carry, to count what is in the inbox
LIST_PAGE = 500  # messages.list's maximum
MODIFY_BATCH = 1000  # messages.batchModify's maximum
MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"  # labels, the list and the labels of messages
SETTINGS_SCOPE = "https://www.googleapis.com/auth/gmail.settings.basic"  # filters
SCOPES = (SETTINGS_SCOPE, MODIFY_SCOPE)


class GmailError(Exception):
    """The Gmail API answered with an error status."""

    def __init__(self, status: int) -> None:
        super().__init__(f"gmail API returned {status}")
        self.status = status


class GuardError(Exception):
    """A request off spec 010 FR-008's list; nothing was sent."""


class GmailClient:
    """One mailbox, one access token, the plan's labels and queries, and nothing else."""

    def __init__(self, transport: HttpTransport, token: str, mail_plan: MailPlan) -> None:
        self._transport = transport
        self._token = token
        self._allowed = frozenset(name.casefold() for name in mail_plan.labels)
        self._queries = frozenset(f.query for f in mail_plan.filters)
        self._label_ids: set[str] = set()  # ids of allowed labels, learnt from list or create
        self._listed: set[str] = set()  # message ids a planned query returned

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token}"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        resp = self._transport.request(method, f"{API}{path}", headers=headers, body=data)
        if resp.status >= 400:
            raise GmailError(resp.status)
        return cast("dict[str, Any]", json.loads(resp.body)) if resp.body else {}

    def labels(self) -> dict[str, str]:
        """Every label's name to its id; remembers the ids of the allowed ones."""
        found = cast("list[dict[str, str]]", self._call("GET", "/labels").get("labels", []))
        names = {label["name"]: label["id"] for label in found}
        self._label_ids |= {i for n, i in names.items() if n.casefold() in self._allowed}
        return names

    def create_label(self, name: str) -> str:
        """Create one of the plan's labels; returns its id."""
        if name.casefold() not in self._allowed:
            raise GuardError("a label outside the plan")
        created = self._call("POST", "/labels", {"name": name})
        self._label_ids.add(str(created["id"]))
        return str(created["id"])

    def filters(self) -> list[dict[str, Any]]:
        """Every filter of the mailbox."""
        return cast("list[dict[str, Any]]", self._call("GET", "/settings/filters").get("filter", []))

    def create_filter(self, query: str, label_id: str) -> None:
        """A filter that adds one alfabeta label and removes the inbox, and nothing else."""
        self._check_query(query)
        self._check_label(label_id)
        action = {"addLabelIds": [label_id], "removeLabelIds": [INBOX]}
        self._call("POST", "/settings/filters", {"criteria": {"query": query}, "action": action})

    def message_ids(self, query: str) -> list[str]:
        """Ids of the messages matching the query, spam and trash excluded; never their content."""
        self._check_query(query)
        ids: list[str] = []
        token = ""
        while True:
            params = {"q": query, "maxResults": str(LIST_PAGE), "fields": "messages/id,nextPageToken"}
            if token:
                params["pageToken"] = token
            page = self._call("GET", "/messages?" + urllib.parse.urlencode(params))
            ids += [str(m["id"]) for m in cast("list[dict[str, str]]", page.get("messages", []))]
            token = str(page.get("nextPageToken", ""))
            if not token:
                self._listed.update(ids)
                return ids

    def move(self, ids: list[str], label_id: str) -> None:
        """Add one alfabeta label to the messages and take them out of the inbox."""
        self._check_label(label_id)
        if not set(ids) <= self._listed:
            raise GuardError("a message no planned query listed")
        for start in range(0, len(ids), MODIFY_BATCH):
            body = {"ids": ids[start : start + MODIFY_BATCH], "addLabelIds": [label_id], "removeLabelIds": [INBOX]}
            self._call("POST", "/messages/batchModify", body)

    def _check_query(self, query: str) -> None:
        planned = query.removesuffix(INBOX_ONLY)
        if planned not in self._queries or not planned.startswith(SENDER_CLAUSE + " "):
            raise GuardError("a query that is not one of the plan's")

    def _check_label(self, label_id: str) -> None:
        if label_id not in self._label_ids:
            raise GuardError("a label outside the plan")


def _normalised(query: str) -> str:
    return " ".join(query.split()).casefold()


@dataclass
class ApplyReport:
    """What `mail apply` found and did (spec 010 data model)."""

    labels: list[dict[str, str]] = field(default_factory=lambda: [])
    filters: list[dict[str, str]] = field(default_factory=lambda: [])
    existing_mail: list[dict[str, Any]] = field(default_factory=lambda: [])

    def as_json(self) -> dict[str, Any]:
        """The report's JSON shape."""
        return {"labels": self.labels, "filters": self.filters, "existing_mail": self.existing_mail}


def apply(client: GmailClient, mail_plan: MailPlan) -> ApplyReport:
    """Create what is missing, then move the notices already there (FR-005 to FR-009)."""
    report = ApplyReport()
    by_name = {name.casefold(): label_id for name, label_id in client.labels().items()}
    ids: dict[str, str] = {}
    for name in mail_plan.labels:  # parents first
        if name.casefold() in by_name:
            ids[name] = by_name[name.casefold()]
            report.labels.append({"name": name, "status": "existing"})
            continue
        try:
            ids[name] = client.create_label(name)
        except GmailError as err:
            if err.status != 409:
                raise
            by_name = {n.casefold(): i for n, i in client.labels().items()}
            ids[name] = by_name[name.casefold()]  # a 409 we cannot read again is a KeyError: a bug, not a state
            report.labels.append({"name": name, "status": "existing"})
            continue
        report.labels.append({"name": name, "status": "created"})
    existing = client.filters()
    for spec in mail_plan.filters:
        label_id = ids[spec.label]
        mine = [
            f for f in existing if label_id in cast("dict[str, list[str]]", f.get("action", {})).get("addLabelIds", [])
        ]
        if not mine:
            client.create_filter(spec.query, label_id)
            status = "created"
        elif any(_normalised(str(f.get("criteria", {}).get("query", ""))) == _normalised(spec.query) for f in mine):
            status = "existing"
        else:
            status = "differs"
        report.filters.append({"subject": spec.subject, "status": status})
    moved: list[dict[str, Any]] = []
    for spec in mail_plan.filters:
        matched = client.message_ids(spec.query)
        in_inbox = client.message_ids(spec.query + INBOX_ONLY)
        client.move(matched, ids[spec.label])
        moved.append({"subject": spec.subject, "matched": len(matched), "in_inbox": len(in_inbox)})
    report.existing_mail = moved
    return report
