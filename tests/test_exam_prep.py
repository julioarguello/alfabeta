"""`exam prep` with an invented student and a fake `nlm` (spec 002 US7, contracts/cli.md).

The fake answers `nlm` at the runner, as the command line would, so the adapter's command lines are
tested with the flow. No test calls nlm, Drive, pandoc or Chrome: the printer writes blank PDFs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter

from alfabeta import __main__ as cli_main
from alfabeta import sandbox
from alfabeta.exam import prompts
from alfabeta.exam.cli import cmd_exam_prep
from alfabeta.exam.drive import living_notes_of
from alfabeta.exam.nlm import NlmError, NlmNotebook
from alfabeta.exam.prep import (
    POLL_SECONDS,
    SOURCE_SETTLE_SECONDS,
    ExamDeps,
    LivingNotes,
    LivingNotesError,
    Refusal,
    Slot,
    topic_number,
)
from alfabeta.exam.printing import PrintPack, refresh_mirrors
from alfabeta.google.drive import DriveFile
from tests.conftest import MemoryStore

STUDENT = "sample"
PROFILE = "prueba"
TODAY = dt.date(2026, 10, 28)
TOPIC = "Tema 01 - Materia inventada"
NOTEBOOK_TITLE = f"3º ESO. FyQ. {TOPIC}"
EXAM_DAY = "2026-11-05"  # a Thursday
ANNOUNCED = "20261020"
SCOPE = "Examen del tema 1 el jueves 5: densidad {y} concentración, y los problemas de la ficha."
NOTE_PATH = f"2026-2027/FyQ/{ANNOUNCED} - No topic/classroom/{ANNOUNCED} - aviso - Examen del tema 1 el jueves.md"
PLACEHOLDERS = re.compile(r"\{(grade|language|subject|exam_day|scope|scope_date|slot|pages|theory)\}")


@dataclass
class Art:
    id: str
    type: str
    title: str
    status: str = "completed"
    created_at: str = "2026-10-25T09:00:00Z"
    polls_left: int = 1  # status polls before it completes; -1 never


@dataclass
class FakeNlm:
    """Answers `nlm` commands the way 0.15.8 does, keeping a notebook's Studio and notes."""

    session: int = 0
    default: str = PROFILE
    notebooks: list[dict[str, str]] = field(default_factory=lambda: [{"id": "nb-1", "title": NOTEBOOK_TITLE}])
    studio: list[Art] = field(default_factory=lambda: [])
    notes: list[dict[str, str]] = field(default_factory=lambda: [])
    never: set[str] = field(default_factory=lambda: set())  # report kinds that never complete
    missing: bool = False
    calls: list[list[str]] = field(default_factory=lambda: [])
    made: int = 0

    def __call__(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        if self.missing:
            raise FileNotFoundError("nlm")
        self.calls.append(argv)
        verb, rest = argv[1:3], argv[3:]
        if verb[0] != "config":
            assert argv[-2:] == ["--profile", PROFILE], argv
        if verb == ["login", "--check"]:
            return self._done(self.session, "")
        if verb == ["config", "get"]:
            return self._done(0, f"{self.default}\n")
        if verb == ["notebook", "list"]:
            return self._done(0, json.dumps(self.notebooks))
        if verb == ["studio", "status"]:
            for art in self.studio:
                if art.status == "in_progress" and art.polls_left > 0:
                    art.polls_left -= 1
                    art.status = "completed" if art.polls_left == 0 else art.status
            listed = [vars(a) | {"artifact_id": a.id} for a in self.studio]
            return self._done(0, json.dumps(listed))
        if verb == ["report", "create"]:
            self.made += 1
            fmt = rest[rest.index("--format") + 1]
            prompt = rest[rest.index("--prompt") + 1] if "--prompt" in rest else ""
            kind = "guide" if fmt == "Study Guide" else "theory" if "Hoja de teoría" in prompt else "problems"
            art = Art(f"art-{self.made}", "report", "Informe sin título", "in_progress", "2026-10-28T16:00:00Z")
            art.polls_left = -1 if kind in self.never else 1
            self.studio.append(art)
            return self._done(0, json.dumps({"artifact_id": art.id, "status": "in_progress"}))
        if verb == ["studio", "rename"]:
            next(a for a in self.studio if a.id == rest[0]).title = rest[1]
            return self._done(0, "renamed")
        if verb == ["studio", "delete"]:
            self.studio = [a for a in self.studio if a.id != rest[1]]
            return self._done(0, "deleted")
        if verb == ["note", "list"]:
            return self._done(0, json.dumps({"notes": self.notes, "count": len(self.notes)}))
        if verb == ["note", "create"]:
            self.notes.append({"id": "note-1", "title": rest[rest.index("--title") + 1]})
            return self._done(0, "created")
        if verb == ["note", "update"]:
            return self._done(0, "updated")
        if verb == ["source", "content"]:
            return self._done(0, json.dumps({"content": "apuntes", "char_count": 7}))
        raise AssertionError(f"unexpected nlm call {argv}")

    @staticmethod
    def _done(code: int, out: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], code, out, "")

    def asked(self, *verb: str) -> list[list[str]]:
        return [c for c in self.calls if c[1 : 1 + len(verb)] == list(verb)]


