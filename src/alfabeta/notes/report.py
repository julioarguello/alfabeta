"""The family's report of a run that changed something, in Spanish (spec 005 FR-013, research R8).

`write_report` compares the records with the snapshot the last report left in `state.json`
(`reported`) and writes `reports/Informe AAAAMMDD-HHMM.md` at the root of the alfabeta folder only
when that diff is not empty: an idle run writes nothing (SC-004), and a condition that persists, a
spent budget or a photo Claude keeps refusing, is reported once when it starts and once when it
clears (User Story 4, scenario 3). Per topic with new pages, one Claude call says what the pages add
against the study guide of the topic's printable pack, `Tema NN para imprimir · <title>.pdf` in its
`notebook/` folder, read with `pypdf`; its `usage` goes into the month's spend ledger (FR-015). A
comparison the budget, the key or Claude's answer stops waits in the snapshot for the next report; one
that has no pack or no guide to compare with is said in one line and dropped. Nothing here regenerates
a study piece (FR-012): the report says that is the family's decision.
"""

from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, cast

from pypdf import PdfReader

from alfabeta.google.drive import DriveError, OutsideFolderError
from alfabeta.notes.model import Health, ItemState, Kind, LivingKind, PhotoState, Review, SpendLedger, Usage, reportable

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable

    from alfabeta.google.drive import DriveFile
    from alfabeta.notes.run import NotesDeps, Pass
    from alfabeta.notes.transcribe import Transcription

REPORTS_FOLDER = "reports"
NOTEBOOK_FOLDER = "notebook"
MARKDOWN = "text/markdown"
REPORTED = "reported"  # the snapshot's key in state.json
# The study-pack skill's printable pack (its step 10): `Tema NN para imprimir · <title>.pdf`.
_PRINTABLE = re.compile(r"^Tema \d+ para imprimir · .+\.pdf$")
# A piece's heading in that PDF, as `print_pack.py` numbers them: `3 · Guía de estudio · …`.
_PIECE = re.compile(r"^\s*\d+\s*·\s*(.+)$")
_GUIDE = re.compile(r"gu[ií]a", re.IGNORECASE)
_HEAD_LINES = 4  # Chrome's `N / M` footer may come first in a page's extracted text
MAX_GUIDE_CHARS = 30_000
MAX_NOTES_CHARS = 30_000
# What the family reads when nothing is compared (FR-012, FR-015).
NO_PACK = "No hay «Tema NN para imprimir» en la carpeta notebook/ del tema: no se compara con la guía de estudio."
NO_GUIDE = "El PDF para imprimir no tiene una sección de guía de estudio: no se compara."
NO_PDF = "El PDF para imprimir no se puede leer: no se compara con la guía de estudio."
WAITS = "se compara en el próximo informe"
NO_BUDGET = f"No se compara con la guía de estudio: el presupuesto mensual de IA está agotado; {WAITS}."
NO_KEY = f"No se compara con la guía de estudio: este sitio no tiene clave de Claude; {WAITS}."
NO_ANSWER = f"No se compara con la guía de estudio: Claude o Drive no respondieron; {WAITS}."
DECISION = (
    "Regenerar las piezas del pack (vídeos, cuestionario, guía) gasta cuota del cuaderno: es decisión de la familia."
)
NOTHING_TO_ADD = "Nada que añadir."

INSTRUCTIONS = """\
You compare a student's new handwritten class notes with the study guide of the same topic.
Answer in Spanish, for the student's family, as Markdown bullets, twelve lines at most:

- an idea, a method or a procedure the notes stress that the guide does not cover, each named plainly;
- a definition or a rule the notes state differently from the guide, with both forms.

When the guide covers everything the notes say, answer only the single line: Nada que añadir.
Name no person. Write nothing that is not in the notes or in the guide. No introduction, no closing.

<notes>
{notes}
</notes>

<guide>
{guide}
</guide>"""

