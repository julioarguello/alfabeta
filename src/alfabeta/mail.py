"""The student's mailbox: labels and filters for the notices of shared notebooks (spec 010).

Pure: the plan comes from the configuration alone, and the import file is written from the plan. The
Gmail adapter that applies it is `alfabeta.google.gmail`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

ROOT_LABEL = "Alfabeta"
# Who mails a notebook's notices (research R1). Written in two parts: an address is personal data to
# the guardrail, and these two are Google's, not anybody's.
_DOMAIN = "google.com"
SENDERS = (f"GeminiNotebook-noreply@{_DOMAIN}", f"NotebookLM-noreply@{_DOMAIN}")
SENDER_CLAUSE = "from:(" + " OR ".join(SENDERS) + ")"
_ATOM = "http://www.w3.org/2005/Atom"
_APPS = "http://schemas.google.com/apps/2006"


class MailError(Exception):
    """The plan cannot be made or written; `reason` is the CLI's code."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class FilterSpec:
    """One subject's filter: notices whose subject holds its title prefix get its label, out of the inbox."""

    subject: str
    label: str
    query: str


@dataclass(frozen=True)
class MailPlan:
    """The labels, parents first, and one filter per subject (FR-002, FR-004)."""

    labels: tuple[str, ...]
    filters: tuple[FilterSpec, ...]


def title_prefix(pattern: str, grade: str, subject: str) -> str:
    """The part of a notebook title that names grade and subject: the pattern cut before `{topic}` (FR-003)."""
    head, found, _ = pattern.partition("{topic}")
    if not found or "{grade}" not in head or "{subject}" not in head:
        raise MailError(
            "invalid_title_pattern", "the notebook title pattern needs {grade} and {subject} before {topic}"
        )
    return head.replace("{grade}", grade).replace("{subject}", subject).strip()


def _words(text: str) -> list[str]:
    """Gmail's view of a phrase: punctuation ignored, case ignored."""
    return "".join(c if c.isalnum() else " " for c in text.casefold()).split()


def _phrase(prefix: str) -> str:
    return 'subject:"' + prefix.replace('"', "") + '"'


def plan(grade: str, subjects: tuple[str, ...], title_pattern: str) -> MailPlan:
    """The plan for one student's grade and subject folders, in configuration order."""
    grade_label = f"{ROOT_LABEL}/{grade}"
    prefixes = {s: title_prefix(title_pattern, grade, s) for s in subjects}
    filters: list[FilterSpec] = []
    for subject, prefix in prefixes.items():
        mine = _words(prefix)
        # A longer subject whose words start with this one's would match its phrase too (FR-004).
        longer = [p for s, p in prefixes.items() if s != subject and len(_words(p)) > len(mine)]
        exclusions = [p for p in longer if _words(p)[: len(mine)] == mine]
        query = " ".join([SENDER_CLAUSE, _phrase(prefix), *("-" + _phrase(p) for p in exclusions)])
        filters.append(FilterSpec(subject, f"{grade_label}/{subject}", query))
    return MailPlan((ROOT_LABEL, grade_label, *(f.label for f in filters)), tuple(filters))


def import_file(mail_plan: MailPlan) -> bytes:
    """Gmail's filter export format, one entry per subject (FR-010)."""
    ET.register_namespace("", _ATOM)
    ET.register_namespace("apps", _APPS)
    feed = ET.Element(f"{{{_ATOM}}}feed")
    ET.SubElement(feed, f"{{{_ATOM}}}title").text = "Mail Filters"
    for spec in mail_plan.filters:
        entry = ET.SubElement(feed, f"{{{_ATOM}}}entry")
        ET.SubElement(entry, f"{{{_ATOM}}}category", term="filter")
        ET.SubElement(entry, f"{{{_ATOM}}}title").text = "Mail Filter"
        ET.SubElement(entry, f"{{{_ATOM}}}content")
        for name, value in (("hasTheWord", spec.query), ("label", spec.label), ("shouldArchive", "true")):
            ET.SubElement(entry, f"{{{_APPS}}}property", name=name, value=value)
    return ET.tostring(feed, encoding="utf-8", xml_declaration=True)


def write_import_file(mail_plan: MailPlan, out: Path) -> None:
    """Write the import file, or MailError `invalid_out`."""
    try:
        out.write_bytes(import_file(mail_plan))
    except OSError:
        raise MailError("invalid_out", "the filter file could not be written there") from None