@dataclass
class FakeLiving:
    found: LivingNotes | None = None
    fails: bool = False
    folder: str = f"20260915 - {TOPIC}"
    reason: str = "drive_failed"

    def living_notes(self, subject: str, folder: str) -> LivingNotes | None:
        assert (subject, folder) == ("FyQ", self.folder)
        if self.fails:
            raise LivingNotesError(self.reason)
        return self.found


@dataclass
class FakePrinter:
    pages_of: dict[str, int] = field(default_factory=lambda: {})  # by the PDF's first words
    fails: set[str] = field(default_factory=lambda: set())
    uncounted: set[str] = field(default_factory=lambda: set())
    printed: list[tuple[str, str, str]] = field(default_factory=lambda: [])

    def print_report(self, notebook: str, artifact: str, out: Path, *, break_before: str = "") -> bool:
        self.printed.append((artifact, out.name, break_before))
        kind = out.name.split(" · ")[0]
        if kind in self.fails:
            return False
        writer = PdfWriter()
        for _ in range(self.pages_of.get(kind, 3)):
            writer.add_blank_page(595, 842)
        with out.open("wb") as handle:
            writer.write(handle)
        return True

    def pages(self, pdf: Path) -> int | None:
        return None if pdf.name.split(" · ")[0] in self.uncounted else PrintPack(PROFILE).pages(pdf)


@dataclass
class World:
    home: Path
    nlm: FakeNlm
    living: FakeLiving
    printer: FakePrinter
    slept: list[float] = field(default_factory=lambda: [])
    mirror_failures: int = 0

    @property
    def base(self) -> Path:
        return sandbox.base_folder(self.home, STUDENT)

    @property
    def topic(self) -> Path:
        return self.base / "2026-2027" / "FyQ" / f"20260915 - {TOPIC}"

    @property
    def data(self) -> Path:
        return self.home / STUDENT / "data"

    def deps(self, cfg: object, store: object) -> ExamDeps:
        return ExamDeps(
            notebook=NlmNotebook(PROFILE, self.nlm),
            living=self.living,
            printer=self.printer,
            mirrors=lambda: self.mirror_failures,
            sleep=self.slept.append,
            now=lambda: dt.datetime(2026, 10, 28, 16, 0, tzinfo=dt.UTC),
        )

    def run(self, *extra: str) -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--student")
        parser.add_argument("--subject")
        parser.add_argument("--exam", type=dt.date.fromisoformat)
        parser.add_argument("--slot")
        parser.add_argument("--topic")
        args = parser.parse_args(["--student", STUDENT, "--subject", "FyQ", *extra])
        return cmd_exam_prep(self.home, args, MemoryStore(), self.deps, lambda: TODAY)


def entry(item: str, category: str, date: str | None, **more: Any) -> dict[str, Any]:
    return {
        "item": item,
        "subject": "FyQ",
        "list": "posted" if category == "announcement" else "pending",
        "category": category,
        "title": "Examen tema 1",
        "date": date,
        "date_only": True,
        "status": None,
        "detected": False,
        "origin": None,
        "corrected": False,
        "classroom_link": "https://classroom.google.com/c/inventada",
        "folder": None,
    } | more


def write_agenda(world: World, entries: list[dict[str, Any]]) -> None:
    path = world.base / "2026-2027" / "agenda.json"
    path.write_text(json.dumps({"version": 1, "school_year": "2026-2027", "entries": entries}))


@pytest.fixture
def world(tmp_path: Path) -> World:
    sandbox.prepare(tmp_path, STUDENT)
    config = tmp_path / STUDENT / "config.toml"
    config.write_text(config.read_text().replace("enabled = false", "enabled = true"))
    w = World(tmp_path, FakeNlm(), FakeLiving(), FakePrinter())
    note = w.base / NOTE_PATH
    note.parent.mkdir(parents=True)
    note.write_text(SCOPE + "\n")
    w.data.mkdir(exist_ok=True)
    (w.data / "state.json").write_text(
        json.dumps({"replicas": {"classroom|synth-30|#announcement": {"role": "announcement", "path": NOTE_PATH}}})
    )
    write_agenda(
        w,
        [
            entry("synth-30", "announcement", "2026-10-20T10:00:00+02:00"),
            entry("synth-30#exam-1", "exam", EXAM_DAY, detected=True, origin="synth-30"),
        ],
    )
    return w


def output(capsys: pytest.CaptureFixture[str]) -> tuple[dict[str, Any], str]:
    out, err = capsys.readouterr()
    return json.loads(out.strip().splitlines()[-1]), err


# --- the prompts ------------------------------------------------------------------------------------


def test_the_three_exam_texts_are_in_prompts_md_and_every_placeholder_is_filled():
    for heading in (prompts.THEORY, prompts.PROBLEMS, prompts.START_NOTE):
        names = set(re.findall(r"\{(\w+)\}", prompts.template(heading)))
        assert names, heading
        assert names <= {"grade", "language", "subject", "exam_day", "scope", "scope_date", "slot", "pages", "theory"}


def test_a_value_is_never_read_again_for_placeholders_and_a_missing_one_raises():
    assert (
        prompts.fill("A {scope} B {slot}", {"scope": "{slot} {x}", "slot": "90 minutos"}) == "A {slot} {x} B 90 minutos"
    )
    with pytest.raises(prompts.PromptError, match="pages"):
        prompts.fill("{pages} {slot}", {"slot": "x"})