# Per-file states the report lists, in Spanish, singular and plural (FR-013).
_PHOTO_LINES = {
    PhotoState.IN_LIVING_FILE: ("página nueva en el archivo vivo", "páginas nuevas en el archivo vivo"),
    PhotoState.TRANSCRIBED: (
        "página transcrita que espera su archivo vivo",
        "páginas transcritas que esperan su archivo vivo",
    ),
    PhotoState.DUPLICATE: ("foto repetida (ya tenía página)", "fotos repetidas (ya tenían página)"),
    PhotoState.UNSUPPORTED: ("foto en un formato no admitido", "fotos en un formato no admitido"),
    PhotoState.UNREADABLE: ("foto ilegible", "fotos ilegibles"),
    PhotoState.GONE: (
        "foto retirada de Drive (su página se conserva)",
        "fotos retiradas de Drive (sus páginas se conservan)",
    ),
    PhotoState.FAILED: (
        "foto que falló al transcribirse (se reintenta)",
        "fotos que fallaron al transcribirse (se reintentan)",
    ),
    PhotoState.FAILED_FINAL: (
        "foto que se dejó de reintentar: cámbiala o súbela de nuevo",
        "fotos que se dejaron de reintentar: cámbialas o súbelas de nuevo",
    ),
}
_ITEM_LINES = {
    ItemState.IN_LIVING_FILE: (
        "material de Classroom nuevo en el archivo vivo",
        "materiales de Classroom nuevos en el archivo vivo",
    ),
    ItemState.GONE: (
        "material de Classroom retirado (sale del archivo vivo)",
        "materiales de Classroom retirados (salen del archivo vivo)",
    ),
    ItemState.FAILED: (
        "material de Classroom que Drive no pudo leer (se reintenta)",
        "materiales de Classroom que Drive no pudo leer (se reintentan)",
    ),
    ItemState.FAILED_FINAL: (
        "material de Classroom que se dejó de reintentar: cámbialo o súbelo de nuevo",
        "materiales de Classroom que se dejaron de reintentar: cámbialos o súbelos de nuevo",
    ),
}
_REVIEW_LINES = {
    Review.CHECKED: (
        "transcripción marcada como revisada por el alumno",
        "transcripciones marcadas como revisadas por el alumno",
    ),
    Review.WRONG: ("transcripción marcada como mal por el alumno", "transcripciones marcadas como mal por el alumno"),
}
_COUNT_LINES = {
    "unexpected": ("fichero fuera de sitio en la carpeta del tema", "ficheros fuera de sitio en la carpeta del tema"),
}
# Conditions that last: said once when they start and once when they clear (scenario 3).
_CONDITIONS = {
    "budget": "el presupuesto mensual de IA está agotado: transcribir y comparar esperan y se reintentan cada día",
    "no_key": "este sitio no tiene clave de Claude: las fotos esperan",
    "drive_write": "Drive no aceptó una escritura: lo pendiente se reintenta en la próxima ejecución",
}
_LIVING_CONDITIONS = {
    "missing": "el archivo vivo «{name}» no está donde se creó: no se actualiza",
    "over": "el archivo vivo «{name}» supera las {pages} páginas",
}
_WAITING_SETUP = "el tema espera a que se cree su cuaderno («notebook setup»)"
SETUP = "setup"  # the snapshot's key, beside the living kinds, for a topic waiting for setup
STARTS, CLEARS = "Comienza", "Resuelto"


