"""The school-year folder shared with the student's other accounts (spec 001 FR-011a, #220).

Every account and id is invented; Drive is a fake transport, never the real API.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from alfabeta import share
from alfabeta.google.transport import Response
from tests.conftest import json_response
from tests.test_google_drive_scope import folder, listing, opened
from tests.test_plan_apply_us1 import Box, cli

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

YEAR = "2026-2027"
ONE, TWO = "familia@example.org", "colegio@example.com"


def test_each_account_can_edit_the_school_year_folder_and_one_refused_stops_nothing(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses += [
        listing(folder("curso-1", "raiz", YEAR)),
        json_response(200, {"permissions": []}),
        Response(403, b'{"error": {"code": 403}}'),  # the first account's domain takes no outside shares
        json_response(200, {"permissions": []}),
        json_response(200, {"id": "p2", "role": "writer"}),
    ]
    result = share.share(drive, YEAR, [ONE, TWO])
    assert result == {"shared": 1, "failed": [{"index": 0, "reason": "refused"}]}
    assert all("/files/curso-1/" in url for _, url, _, _ in t.calls[-4:])  # the school-year folder, not the root
    assert share.counts(result) == {"shared": 1, "failed": 1}
    assert share.summary(result) == "carpeta del curso compartida con 1 cuenta(s), fallidas: 1"


def test_with_no_school_year_folder_nothing_is_shared(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(listing())
    assert share.share(drive, YEAR, [ONE, TWO]) == share.not_reached(2, "no_folder")
    assert not t.responses


def test_with_no_account_drive_is_not_asked(tmp_path: Path):
    drive, t = opened(tmp_path)
    before = len(t.calls)
    assert share.share(drive, YEAR, []) == {"shared": 0, "failed": []}
    assert len(t.calls) == before


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def drive_share(box: Box) -> tuple[int, dict[str, object], str]:
    done = box("drive", "share", "--student", "sample")
    return done.returncode, json.loads(done.stdout), done.stderr


def test_the_command_logs_counts_and_needs_the_lock(box: Box):
    code, result, err = drive_share(box)
    assert (code, result) == (0, {"shared": 0, "failed": []})
    assert "compartida con 0 cuenta(s)" in err
    log = [json.loads(line) for line in (box.home / "sample" / "data" / "log.jsonl").read_text().splitlines()]
    assert {k: log[-1][k] for k in ("type", "run", "result", "shares")} == {
        "type": "shares",
        "run": box.run,
        "result": "ok",
        "shares": {"shared": 0, "failed": 0},
    }
    done = cli(box.home, "drive", "share", "--student", "sample")
    assert json.loads(done.stdout)["reason"] == "lock_not_held"


def test_an_account_drive_cannot_reach_fails_by_index_and_is_never_named(box: Box):
    config = box.home / "sample" / "config.toml"
    config.write_text(config.read_text().replace("share_with = []", f'share_with = ["{ONE}"]', 1))
    code, result, err = drive_share(box)  # the sandbox student has no linked account
    assert (code, result) == (1, {"shared": 0, "failed": [{"index": 0, "reason": "not_reached"}]})
    assert ONE not in json.dumps(result) + err