def test_dates_and_languages_in_words():
    day = dt.date(2026, 11, 5)
    assert (prompts.exam_day(day), prompts.day_month(day), prompts.short_day(day)) == (
        "jueves 5 de noviembre",
        "5 de noviembre",
        "5 nov",
    )
    assert prompts.language_words("eu") == "euskera"
    with pytest.raises(prompts.PromptError):
        prompts.language_words("xx")


# --- the slot and the topic -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "minutes", "words", "pages"),
    [
        (None, 90, "90 minutos", 4),
        ("17:00-18:30", 90, "17:00–18:30", 4),
        ("17:00-18:40", 100, "17:00–18:40", 5),
        ("16:00-19:00", 180, "16:00–19:00", 8),
    ],
)
def test_the_slot_sets_four_pages_per_90_minutes_rounded_up(given: str | None, minutes: int, words: str, pages: int):
    slot = Slot.parse(given)
    assert (slot.minutes, slot.words, slot.pages) == (minutes, words, pages)


@pytest.mark.parametrize("given", ["18:30-17:00", "17:00", "7:00-8:00", "25:00-26:00"])
def test_a_slot_that_is_not_one_interval_of_a_day_is_refused(given: str):
    with pytest.raises(Refusal):
        Slot.parse(given)


def test_the_sheets_name_the_topic_by_its_number_or_else_by_its_name():
    assert topic_number("20260915 - Tema 01 - Materia inventada") == "T01"
    assert topic_number("20261031 - Tema 02B - Lección inventada") == "T02B"
    assert topic_number("20261001 - Proyecto de laboratorio") == "Proyecto de laboratorio"


# --- a whole run ------------------------------------------------------------------------------------


def test_both_sheets_are_asked_titled_and_printed_into_exam(world: World, capsys: pytest.CaptureFixture[str]):
    code = world.run("--slot", "17:00-18:30")
    result, err = output(capsys)
    assert code == 0
    assert result == {
        "ok": True,
        "exam_date": EXAM_DAY,
        "guide_regenerated": False,
        "slot_minutes": 90,
        "pages_allowed": 4,
        "sheets": [{"kind": "theory", "printed": True, "pages": 3}, {"kind": "problems", "printed": True, "pages": 3}],
        "topic": 0,
    }
    printed = sorted(p.name for p in (world.topic / "exam").iterdir())
    assert printed == ["Problemas tipo · T01 (5 nov).pdf", "Teoría para el examen · T01 (5 nov).pdf"]
    # Both reports in Spanish with their own language option, every placeholder filled.
    asked = world.nlm.asked("report", "create")
    assert len(asked) == 2
    for argv in asked:
        assert argv[argv.index("--format") + 1] == "Create Your Own" and argv[argv.index("--language") + 1] == "es"
        prompt = argv[argv.index("--prompt") + 1]
        assert not PLACEHOLDERS.search(prompt)
        assert SCOPE in prompt or "Problemas tipo" in prompt
    theory = asked[0][asked[0].index("--prompt") + 1]
    assert (
        SCOPE in theory and "(20 de octubre)" in theory and "17:00–18:30" in theory and "Como mucho 4 páginas" in theory
    )
    assert "Examen del jueves 5 de noviembre" in theory
    # Titled from the last to the first, then the start note.
    renames = [c[3:5] for c in world.nlm.asked("studio", "rename")]
    assert renames == [
        ["art-2", f"EXAMEN jueves 2 · Problemas tipo · {TOPIC}"],
        ["art-1", f"EXAMEN jueves 1 · Teoría para el examen · {TOPIC}"],
    ]
    [note] = world.nlm.asked("note", "create")
    assert note[note.index("--title") + 1] == "EXAMEN jueves · Empieza aquí"
    assert f"«EXAMEN jueves 1 · Teoría para el examen · {TOPIC}» (17:00–18:30)" in note[note.index("--content") + 1]
    assert world.nlm.calls.index(note) > world.nlm.calls.index(world.nlm.asked("studio", "rename")[-1])
    # The problems sheet breaks the page before «Soluciones»; the theory sheet does not.
    assert [(a, b) for a, _, b in world.printer.printed] == [("art-1", ""), ("art-2", "Soluciones")]
    # The pack record holds both pieces.
    pack = json.loads((world.data / "study-pack.json").read_text())
    pieces = pack["topics"][f"2026-2027/FyQ/20260915 - {TOPIC}"]["pieces"]
    assert [(p["id"], p["kind"], p["moment"], p["verification"]) for p in pieces] == [
        ("art-1", "exam_theory", "EXAMEN jueves", "pages_only"),
        ("art-2", "exam_problems", "EXAMEN jueves", "pages_only"),
    ]
    # The topic is named; nothing absolute, no id.
    assert f"most recent one: 20260915 - {TOPIC}" in err and "not set up yet" in err
    assert str(world.home) not in err and "nb-1" not in err and "art-" not in err


def test_the_numbers_follow_the_pieces_the_moment_already_holds(world: World, capsys: pytest.CaptureFixture[str]):
    world.nlm.studio = [Art("old-1", "report", "EXAMEN jueves 1 · Teoría para el examen · Tema 00 - Otro")]
    world.nlm.notes = [{"id": "note-1", "title": "EXAMEN jueves · Empieza aquí"}]
    assert world.run() == 0
    renames = [c[4] for c in world.nlm.asked("studio", "rename")]
    assert renames == [
        f"EXAMEN jueves 3 · Problemas tipo · {TOPIC}",
        f"EXAMEN jueves 2 · Teoría para el examen · {TOPIC}",
    ]
    assert world.nlm.asked("note", "update") and not world.nlm.asked("note", "create")
    assert world.nlm.asked("note", "update")[0][4] == "note-1"