class ReportDrive(Protocol):
    """What the report needs of spec 004's `ScopedDrive`."""

    @property
    def root(self) -> DriveFile:
        """The alfabeta folder."""
        ...

    def listed(self, item_id: str) -> DriveFile:
        """The item as the run's listing holds it."""
        ...

    def contains(self, item_id: str) -> bool:
        """Whether the item is under the root, as listed this run."""
        ...

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        """The item with that name in the folder, asked of Drive now."""
        ...

    def create_folder(self, parent_id: str, name: str) -> DriveFile:
        """A new folder."""
        ...

    def children(self, folder_id: str) -> list[DriveFile]:
        """What this run's listing found directly inside the folder."""
        ...

    def content(self, file_id: str) -> bytes:
        """The file's bytes."""
        ...

    def upload(
        self, parent_id: str, name: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        """A new file, confirmed."""
        ...

    def update(
        self, file_id: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        """New content on the same id, confirmed."""
        ...


@dataclass
class TopicChanges:
    """What one topic's section says."""

    name: str
    lines: list[str] = field(default_factory=lambda: [])
    new_pages: list[str] = field(default_factory=lambda: [])  # photo ids to compare: new, or waiting since a report
    started: list[str] = field(default_factory=lambda: [])
    cleared: list[str] = field(default_factory=lambda: [])

    @property
    def empty(self) -> bool:
        """Whether nothing of it is worth a report."""
        return not (self.lines or self.started or self.cleared)


@dataclass
class Changes:
    """The diff between the records and the last report's snapshot."""

    topics: dict[str, TopicChanges] = field(default_factory=lambda: {})
    started: list[str] = field(default_factory=lambda: [])
    cleared: list[str] = field(default_factory=lambda: [])

    @property
    def empty(self) -> bool:
        """Whether the run changed nothing the family should hear of (scenario 1)."""
        return not (self.started or self.cleared) and all(t.empty for t in self.topics.values())


def report_name(started: dt.datetime) -> str:
    """`Informe AAAAMMDD-HHMM.md`, in the run's own zone (`Europe/Madrid`)."""
    return f"Informe {started:%Y%m%d-%H%M}.md"


def _plural(n: int, forms: tuple[str, str]) -> str:
    return f"{n} {forms[0] if n == 1 else forms[1]}"


def snapshot(state: dict[str, Any], work: Pass, warn_pages: int) -> dict[str, Any]:
    """What the next report compares against: every file's state, every page's review, the conditions."""
    files = cast("dict[str, dict[str, Any]]", state.get("files", {}))
    pages = cast("dict[str, dict[str, Any]]", state.get("pages", {}))
    topics = cast("dict[str, dict[str, Any]]", state.get("topics", {}))
    living: dict[str, dict[str, str]] = {}
    for topic, record in topics.items():
        waiting = topic in work.counts and work.counts[topic]["waiting_setup"] > 0
        living.setdefault(topic, {})[SETUP] = "waiting" if waiting else "none"
        for kind in LivingKind:
            found = cast("dict[str, Any] | None", record.get("living", {}).get(kind))
            if found is None or found.get("file_id") is None:
                condition = "none"
            elif found.get("health") == Health.MISSING:
                condition = "missing"
            elif int(found.get("pages", 0)) > warn_pages:
                condition = "over"
            else:
                condition = "ok"
            living.setdefault(topic, {})[kind] = condition
    budget = work.budget_refused or any(
        r.get("state") == PhotoState.BUDGET_WAIT for r in files.values() if r.get("kind") == Kind.NOTES_PHOTO
    )
    # A refusal of the report's own call leaves no photo waiting: it holds until a call is answered.
    held = cast("dict[str, Any]", state.get(REPORTED, {})).get("conditions", {}).get("budget", False)
    budget = budget or (bool(held) and not work.claude_answered)
    return {
        "files": {fid: str(r["state"]) for fid, r in sorted(files.items()) if "state" in r},
        "pages": {fid: str(p.get("review", Review.AUTOMATIC)) for fid, p in sorted(pages.items())},
        "living": living,
        "conditions": {"budget": budget, "no_key": work.no_key, "drive_write": work.write_failed},
        "compare": {},
    }


def baseline(state: dict[str, Any], work: Pass, warn_pages: int) -> None:
    """Before the first report, take the records as they are as already reported.

    A topic with pages before this module existed is not reported, nor compared, as new on the first
    run that changes something; what that run changes is.
    """
    if REPORTED not in state and state.get("files"):
        state[REPORTED] = snapshot(state, work, warn_pages)


def diff(state: dict[str, Any], work: Pass, before: dict[str, Any], now: dict[str, Any]) -> Changes:
    """The state changes since the last report (FR-013), classified for the family."""
    files = cast("dict[str, dict[str, Any]]", state.get("files", {}))
    topics = cast("dict[str, dict[str, Any]]", state.get("topics", {}))
    changes = Changes()

    def section(topic: str) -> TopicChanges:
        if topic not in changes.topics:
            changes.topics[topic] = TopicChanges(str(topics.get(topic, {}).get("name", "tema")))
        return changes.topics[topic]

    counted: dict[str, Counter[str]] = {}  # per topic: `photo:<state>`, `item:<state>`, `review:<review>`, a count
    old_files = cast("dict[str, str]", before.get("files", {}))
    for fid, after in cast("dict[str, str]", now["files"]).items():
        if not reportable(old_files.get(fid), after):
            continue
        record = files[fid]
        topic = str(record.get("living") or record["topic"])
        if record["kind"] == Kind.NOTES_PHOTO:
            state_now = PhotoState(after)
            paged = (PhotoState.TRANSCRIBED, PhotoState.IN_LIVING_FILE)
            if state_now in paged and old_files.get(fid) not in paged:
                section(topic).new_pages.append(fid)  # once: not again when a waiting page reaches its file
            if state_now in _PHOTO_LINES:
                counted.setdefault(topic, Counter())[f"photo:{state_now}"] += 1
        elif record["kind"] == Kind.CLASSROOM_ITEM and ItemState(after) in _ITEM_LINES:
            counted.setdefault(topic, Counter())[f"item:{after}"] += 1
    old_pages = cast("dict[str, str]", before.get("pages", {}))
    for fid, review in cast("dict[str, str]", now["pages"]).items():
        if reportable(old_pages.get(fid), review) and Review(review) in _REVIEW_LINES and fid in files:
            counted.setdefault(str(files[fid]["topic"]), Counter())[f"review:{review}"] += 1
    for topic, counts in work.counts.items():
        for what in _COUNT_LINES:
            if counts.get(what):
                counted.setdefault(topic, Counter())[f"count:{what}"] = counts[what]
    for topic, items in counted.items():
        lines = section(topic).lines
        for key, n in items.items():
            kind, _, value = key.partition(":")
            if kind == "photo":
                lines.append(_plural(n, _PHOTO_LINES[PhotoState(value)]))
            elif kind == "item":
                lines.append(_plural(n, _ITEM_LINES[ItemState(value)]))
            elif kind == "review":
                lines.append(_plural(n, _REVIEW_LINES[Review(value)]))
            else:
                lines.append(_plural(n, _COUNT_LINES[value]))
    old_living = cast("dict[str, dict[str, str]]", before.get("living", {}))
    for topic, kinds in cast("dict[str, dict[str, str]]", now["living"]).items():
        for kind, condition in kinds.items():
            was = old_living.get(topic, {}).get(kind, "none")
            if was == condition:
                continue
            if kind == SETUP:
                (section(topic).started if condition == "waiting" else section(topic).cleared).append(_WAITING_SETUP)
                continue
            name = f"{LivingKind(kind).prefix} · {topics[topic]['name']}.pdf"
            pages = cast("dict[str, Any]", topics[topic].get("living", {}).get(kind, {})).get("pages", 0)
            if condition in _LIVING_CONDITIONS:
                section(topic).started.append(_LIVING_CONDITIONS[condition].format(name=name, pages=pages))
            if was in _LIVING_CONDITIONS:
                section(topic).cleared.append(_LIVING_CONDITIONS[was].format(name=name, pages=pages))
    _conditions(changes, before, now)
    return changes


def _conditions(changes: Changes, before: dict[str, Any], now: dict[str, Any]) -> None:
    """The run-wide conditions that start or clear (scenario 3)."""
    old = cast("dict[str, bool]", before.get("conditions", {}))
    changes.started = [t for k, t in _CONDITIONS.items() if now["conditions"][k] and not old.get(k, False)]
    changes.cleared = [t for k, t in _CONDITIONS.items() if old.get(k, False) and not now["conditions"][k]]


# --- "what it adds" (research R8) --------------------------------------------------------------------


def printable_pack(drive: ReportDrive, topic: str) -> DriveFile | None:
    """The topic's `Tema NN para imprimir · <title>.pdf` in its `notebook/`, or None."""
    try:
        listed = drive.children(topic)
    except OutsideFolderError:
        return None  # moved out of the alfabeta folder or trashed since its pages arrived
    for folder in listed:
        if folder.is_folder and folder.name == NOTEBOOK_FOLDER:
            found = [f for f in drive.children(folder.id) if not f.is_folder and _PRINTABLE.match(f.name)]
            return sorted(found, key=lambda f: f.name)[0] if found else None
    return None


def guide_section(pdf: bytes) -> str | None:
    """The study guide's pages of the printable pack, as text; None when no piece is a guide.

    `print_pack.py` prints the index first and then each piece on a new page under its numbered title.
    A page opens a piece when one of its first lines is such a title; the guide runs from its own
    opening page to the page before the next piece's.
    """
    pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages]
    opening: list[str | None] = []
    for text in pages:
        head = [line.strip() for line in text.splitlines() if line.strip()][:_HEAD_LINES]
        titles = [m.group(1) for line in head if (m := _PIECE.match(line))]
        opening.append(titles[0] if titles else None)
    start = next((i for i, title in enumerate(opening) if i > 0 and title and _GUIDE.search(title)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(pages)) if opening[i]), len(pages))
    return "\n".join(pages[start:end]).strip()[:MAX_GUIDE_CHARS]


