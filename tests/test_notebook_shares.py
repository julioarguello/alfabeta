"""`notebook share`: each topic's notebook, editable by the accounts of `notebook.share_with` (spec 001 FR-011b, #233).

Every account, title and id is invented; `nlm` is a fake, never the real command.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from alfabeta import __main__, config
from alfabeta.notes import cli, shares
from alfabeta.notes.sources import NlmMissingError, NlmSources, SourcesError
from tests.conftest import CONFIG

ONE, TWO, OWNER = "familia@example.org", "alumna@colegio.example.com", "madre@example.com"
YEAR = "2026-2027"
TOPIC = "FyQ/20260915 - Tema 01 - Materia inventada"
TITLE = "3º ESO. FyQ. Tema 01 - Materia inventada"
OTHER = "Lengua/20261001 - Tema 02 - Texto inventado"
OTHER_TITLE = "3º ESO. Lengua. Tema 02 - Texto inventado"

TABLES = """
[student]
display_name = "Alumna Inventada"
school_year = "2026-2027"
grade_level = "3º ESO"
languages = ["es", "en"]
rules_both = ""
rules_problems = ""
rules_theory = ""

[storage]
base = "{base}"

[notebook]
enabled = {enabled}
share_with = {share_with}
title_pattern = "{{grade}}. {{subject}}. {{topic}}"
nlm_profile = "prueba"
owner = "madre@example.com"
refresh_minutes = 15
"""


@dataclass
class FakeShares:
    """`NotebookShares` in memory: who each notebook lists, and what an invite does."""

    listed: list[tuple[str, str]] = field(default_factory=lambda: [])
    roles: dict[str, dict[str, str]] = field(default_factory=lambda: {})
    refuses: set[str] = field(default_factory=lambda: set())  # addresses whose invite fails
    ignores: set[str] = field(default_factory=lambda: set())  # addresses an accepted invite does not list
    unreadable: set[str] = field(default_factory=lambda: set())  # notebooks whose sharing cannot be read
    invites: list[tuple[str, str]] = field(default_factory=lambda: [])

    def notebooks(self) -> list[tuple[str, str]]:
        return list(self.listed)

    def collaborators(self, notebook: str) -> dict[str, str]:
        if notebook in self.unreadable:
            raise SourcesError(signed_out=False)
        return dict(self.roles.get(notebook, {}))

    def invite_editor(self, notebook: str, address: str) -> None:
        self.invites.append((notebook, address))
        if address in self.refuses:
            raise SourcesError(signed_out=False)
        if address not in self.ignores:
            self.roles.setdefault(notebook, {})[address] = "editor"


def wanted(*pairs: tuple[str, str]) -> list[shares.TopicNotebook]:
    return [shares.TopicNotebook(topic, title) for topic, title in pairs]


def test_a_missing_account_is_invited_a_viewer_is_raised_and_an_editor_is_left_alone():
    port = FakeShares(
        listed=[("nb-1", TITLE), ("nb-2", OTHER_TITLE), ("nb-9", "Un cuaderno de otra cosa")],
        roles={"nb-1": {OWNER: "owner", ONE: "viewer"}, "nb-2": {OWNER: "owner", ONE: "editor", TWO: "editor"}},
    )
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE), (OTHER, OTHER_TITLE)), [ONE, TWO])
    assert report == {
        "ok": True,
        "dry_run": False,
        "notebooks": 2,
        "invited": 1,
        "raised": 1,
        "already": 2,
        "failed": [],
        "changed": [TOPIC],
    }
    assert port.invites == [("nb-1", ONE), ("nb-1", TWO)]  # never the notebook nobody asked about
    assert port.roles["nb-1"] == {OWNER: "owner", ONE: "editor", TWO: "editor"}  # nobody removed


def test_a_second_run_invites_nobody():
    port = FakeShares(listed=[("nb-1", TITLE)], roles={"nb-1": {ONE: "viewer"}})
    shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE, TWO])
    port.invites.clear()
    again = shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE, TWO])
    assert (again["already"], again["invited"], again["raised"], again["changed"]) == (2, 0, 0, [])
    assert port.invites == []


def test_an_account_that_owns_the_notebook_is_not_invited():
    port = FakeShares(listed=[("nb-1", TITLE)], roles={"nb-1": {ONE: "owner"}})
    assert shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE])["already"] == 1
    assert port.invites == []


def test_a_dry_run_counts_and_invites_nobody():
    port = FakeShares(listed=[("nb-1", TITLE)], roles={"nb-1": {ONE: "viewer"}})
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE, TWO], dry_run=True)
    assert (report["dry_run"], report["invited"], report["raised"], report["changed"]) == (True, 1, 1, [TOPIC])
    assert port.invites == []
    assert shares.summary(report).startswith(
        "simulación, nada cambiado: cuadernos compartidos como editor: 1 revisado(s)"
    )


def test_a_refused_account_is_counted_by_position_and_the_rest_go_on():
    port = FakeShares(listed=[("nb-1", TITLE), ("nb-2", OTHER_TITLE)], refuses={ONE})
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE), (OTHER, OTHER_TITLE)), [ONE, TWO])
    assert report["ok"] is False
    assert report["failed"] == [
        {"topic": TOPIC, "index": 0, "reason": "refused"},
        {"topic": OTHER, "index": 0, "reason": "refused"},
    ]
    assert (report["invited"], report["changed"]) == (2, [TOPIC, OTHER])
    assert ONE not in json.dumps(report) and TWO not in json.dumps(report)
    assert shares.counts(report) == {"notebooks": 2, "invited": 2, "raised": 0, "already": 0, "failed": 2}


def test_an_invite_counts_only_when_the_notebook_lists_the_account_as_editor():
    port = FakeShares(listed=[("nb-1", TITLE)], ignores={TWO})
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE, TWO])
    assert report["invited"] == 1
    assert report["failed"] == [{"topic": TOPIC, "index": 1, "reason": "not_confirmed"}]


def test_a_notebook_whose_sharing_cannot_be_read_fails_every_account_and_the_next_goes_on():
    port = FakeShares(listed=[("nb-1", TITLE), ("nb-2", OTHER_TITLE)], unreadable={"nb-1"})
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE), (OTHER, OTHER_TITLE)), [ONE, TWO])
    assert [f for f in report["failed"] if f["topic"] == TOPIC] == [
        {"topic": TOPIC, "index": 0, "reason": "status_failed"},
        {"topic": TOPIC, "index": 1, "reason": "status_failed"},
    ]
    assert report["changed"] == [OTHER]


def test_an_address_listed_in_another_case_is_the_same_account():
    port = FakeShares(listed=[("nb-1", TITLE)], roles={"nb-1": {"Familia@Example.ORG": "editor"}})
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE])
    assert (report["already"], report["failed"], port.invites) == (1, [], [])


def test_an_invite_nobody_could_read_back_is_not_counted():
    class ReadsOnce(FakeShares):
        def collaborators(self, notebook: str) -> dict[str, str]:
            if self.invites:
                raise SourcesError(signed_out=False)
            return super().collaborators(notebook)

    report = shares.share_notebooks(ReadsOnce(listed=[("nb-1", TITLE)]), wanted((TOPIC, TITLE)), [ONE, TWO])
    assert (report["invited"], report["changed"]) == (0, [])
    assert [f["reason"] for f in report["failed"]] == ["status_failed", "status_failed"]


def test_two_notebooks_with_one_title_are_never_guessed_between():
    port = FakeShares(listed=[("nb-1", TITLE), ("nb-1b", TITLE)])
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE])
    assert report["failed"] == [{"topic": TOPIC, "index": 0, "reason": "ambiguous"}]
    assert port.invites == []


def test_with_no_account_or_no_topic_nlm_is_not_asked():
    class Unreachable(FakeShares):
        def notebooks(self) -> list[tuple[str, str]]:
            raise AssertionError("nlm was asked")

    assert shares.share_notebooks(Unreachable(), wanted((TOPIC, TITLE)), [])["notebooks"] == 0
    assert shares.share_notebooks(Unreachable(), [], [ONE])["ok"] is True


def test_every_reason_reported_is_a_declared_one():
    port = FakeShares(listed=[("nb-1", TITLE)], refuses={ONE}, ignores={TWO})
    report = shares.share_notebooks(port, wanted((TOPIC, TITLE)), [ONE, TWO])
    assert {f["reason"] for f in report["failed"]} <= set(shares.REASONS)


def test_the_topics_are_the_school_years_folders_named_by_the_pattern(tmp_path: Path):
    year = tmp_path / YEAR
    (year / "FyQ" / "20260915 - Tema 01 - Materia inventada").mkdir(parents=True)
    (year / "FyQ" / "No topic").mkdir()
    (year / "FyQ" / "suelto.pdf").write_bytes(b"")
    (year / ".oculta" / "20260915 - Tema 09 - Nada").mkdir(parents=True)
    found = shares.topics(year, "{grade}. {subject}. {topic}", "3º ESO")
    assert found == wanted((TOPIC, TITLE), ("FyQ/No topic", "3º ESO. FyQ. No topic"))
    assert shares.topics(tmp_path / "2031-2032", "{topic}", "3º ESO") == []


# --- the `nlm` adapter -------------------------------------------------------------------------


def nlm_runner(answers: dict[str, tuple[int, str]], calls: list[list[str]]) -> Any:
    def run(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        code, stdout = answers[" ".join(argv[1:3])]
        return subprocess.CompletedProcess(argv, code, stdout, "")

    return run


def test_the_adapter_reads_roles_by_address_and_invites_as_editor_with_the_profile():
    calls: list[list[str]] = []
    status = {"is_public": False, "collaborators": [{"email": ONE, "role": "viewer", "is_pending": False}]}
    answers = {
        "notebook list": (0, json.dumps([{"id": "nb-1", "title": TITLE}])),
        "share status": (0, json.dumps(status)),
        "share invite": (0, "invited"),
    }
    nlm = NlmSources("prueba", nlm_runner(answers, calls))
    assert nlm.notebooks() == [("nb-1", TITLE)]
    assert nlm.collaborators("nb-1") == {ONE: "viewer"}
    nlm.invite_editor("nb-1", ONE)
    assert calls[-1] == ["nlm", "share", "invite", "nb-1", ONE, "--role", "editor", "--profile", "prueba"]
    assert not any("public" in argv for argv in calls)


@pytest.mark.parametrize("answer", ["", "{}", '{"collaborators": null}', "[]"])
def test_the_adapter_fails_on_an_answer_that_is_not_the_shape_it_reads(answer: str):
    nlm = NlmSources("prueba", nlm_runner({"share status": (0, answer), "notebook list": (0, "{}")}, []))
    with pytest.raises(SourcesError):
        nlm.collaborators("nb-1")
    with pytest.raises(SourcesError):
        nlm.notebooks()


def test_the_adapter_reports_a_failed_invite():
    nlm = NlmSources("prueba", nlm_runner({"share invite": (1, "")}, []))
    with pytest.raises(SourcesError):
        nlm.invite_editor("nb-1", ONE)


# --- the command -------------------------------------------------------------------------------


def student(home: Path, base: Path, *, enabled: bool = True, share_with: tuple[str, ...] = (ONE, TWO)) -> None:
    (home / "s9").mkdir(parents=True, exist_ok=True)
    tables = TABLES.format(base=base, enabled=str(enabled).lower(), share_with=json.dumps(list(share_with)))
    (home / "s9" / "config.toml").write_text(CONFIG + tables)


@pytest.fixture
def cfg(tmp_path: Path) -> config.StudentConfig:
    base = tmp_path / "base"
    (base / YEAR / "FyQ" / "20260915 - Tema 01 - Materia inventada").mkdir(parents=True)
    (base / YEAR / "Lengua" / "20261001 - Tema 02 - Texto inventado").mkdir(parents=True)
    student(tmp_path / "home", base)
    return config.load(tmp_path / "home", "s9", __main__.SHARE_TABLES)


def run(
    cfg: config.StudentConfig, port: Any, capsys: pytest.CaptureFixture[str], **kwargs: Any
) -> tuple[int, Any, str]:
    code = cli.cmd_notebook_share(cfg, kwargs.pop("topic", None), shares=lambda profile: port, **kwargs)
    captured = capsys.readouterr()
    return code, json.loads(captured.out.strip().splitlines()[-1]), captured.err


def log_lines(cfg: config.StudentConfig) -> list[dict[str, Any]]:
    path = cfg.data_dir / "log.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []


def test_the_command_shares_every_topics_notebook_and_logs_counts_only(
    cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]
):
    port = FakeShares(listed=[("nb-1", TITLE), ("nb-2", OTHER_TITLE)], roles={"nb-2": {ONE: "viewer"}})
    code, printed, err = run(cfg, port, capsys)
    assert code == 0
    assert (printed["notebooks"], printed["invited"], printed["raised"], printed["failed"]) == (2, 3, 1, [])
    assert "cuadernos compartidos como editor: 2 revisado(s), cuentas invitadas 3, subidas a editor 1" in err
    (line,) = log_lines(cfg)
    assert (line["type"], line["result"]) == ("notebook_shares", "ok")
    assert line["shares"] == {"notebooks": 2, "invited": 3, "raised": 1, "already": 0, "failed": 0}
    for text in (json.dumps(printed), err, json.dumps(line)):
        assert ONE not in text and TWO not in text


def test_a_failed_account_exits_3_and_is_logged(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    code, printed, _ = run(cfg, FakeShares(listed=[("nb-1", TITLE)], refuses={TWO}), capsys)
    assert code == 3
    assert printed["failed"] == [{"topic": TOPIC, "index": 1, "reason": "refused"}]
    assert log_lines(cfg)[0]["result"] == "failed"


def test_one_topic_alone_and_a_dry_run_writes_no_log(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    port = FakeShares(listed=[("nb-1", TITLE), ("nb-2", OTHER_TITLE)])
    code, printed, _ = run(cfg, port, capsys, topic=OTHER, dry_run=True)
    assert (code, printed["notebooks"], printed["invited"], printed["changed"]) == (0, 1, 2, [OTHER])
    assert port.invites == [] and log_lines(cfg) == []


def test_an_unknown_topic_and_a_topic_with_no_notebook_are_refused(
    cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]
):
    port = FakeShares(listed=[("nb-1", TITLE)])
    assert run(cfg, port, capsys, topic="FyQ/No existe")[:2] == (1, {"ok": False, "reason": "no_topic"})
    assert run(cfg, port, capsys, topic=OTHER)[:2] == (1, {"ok": False, "reason": "no_notebook"})


def test_a_signed_out_nlm_exits_5(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    class SignedOut(FakeShares):
        def notebooks(self) -> list[tuple[str, str]]:
            raise SourcesError(signed_out=True)

    assert run(cfg, SignedOut(), capsys)[:2] == (5, {"ok": False, "reason": "nlm_signed_out"})


def test_with_notebooks_disabled_nothing_is_asked_or_shared(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    student(tmp_path / "home", tmp_path, enabled=False)
    off = config.load(tmp_path / "home", "s9", __main__.SHARE_TABLES)
    code, printed, err = run(off, FakeShares(listed=[("nb-1", TITLE)]), capsys)
    assert (code, printed["notebooks"]) == (0, 0)
    assert "enabled is false" in err


@pytest.mark.parametrize(
    ("error", "code", "reason"),
    [(NlmMissingError(), 1, "no_nlm"), (SourcesError(signed_out=False), 3, "nlm_failed")],
)
def test_a_run_that_could_not_start_is_refused_and_logged(
    cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str], error: Exception, code: int, reason: str
):
    class Broken(FakeShares):
        def notebooks(self) -> list[tuple[str, str]]:
            raise error

    assert run(cfg, Broken(), capsys)[:2] == (code, {"ok": False, "reason": reason})
    (line,) = log_lines(cfg)
    assert (line["type"], line["result"], line["reason"]) == ("notebook_shares", "failed", reason)
    assert run(cfg, Broken(), capsys, dry_run=True)[0] == code
    assert len(log_lines(cfg)) == 1  # a dry run writes no line, even when it fails


def test_main_reads_only_the_tables_the_command_needs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    student(tmp_path, tmp_path / "base", share_with=())  # no [google], [drive] or [notes] table is needed
    seen: list[tuple[str | None, bool]] = []

    def fake(share_cfg: config.StudentConfig, topic: str | None, *, dry_run: bool = False) -> int:
        seen.append((topic, dry_run))
        return 0

    monkeypatch.setattr(cli, "cmd_notebook_share", fake)
    argv = ["--home", str(tmp_path), "notebook", "share", "--student", "s9", "--dry-run"]
    assert __main__.main(argv) == 0
    assert seen == [(None, True)]


def test_the_parser_carries_the_command_with_its_student(tmp_path: Path):
    args = __main__.build_parser().parse_args(["notebook", "share", "--student", "s9", "--topic", TOPIC, "--dry-run"])
    assert (args.group, args.verb, args.topic, args.dry_run) == ("notebook", "share", TOPIC, True)