def test_the_exam_start_note_is_not_a_second_zero_and_leaves_the_old_one_alone(
    world: World, capsys: pytest.CaptureFixture[str]
):
    # FR-015: piece 0 is the plan; the retired note «0 · Empieza aquí» is neither rewritten nor removed.
    world.nlm.notes = [{"id": "note-0", "title": "0 · Empieza aquí"}]
    assert world.run() == 0
    [note] = world.nlm.asked("note", "create")
    assert note[note.index("--title") + 1] == "EXAMEN jueves · Empieza aquí"
    assert not world.nlm.asked("note", "update") and not world.nlm.asked("note", "delete")


def test_a_second_exam_on_the_topic_sits_beside_the_first(world: World, capsys: pytest.CaptureFixture[str]):
    exam_dir = world.topic / "exam"
    exam_dir.mkdir()
    (exam_dir / "Teoría para el examen · T01 (29 oct).pdf").write_bytes(b"%PDF-1.4\n")
    assert world.run() == 0
    assert len(list(exam_dir.iterdir())) == 3


def test_a_theory_sheet_longer_than_the_slot_is_printed_and_reported(world: World, capsys: pytest.CaptureFixture[str]):
    world.printer.pages_of["Teoría para el examen"] = 6
    assert world.run() == 0
    result, err = output(capsys)
    assert result["sheets"][0] == {"kind": "theory", "printed": True, "pages": 6}
    assert "6 pages; the slot allows 4" in err


def test_the_exam_on_a_date_and_a_named_topic(world: World, capsys: pytest.CaptureFixture[str]):
    other = world.base / "2026-2027" / "FyQ" / "20261101 - Tema 02 - Otra materia"
    other.mkdir()
    world.nlm.notebooks.append({"id": "nb-2", "title": "3º ESO. FyQ. Tema 02 - Otra materia"})
    assert world.run("--exam", EXAM_DAY, "--topic", f"20260915 - {TOPIC}") == 0
    _, err = output(capsys)
    assert "most recent" not in err
    assert (world.topic / "exam" / "Problemas tipo · T01 (5 nov).pdf").is_file()


def test_without_a_topic_the_most_recent_one_is_taken(world: World, capsys: pytest.CaptureFixture[str]):
    (world.base / "2026-2027" / "FyQ" / "20261101 - Tema 02 - Otra materia").mkdir()
    world.nlm.notebooks = []
    assert world.run() == 1
    result, err = output(capsys)
    assert result == {"ok": False, "reason": "no_notebook"} and "Tema 02 - Otra materia" in err


# --- the study guide (step 5) -----------------------------------------------------------------------