# What `_what_it_adds` says when the comparison waits for the next report rather than being dropped.
_DEFERRED = frozenset({NO_BUDGET, NO_KEY, NO_ANSWER})


def _what_it_adds(deps: NotesDeps, work: Pass, topic: str, section: TopicChanges, *, spent: bool) -> list[str]:
    """The topic's "what it adds" paragraph: one call, or the one line saying why there is none."""
    pack = printable_pack(deps.drive, topic)
    if pack is None:
        return [NO_PACK]
    try:
        data = deps.drive.content(pack.id)
    except DriveError:
        return [NO_ANSWER]
    try:
        guide = guide_section(data)
    except Exception:  # a third-party parser over a file the run did not write: PyPdfError and others
        return [NO_PDF]  # damaged, encrypted or unusual: the run goes on (FR-013 reports, never stops)
    if guide is None:
        return [NO_GUIDE]
    if deps.answerer is None:
        return [NO_KEY]
    if spent or work.budget_refused:
        return [NO_BUDGET]
    pages = cast("dict[str, dict[str, Any]]", work.state.get("pages", {}))
    notes = "\n\n".join(str(pages[p]["markdown"]) for p in section.new_pages if p in pages)[:MAX_NOTES_CHARS]
    try:
        done: Transcription = deps.answerer.answer(INSTRUCTIONS.format(notes=notes, guide=guide))
    except ValueError:
        return [NO_ANSWER]  # an answer that is not the JSON of the Messages API
    if done.usage is not None:
        _spend(work, done.usage)
    if done.state == PhotoState.BUDGET_WAIT:
        work.budget_refused = True
        return [NO_BUDGET]
    work.claude_answered = work.claude_answered or done.usage is not None
    if done.state != PhotoState.TRANSCRIBED:
        return [NO_ANSWER]
    compared = f"Comparadas {_plural(len(section.new_pages), ('página nueva', 'páginas nuevas'))} con la guía de estudio de «{pack.name}»."
    return [compared, "", done.markdown.strip(), "", DECISION]


def _spend(work: Pass, usage: Usage) -> None:
    """One more call in the month's ledger (FR-015, research R8)."""
    months = cast("dict[str, dict[str, int]]", work.state.get("spend", {}))
    ledger = SpendLedger({m: Usage(u["in"], u["out"]) for m, u in months.items()}).add(work.today[:7], usage)
    work.state["spend"] = {m: {"in": u.tokens_in, "out": u.tokens_out} for m, u in ledger.months.items()}


# --- the report ----------------------------------------------------------------------------------------


def _usage_of(months: dict[str, Any], month: str) -> Usage:
    found = cast("dict[str, int]", months.get(month, {}))
    return Usage(int(found.get("in", 0)), int(found.get("out", 0)))


def _number(n: int) -> str:
    """Spanish thousands: 3.000."""
    return f"{n:,}".replace(",", ".")


def _usd(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " USD"


def render(deps: NotesDeps, work: Pass, started: dt.datetime, changes: Changes, adds: dict[str, list[str]]) -> str:
    """The report's Markdown, in Spanish; topic names and counts, never an id or an address."""
    where = "en la nube" if str(deps.ran_on) == "cloud" else "en el Mac"
    lines = [f"# Informe de apuntes · {started:%d/%m/%Y %H:%M}", "", f"Ejecución {where}."]
    for topic in sorted(changes.topics, key=lambda t: changes.topics[t].name):
        section = changes.topics[topic]
        if section.empty and topic not in adds:
            continue
        lines += ["", f"## {section.name}", ""]
        lines += [f"- {line}." for line in section.lines]
        lines += [f"- {STARTS}: {line}." for line in section.started]
        lines += [f"- {CLEARS}: {line}." for line in section.cleared]
        if topic in adds:
            lines += ["", "### Qué aportan los apuntes nuevos", "", *adds[topic]]
    if changes.started or changes.cleared:
        lines += ["", "## Avisos", ""]
        lines += [f"- {STARTS}: {line}." for line in changes.started]
        lines += [f"- {CLEARS}: {line}." for line in changes.cleared]
    month = started.strftime("%Y-%m")
    after = _usage_of(cast("dict[str, Any]", work.state.get("spend", {})), month)
    before = _usage_of(work.spent_before, month)
    run_usage = Usage(after.tokens_in - before.tokens_in, after.tokens_out - before.tokens_out)
    cost = SpendLedger({month: after}).cost(month, deps.prices)
    lines += [
        "",
        "## Gasto en IA",
        "",
        f"- Esta ejecución: {_number(run_usage.tokens_in)} tokens de entrada y {_number(run_usage.tokens_out)} de salida.",
        f"- Mes {month}: {_usd(cost)} al precio configurado; la referencia es la página de costes de la Console.",
    ]
    return "\n".join(lines) + "\n"


def _upload(drive: ReportDrive, name: str, text: str) -> None:
    """Into `reports/`, made when missing; the same name again is updated, not duplicated (research R4)."""
    folder = drive.lookup(drive.root.id, REPORTS_FOLDER) or drive.create_folder(drive.root.id, REPORTS_FOLDER)
    found = drive.lookup(folder.id, name)
    if found is not None:
        drive.update(found.id, text.encode(), MARKDOWN)
    else:
        drive.upload(folder.id, name, text.encode(), MARKDOWN)


def write_report(deps: NotesDeps, work: Pass, started: dt.datetime) -> str | None:
    """Write the report if the run changed something; the text written, or None (scenario 1).

    The snapshot moves only once the report is in Drive, so a failed upload is reported again, whole,
    by the next run that writes one.
    """
    before = cast("dict[str, Any]", work.state.get(REPORTED, {}))
    now = snapshot(work.state, work, deps.warn_pages)
    changes = diff(work.state, work, before, now)
    if changes.empty:
        return None  # a comparison waiting from an earlier report waits for one with something new
    topics = cast("dict[str, dict[str, Any]]", work.state.get("topics", {}))
    for topic, waiting in sorted(cast("dict[str, list[str]]", before.get("compare", {})).items()):
        if not deps.drive.contains(topic) or topic not in topics:
            continue  # the topic left the alfabeta folder: its waiting comparison goes with it
        if topic not in changes.topics:
            changes.topics[topic] = TopicChanges(str(topics.get(topic, {}).get("name", "tema")))
        new = changes.topics[topic].new_pages
        changes.topics[topic].new_pages = [*waiting, *(p for p in new if p not in waiting)]
    # Spent today: a photo was refused this pass, or the report's own call was, on an earlier run of the
    # same day. A budget held from another day is probed once by the comparison (research R5: a day).
    files = cast("dict[str, dict[str, Any]]", work.state.get("files", {}))
    refused_today = work.budget_refused or any(r.get("state") == PhotoState.BUDGET_WAIT for r in files.values())
    spent = refused_today or (now["conditions"]["budget"] and before.get("budget_day") == work.today)
    adds = {
        topic: _what_it_adds(deps, work, topic, section, spent=spent)
        for topic, section in sorted(changes.topics.items())
        if section.new_pages
    }
    now["compare"] = {t: changes.topics[t].new_pages for t, said in adds.items() if said[0] in _DEFERRED}
    if work.budget_refused:
        now["conditions"]["budget"] = True  # the comparison itself met the spent budget
    if now["conditions"]["budget"]:
        now["budget_day"] = work.today if work.budget_refused else before.get("budget_day", work.today)
    _conditions(changes, before, now)
    text = render(deps, work, started, changes, adds)
    _upload(deps.drive, report_name(started), text)
    work.state[REPORTED] = now
    return text


def scan_text(text: str) -> Iterable[tuple[int, str]]:
    """The report's lines numbered as the guardrail reads a file (SC-008, T035)."""
    return enumerate(text.splitlines(), start=1)