def test_a_guide_made_before_the_notes_is_regenerated_before_anything_prints(
    world: World, capsys: pytest.CaptureFixture[str]
):
    world.nlm.studio = [Art("guide-0", "report", "6 · Guía de estudio · Materia", created_at="2026-10-25T09:00:00Z")]
    world.living.found = LivingNotes("src-notes", "md5-new", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    assert world.run() == 0
    result, _ = output(capsys)
    assert result["guide_regenerated"] is True
    [guide] = [c for c in world.nlm.asked("report", "create") if "Study Guide" in c]
    assert guide[guide.index("--language") + 1] == "es"
    assert ["art-1", "6 · Guía de estudio · Materia"] in [c[3:5] for c in world.nlm.asked("studio", "rename")]
    assert [c[4] for c in world.nlm.asked("studio", "delete")] == ["guide-0"]
    # The guide comes before both sheets are asked for.
    assert world.nlm.calls.index(guide) < world.nlm.calls.index(world.nlm.asked("report", "create")[1])
    # The notes source was read once and given its two minutes; the refresh record says so.
    assert len(world.nlm.asked("source", "content")) == 1 and SOURCE_SETTLE_SECONDS in world.slept
    refresh = json.loads((world.data / "notebook-refresh.json").read_text())
    assert refresh["sources"]["src-notes"]["read_md5"] == "md5-new" and refresh["sources"]["src-notes"]["reads"] == 1
    pack = json.loads((world.data / "study-pack.json").read_text())
    assert pack["topics"][f"2026-2027/FyQ/20260915 - {TOPIC}"]["guide"]["id"] == "art-1"


PLAN = "0 · Guía de estudio · Empieza aquí"


def test_regenerating_a_stale_guide_leaves_the_plan_untouched(world: World, capsys: pytest.CaptureFixture[str]):
    # FR-033 regenerates the FR-004 theory guide, never the plan of FR-015, though both say «guía de estudio».
    world.nlm.studio = [
        Art("guide-0", "report", "6 · Guía de estudio · Materia", created_at="2026-10-24T09:00:00Z"),
        Art("plan-0", "report", PLAN, created_at="2026-10-25T09:00:00Z"),
    ]
    world.living.found = LivingNotes("src-notes", "md5", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    assert world.run() == 0
    result, _ = output(capsys)
    assert result["guide_regenerated"] is True
    renames = [c[3:5] for c in world.nlm.asked("studio", "rename")]
    assert ["art-1", "6 · Guía de estudio · Materia"] in renames
    assert not [r for r in renames if r[0] == "plan-0" or r[1] == PLAN]
    assert [c[4] for c in world.nlm.asked("studio", "delete")] == ["guide-0"]
    assert [a.title for a in world.nlm.studio if a.id == "plan-0"] == [PLAN]


def test_a_plan_made_after_the_notes_does_not_pass_for_a_fresh_guide(world: World, capsys: pytest.CaptureFixture[str]):
    # The pack generates the plan last, so it is usually the newest report that says «guía de estudio».
    world.nlm.studio = [
        Art("guide-0", "report", "6 · Guía de estudio · Materia", created_at="2026-10-25T09:00:00Z"),
        Art("plan-0", "report", PLAN, created_at="2026-10-28T09:00:00Z"),
    ]
    world.living.found = LivingNotes("src-notes", "md5", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    assert world.run() == 0
    result, _ = output(capsys)
    assert result["guide_regenerated"] is True
    assert [c[4] for c in world.nlm.asked("studio", "delete")] == ["guide-0"]
    assert [a.title for a in world.nlm.studio if a.id == "plan-0"] == [PLAN]


def test_a_guide_made_after_the_notes_stays_and_a_source_already_read_is_not_read_again(
    world: World, capsys: pytest.CaptureFixture[str]
):
    world.nlm.studio = [Art("guide-0", "report", "Guía de estudio", created_at="2026-10-28T09:00:00Z")]
    world.living.found = LivingNotes("src-notes", "md5-same", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    (world.data / "notebook-refresh.json").write_text(
        json.dumps({"sources": {"src-notes": {"read_md5": "md5-same", "reads": 2}}})
    )
    assert world.run() == 0
    result, _ = output(capsys)
    assert result["guide_regenerated"] is False
    assert not [c for c in world.nlm.asked("report", "create") if "Study Guide" in c]
    assert not world.nlm.asked("source", "content") and not world.nlm.asked("studio", "delete")


def test_a_topic_with_no_guide_gets_one(world: World, capsys: pytest.CaptureFixture[str]):
    world.living.found = LivingNotes("src-notes", "md5", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    assert world.run() == 0
    result, _ = output(capsys)
    assert result["guide_regenerated"] is True and not world.nlm.asked("studio", "delete")


def test_drive_failing_leaves_the_guide_unchecked_and_still_prints_both(
    world: World, capsys: pytest.CaptureFixture[str]
):
    world.living.fails = True
    assert world.run() == 3
    result, err = output(capsys)
    assert result["ok"] is False and result["guide_regenerated"] is False
    assert [s["printed"] for s in result["sheets"]] == [True, True]
    assert "may be stale" in err


def test_a_guide_that_never_completes_is_reported_and_the_sheets_still_print(
    world: World, capsys: pytest.CaptureFixture[str]
):
    world.living.found = LivingNotes("src-notes", "md5", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    world.nlm.never = {"guide"}
    assert world.run() == 3
    result, err = output(capsys)
    assert result["guide_regenerated"] is False and [s["printed"] for s in result["sheets"]] == [True, True]
    assert "may be stale" in err and POLL_SECONDS in world.slept


# --- what fails after step 5 is code 3 and stops nothing ---------------------------------------------


def test_a_report_that_never_completes_leaves_the_other_printed(world: World, capsys: pytest.CaptureFixture[str]):
    world.nlm.never = {"theory"}
    assert world.run() == 3
    result, err = output(capsys)
    assert result["sheets"] == [
        {"kind": "theory", "printed": False, "pages": None},
        {"kind": "problems", "printed": True, "pages": 3},
    ]
    assert "«Teoría para el examen» never completed" in err
    assert not world.nlm.asked("note", "create")  # the start note names the theory sheet, which is not there
    assert [c[3] for c in world.nlm.asked("studio", "rename")] == ["art-2"]


def test_a_sheet_that_does_not_print_is_code_3(world: World, capsys: pytest.CaptureFixture[str]):
    world.printer.fails = {"Problemas tipo"}
    assert world.run() == 3
    result, err = output(capsys)
    assert [s["printed"] for s in result["sheets"]] == [True, False] and "did not print" in err


def test_a_mirror_that_fails_is_counted_and_stops_nothing(world: World, capsys: pytest.CaptureFixture[str]):
    world.mirror_failures = 1
    assert world.run() == 3
    result, err = output(capsys)
    assert [s["printed"] for s in result["sheets"]] == [True, True] and "1 mirror(s)" in err


# --- refusals: nothing asked, nothing printed --------------------------------------------------------


def refused(world: World, capsys: pytest.CaptureFixture[str], code: int, reason: str, *extra: str) -> str:
    assert world.run(*extra) == code
    result, err = output(capsys)
    assert result == {"ok": False, "reason": reason}
    assert not world.nlm.asked("report", "create") and not world.nlm.asked("studio", "rename")
    assert not (world.topic / "exam").exists()
    return err


def test_notebooks_switched_off_refuse_before_nlm_is_called(world: World, capsys: pytest.CaptureFixture[str]):
    config = world.home / STUDENT / "config.toml"
    config.write_text(config.read_text().replace("enabled = true", "enabled = false"))
    err = refused(world, capsys, 1, "notebook_disabled")
    assert "notebook.enabled" in err and world.nlm.calls == []


@pytest.mark.parametrize(
    ("setup", "reason", "hint"),
    [
        ({"missing": True}, "no_nlm", "cannot be run"),
        ({"session": 2}, "nlm_signed_out", "nlm login --profile <profile>"),
        ({"session": 1}, "nlm_failed", "nlm failed"),
        ({"default": "otro"}, "nlm_not_default", "nlm config set auth.default_profile <profile>"),
    ],
)
def test_nlm_not_usable_is_code_5_and_says_which(
    world: World, capsys: pytest.CaptureFixture[str], setup: dict[str, Any], reason: str, hint: str
):
    for key, value in setup.items():
        setattr(world.nlm, key, value)
    err = refused(world, capsys, 5, reason)
    assert hint in err and PROFILE not in err and "otro" not in err


def test_no_agenda_is_no_exam(world: World, capsys: pytest.CaptureFixture[str]):
    (world.base / "2026-2027" / "agenda.json").unlink()
    refused(world, capsys, 1, "no_exam")


def test_no_exam_on_the_date_given_or_none_to_come(world: World, capsys: pytest.CaptureFixture[str]):
    refused(world, capsys, 1, "no_exam", "--exam", "2026-11-06")
    write_agenda(world, [entry("synth-30#exam-1", "exam", "2026-10-01", detected=True, origin="synth-30")])
    refused(world, capsys, 1, "no_exam")


def test_an_exam_of_another_subject_is_not_this_subjects(world: World, capsys: pytest.CaptureFixture[str]):
    write_agenda(
        world, [entry("synth-30#exam-1", "exam", EXAM_DAY, detected=True, origin="synth-30", subject="Ingles")]
    )
    refused(world, capsys, 1, "no_exam")


def test_a_classroom_assignment_exam_has_no_announcement(world: World, capsys: pytest.CaptureFixture[str]):
    write_agenda(world, [entry("assignment-9", "exam", EXAM_DAY)])
    err = refused(world, capsys, 1, "no_announcement")
    assert "announcement" in err


def test_an_exam_detected_in_a_material_has_no_announcement(world: World, capsys: pytest.CaptureFixture[str]):
    write_agenda(world, [entry("material-7#exam-1", "exam", EXAM_DAY, detected=True, origin="material-7")])
    (world.data / "state.json").write_text(
        json.dumps({"replicas": {"classroom|material-7|#description": {"role": "description", "path": NOTE_PATH}}})
    )
    refused(world, capsys, 1, "no_announcement")


def test_an_announcement_whose_note_is_gone_is_no_announcement(world: World, capsys: pytest.CaptureFixture[str]):
    (world.base / NOTE_PATH).unlink()
    refused(world, capsys, 1, "no_announcement")


def test_a_topic_without_its_notebook(world: World, capsys: pytest.CaptureFixture[str]):
    world.nlm.notebooks = [{"id": "nb-9", "title": "3º ESO. FyQ. Tema 09 - Otro"}]
    refused(world, capsys, 1, "no_notebook")


@pytest.mark.parametrize(
    ("extra", "reason"),
    [
        (("--slot", "18:00-17:00"), "invalid_slot"),
        (("--topic", "20990101 - Tema 99 - No existe"), "no_topic"),
    ],
)
def test_usage_errors_refuse(world: World, capsys: pytest.CaptureFixture[str], extra: tuple[str, ...], reason: str):
    refused(world, capsys, 1, reason, *extra)


def test_a_subject_not_configured_and_an_invalid_configuration_refuse(world: World, capsys: pytest.CaptureFixture[str]):
    assert (
        cmd_exam_prep(
            world.home,
            argparse.Namespace(student=STUDENT, subject="Latín", exam=None, slot=None, topic=None),
            MemoryStore(),
            world.deps,
            lambda: TODAY,
        )
        == 1
    )
    assert output(capsys)[0]["reason"] == "no_subject"
    config = world.home / STUDENT / "config.toml"
    config.write_text(config.read_text().replace('nlm_profile = "prueba"\n', ""))
    err = refused(world, capsys, 1, "invalid_config")
    assert "notebook.nlm_profile: missing" in err and world.nlm.calls == []


def test_the_command_is_wired_into_alfabeta(world: World, capsys: pytest.CaptureFixture[str]):
    config = world.home / STUDENT / "config.toml"
    config.write_text(config.read_text().replace("enabled = true", "enabled = false"))
    argv = [
        "--home",
        str(world.home),
        "exam",
        "prep",
        "--student",
        STUDENT,
        "--subject",
        "FyQ",
        "--slot",
        "17:00-18:30",
    ]
    assert cli_main.main(argv) == 1
    assert output(capsys)[0] == {"ok": False, "reason": "notebook_disabled"}


# --- the adapters -----------------------------------------------------------------------------------


def test_every_nlm_command_but_config_carries_the_profile():
    nlm = FakeNlm()
    notebook = NlmNotebook(PROFILE, nlm)
    notebook.check_session()
    assert notebook.default_profile() == PROFILE
    made = notebook.create_report("nb-1", "Study Guide", "es")
    notebook.rename(made, "Guía")
    notebook.delete("nb-1", made)
    assert nlm.calls == [
        ["nlm", "login", "--check", "--profile", PROFILE],
        ["nlm", "config", "get", "auth.default_profile"],
        [
            "nlm",
            "report",
            "create",
            "nb-1",
            "--format",
            "Study Guide",
            "--language",
            "es",
            "-y",
            "--json",
            "--profile",
            PROFILE,
        ],
        ["nlm", "studio", "rename", "art-1", "Guía", "--profile", PROFILE],
        ["nlm", "studio", "delete", "nb-1", "art-1", "--confirm", "--profile", PROFILE],
    ]


def test_mirrors_are_refreshed_without_delete_and_one_not_mounted_is_counted(tmp_path: Path):
    base, mounted, absent = tmp_path / "base", tmp_path / "mirror", tmp_path / "not-mounted"
    base.mkdir()
    mounted.mkdir()
    calls: list[list[str]] = []

    def runner(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert refresh_mirrors(base, [mounted, absent], runner) == 1
    assert calls == [["rsync", "-rlt", "--exclude", ".DS_Store", f"{base}/", f"{mounted}/"]]


# --- what the review asked for ----------------------------------------------------------------------


def test_a_heading_without_its_own_text_block_never_borrows_the_next_sections(tmp_path: Path):
    source = tmp_path / "prompts.md"
    source.write_text("## A\n\nno block here\n\n## B\n\n```text\nB's prompt\n```\n")
    with pytest.raises(prompts.PromptError, match="«A»"):
        prompts.template("A", source)
    assert prompts.template("B", source) == "B's prompt"


@pytest.mark.parametrize("topic", ["..", "."])
def test_a_topic_that_is_not_a_folder_of_the_subject_is_refused(
    world: World, capsys: pytest.CaptureFixture[str], topic: str
):
    refused(world, capsys, 1, "no_topic", "--topic", topic)


def test_a_sheet_named_after_a_long_teachers_topic_fits_a_file_name(world: World, capsys: pytest.CaptureFixture[str]):
    long_topic = ("20261001 - " + "Proyecto de laboratorio sobre la densidad " * 6)[:240].strip()
    (world.base / "2026-2027" / "FyQ" / long_topic).mkdir()
    world.nlm.notebooks.append({"id": "nb-2", "title": f"3º ESO. FyQ. {long_topic[11:]}"})
    world.living = FakeLiving(folder=long_topic)
    assert world.run("--topic", long_topic) == 0
    names = [p.name for p in (world.base / "2026-2027" / "FyQ" / long_topic / "exam").iterdir()]
    assert len(names) == 2 and all(len(n.encode()) <= 255 and n.endswith(" (5 nov).pdf") for n in names)


def test_a_new_guide_whose_old_one_cannot_be_removed_is_still_the_recorded_guide(
    world: World, capsys: pytest.CaptureFixture[str]
):
    world.nlm.studio = [Art("guide-0", "report", "Guía de estudio", created_at="2026-10-25T09:00:00Z")]
    world.living.found = LivingNotes("src-notes", "md5", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    real = world.nlm.__call__

    def refuse_delete(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["studio", "delete"]:
            world.nlm.calls.append(argv)
            return subprocess.CompletedProcess(argv, 1, "", "error")
        return real(argv, stdin)

    deps = world.deps

    def with_refusal(cfg: object, store: object) -> ExamDeps:
        made = deps(cfg, store)
        made.notebook = NlmNotebook(PROFILE, refuse_delete)
        return made

    world.deps = with_refusal  # type: ignore[method-assign]
    assert world.run() == 3
    result, err = output(capsys)
    assert result["guide_regenerated"] is True and "was not retitled or removed" in err
    pack = json.loads((world.data / "study-pack.json").read_text())
    assert pack["topics"][f"2026-2027/FyQ/20260915 - {TOPIC}"]["guide"]["id"] == "art-1"


@pytest.mark.parametrize(("file", "reason"), [("agenda", "unreadable_agenda"), ("state", "unreadable_state")])
def test_an_unreadable_record_of_the_sync_is_a_refusal_not_a_traceback(
    world: World, capsys: pytest.CaptureFixture[str], file: str, reason: str
):
    path = world.base / "2026-2027" / "agenda.json" if file == "agenda" else world.data / "state.json"
    path.write_text("{ half written")
    err = refused(world, capsys, 1, reason)
    assert "run the sync again" in err and str(world.home) not in err


def test_a_usage_error_of_nlm_login_is_not_a_signed_out_session():
    def usage(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2, "", "Usage: nlm login [OPTIONS]\nError: No such option: --check")

    with pytest.raises(NlmError) as err:
        NlmNotebook(PROFILE, usage).check_session()
    assert err.value.reason == "nlm_failed"


def test_the_configurations_warnings_are_shown(world: World, capsys: pytest.CaptureFixture[str]):
    config = world.home / STUDENT / "config.toml"
    config.write_text(config.read_text().replace("mirrors = []", f'mirrors = ["{world.home}/no-montado"]'))
    world.mirror_failures = 1
    assert world.run() == 3
    _, err = output(capsys)
    assert "warning: drive.mirrors[0]: not_mounted" in err


def test_the_printer_runs_print_pack_with_the_profile_and_passes_on_only_its_own_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    calls: list[list[str]] = []
    out = tmp_path / "exam" / "Problemas tipo · T01 (5 nov).pdf"

    def runner(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        out.parent.mkdir()
        out.write_bytes(b"%PDF-1.4\n")
        stderr = "print_pack: no heading «Soluciones»; no page break added\nnlm download report nb-1 failed: id art-2\n"
        return subprocess.CompletedProcess(argv, 0, "", stderr)

    assert PrintPack(PROFILE, runner).print_report("nb-1", "art-2", out, break_before="Soluciones")
    [argv] = calls
    assert argv[1].endswith("skills/study-pack/scripts/print_pack.py")
    assert argv[2:] == ["report", "nb-1", "art-2", str(out), "--profile", PROFILE, "--break-before", "Soluciones"]
    err = capsys.readouterr().err
    assert "no heading «Soluciones»" in err and "art-2" not in err


@dataclass
class FakeDrive:
    files: dict[str, DriveFile]

    def items(self) -> list[DriveFile]:
        return list(self.files.values())

    def contains(self, item_id: str) -> bool:
        return item_id in self.files

    def listed(self, item_id: str) -> DriveFile:
        return self.files[item_id]

    def get(self, file_id: str) -> DriveFile:
        return self.files[file_id]


FOLDER_MIME = "application/vnd.google-apps.folder"
PDF_MIME = "application/pdf"


def drive_with_topic() -> FakeDrive:
    return FakeDrive(
        {
            "subj": DriveFile("subj", "FyQ", FOLDER_MIME),
            "other": DriveFile("other", "Ingles", FOLDER_MIME),
            "top-1": DriveFile("top-1", f"20260915 - {TOPIC}", FOLDER_MIME, ("subj",)),
            "top-2": DriveFile("top-2", f"20260915 - {TOPIC}", FOLDER_MIME, ("other",)),
            "n-1": DriveFile("n-1", "notes", FOLDER_MIME, ("top-1",)),
            "liv-1": DriveFile(
                "liv-1", f"Apuntes · {TOPIC}.pdf", PDF_MIME, ("n-1",), modified="2026-10-27T10:00:00.000Z"
            ),
            "stray": DriveFile(
                "stray", f"Apuntes · {TOPIC}.pdf", PDF_MIME, ("top-1",), modified="2026-10-27T10:00:00.000Z"
            ),
        }
    )


def notes_record(**more: Any) -> dict[str, Any]:
    notes = {"file_id": "liv-1", "source_id": "src-1", "built_md5": "md5-1", "pages": 3, "health": "ok"} | more
    return {"topics": {"top-1": {"name": TOPIC, "living": {"notes": notes}}}}


def test_the_living_notes_file_is_read_from_the_topics_record_in_drive():
    found = living_notes_of(drive_with_topic(), notes_record(), "FyQ", f"20260915 - {TOPIC}")
    assert found == LivingNotes("src-1", "md5-1", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))


def test_a_living_notes_file_not_set_up_is_none():
    for state in ({}, notes_record(source_id=None)):
        assert living_notes_of(drive_with_topic(), state, "FyQ", f"20260915 - {TOPIC}") is None
    assert living_notes_of(drive_with_topic(), notes_record(), "FyQ", "20261101 - Tema 02 - Sin carpeta") is None


@pytest.mark.parametrize(
    "state", [notes_record(health="missing"), notes_record(file_id="gone"), notes_record(file_id="stray")]
)
def test_a_living_notes_file_set_up_but_not_in_place_is_missing(state: dict[str, Any]):
    with pytest.raises(LivingNotesError) as err:
        living_notes_of(drive_with_topic(), state, "FyQ", f"20260915 - {TOPIC}")
    assert err.value.reason == "missing"


def test_a_missing_living_notes_file_is_code_3_and_says_so(world: World, capsys: pytest.CaptureFixture[str]):
    world.living = FakeLiving(fails=True, reason="missing")
    assert world.run() == 3
    result, err = output(capsys)
    assert "not where `notebook setup` put it" in err and "may be stale" in err
    assert [s["printed"] for s in result["sheets"]] == [True, True]


def test_a_printed_sheet_whose_pages_cannot_be_counted_is_code_3(world: World, capsys: pytest.CaptureFixture[str]):
    world.printer.uncounted = {"Teoría para el examen"}
    assert world.run() == 3
    result, err = output(capsys)
    assert result["sheets"][0] == {"kind": "theory", "printed": True, "pages": None}
    assert "pages could not be counted" in err


def test_an_unreadable_pdf_has_no_page_count(tmp_path: Path):
    broken = tmp_path / "x.pdf"
    broken.write_bytes(b"not a pdf")
    assert PrintPack(PROFILE).pages(broken) is None


def test_pieces_that_cannot_be_listed_before_numbering_are_reported(world: World, capsys: pytest.CaptureFixture[str]):
    real = world.nlm.__call__
    polls = [0]

    def flaky(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["studio", "status"]:
            polls[0] += 1
            if polls[0] == 2:  # the listing once both reports completed
                return subprocess.CompletedProcess(argv, 1, "", "error")
        return real(argv, stdin)

    deps = world.deps

    def with_flaky(cfg: object, store: object) -> ExamDeps:
        made = deps(cfg, store)
        made.notebook = NlmNotebook(PROFILE, flaky)
        return made

    world.deps = with_flaky  # type: ignore[method-assign]
    assert world.run() == 3
    assert "numbered from 1" in output(capsys)[1]


def test_the_records_are_readable_by_their_user_alone(world: World, capsys: pytest.CaptureFixture[str]):
    world.living.found = LivingNotes("src-notes", "md5", dt.datetime(2026, 10, 27, 10, 0, tzinfo=dt.UTC))
    assert world.run() == 0
    for name in ("study-pack.json", "notebook-refresh.json"):
        assert (world.data / name).stat().st_mode & 0o777 == 0o600
