"""US4 with the student `sample` (spec 001 T055): a book provider's topic in its folder, and the notebook's line.

`book place` leaves `TemaNN_<LANG>.pdf` and `.md` in `<school-year>/<subject>/<YYYYMMDD> - Tema NN -
<title>/<book>/`, reusing the folder that holds `Tema NN - ` whatever its date, with hash and previous
version, and never touches `classroom/`; `log notebook` writes its line with every result.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pytest

from alfabeta import book, sandbox
from alfabeta.book import BookError, BookFiles, BookPlacer
from alfabeta.dates import MADRID
from alfabeta.model import Subject
from alfabeta.sources import BookSource
from tests.test_plan_apply_us1 import FYQ, Box, cli

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

TOPIC = "Tema 01 - Materia inventada"
TOPIC_FOLDER = f"{FYQ}/{sandbox.BOOK_TOPIC}"
BUILT = ("Tema01_EN.md", "Tema01_EN.pdf", "Tema01_ES.md", "Tema01_ES.pdf")


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def built(where: Path, number: str = "01", text: str = "primera") -> Path:
    """What the Science Bits skill's build leaves in `out/`: one PDF and one Markdown per language."""
    where.mkdir(parents=True)
    for lang in ("ES", "EN"):
        (where / f"Tema{number}_{lang}.pdf").write_bytes(f"%PDF-1.4 libro inventado {lang} {text}\n".encode())
        (where / f"Tema{number}_{lang}.md").write_text(f"# Tema inventado {lang} {text}\n")
    (where / ".DS_Store").write_bytes(b"no es del libro")
    return where


def place(box: Box, origin: Path, topic: str = TOPIC, subject: str = "FyQ") -> subprocess.CompletedProcess[str]:
    return box("book", "place", "--student", "sample", "--subject", subject, "--topic", topic, "--origin", str(origin))


def notebook(box: Box, *args: str) -> subprocess.CompletedProcess[str]:
    return box("log", "notebook", "--student", "sample", "--topic", TOPIC, *args)


def tree(root: Path) -> dict[str, tuple[int, str]]:
    """Every folder and file under `root`, with mtime and hash."""
    found: dict[str, tuple[int, str]] = {}
    for path in root.rglob("*"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        found[str(path.relative_to(root))] = (path.stat().st_mtime_ns, digest)
    return found


def written(box: Box) -> dict[str, tuple[int, str]]:
    """`tree` of the whole home but the lease, which every command that checks the lock renews."""
    return {k: v for k, v in tree(box.home).items() if k not in {"sample/data", "sample/data/lock.json"}}


def lines(box: Box) -> list[dict[str, Any]]:
    log = box.data / "log.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []


def replicas(box: Box) -> dict[str, dict[str, Any]]:
    return cast("dict[str, dict[str, Any]]", json.loads((box.data / "state.json").read_text())["replicas"])


def madrid_days() -> set[str]:
    return {dt.datetime.now(MADRID).strftime("%Y%m%d")}


def test_the_topic_goes_in_the_book_subfolder_of_its_folder(box: Box, tmp_path: Path):
    done = place(box, built(tmp_path / "out"))
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["folder"] == f"{TOPIC_FOLDER}/sciencebits" and result["result"] == "placed"
    assert sorted(result["placed"]) == list(BUILT) and result["unchanged"] == []
    assert sorted(p.name for p in (box.base / TOPIC_FOLDER / "sciencebits").iterdir()) == list(BUILT)
    record = replicas(box)["sciencebits|Tema 01|Tema01_ES.pdf"]
    origin = (tmp_path / "out" / "Tema01_ES.pdf").read_bytes()
    assert record == {
        "role": "material",
        "path": f"{TOPIC_FOLDER}/sciencebits/Tema01_ES.pdf",
        "hash": hashlib.sha256(origin).hexdigest(),
        "version": 1,
    }
    assert (tmp_path / "out" / "Tema01_ES.pdf").read_bytes() == origin  # the origin is only read
    assert str(box.home) not in done.stdout + done.stderr  # never an absolute path (FR-031)
    assert "4 colocados" in done.stderr


def test_the_folder_is_found_by_its_number_whatever_its_date_and_title(box: Box, tmp_path: Path):
    teachers = box.base / FYQ / "20261020 - Tema 02 - Título del profesor"
    (teachers / "classroom").mkdir(parents=True)
    (teachers / "classroom" / "20261020 - Ficha inventada.pdf").write_bytes(b"%PDF de la clase")
    classroom = tree(teachers / "classroom")
    done = place(box, built(tmp_path / "out", "02"), "Tema 02 - Otro título del libro")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["folder"] == f"{FYQ}/{teachers.name}/sciencebits"
    assert [p.name for p in (box.base / FYQ).iterdir() if "Tema 02 - " in p.name] == [teachers.name]
    assert tree(teachers / "classroom") == classroom  # classroom/ of the same topic does not change


def test_a_topic_with_no_folder_gets_one_dated_today(box: Box, tmp_path: Path):
    before = madrid_days()
    done = place(box, built(tmp_path / "out", "03"), "Tema 03 - Gases inventados")
    days = before | madrid_days()
    assert done.returncode == 0, done.stderr
    folder = json.loads(done.stdout)["folder"]
    assert folder in {f"{FYQ}/{day} - Tema 03 - Gases inventados/sciencebits" for day in days}
    assert (box.base / folder / "Tema03_ES.md").is_file()


def test_placing_the_same_files_again_writes_nothing(box: Box, tmp_path: Path):
    origin = built(tmp_path / "out")
    assert place(box, origin).returncode == 0
    before = tree(box.base) | {"state": tree(box.data)["state.json"]}
    done = place(box, origin)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert (result["result"], result["placed"], sorted(result["unchanged"])) == ("unchanged", [], list(BUILT))
    assert tree(box.base) | {"state": tree(box.data)["state.json"]} == before
    first, again = lines(box)[-2:]
    assert first["result"] == "placed" and again["result"] == "unchanged"
    assert {k: again[k] for k in ("type", "run", "source", "subject", "topic", "mirrors")} == {
        "type": "book",
        "run": box.run,
        "source": "sciencebits",
        "subject": "FyQ",
        "topic": TOPIC,
        "mirrors": {"up_to_date": 0, "failed": 0},
    }
    assert dt.datetime.fromisoformat(again["at"]).tzinfo is not None


def test_a_changed_file_keeps_its_previous_version(box: Box, tmp_path: Path):
    assert place(box, built(tmp_path / "first")).returncode == 0
    second = built(tmp_path / "second", text="segunda")
    for name in ("Tema01_EN.md", "Tema01_EN.pdf", "Tema01_ES.md"):
        shutil.copyfile(tmp_path / "first" / name, second / name)
    done = place(box, second)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert (result["placed"], len(result["unchanged"])) == (["Tema01_ES.pdf"], 3)
    folder = box.base / TOPIC_FOLDER / "sciencebits"
    [kept] = result["previous"]
    assert kept in {f"Tema01_ES (anterior {d[:4]}-{d[4:6]}-{d[6:]}).pdf" for d in madrid_days()}
    assert (folder / kept).read_bytes() == (tmp_path / "first" / "Tema01_ES.pdf").read_bytes()
    assert (folder / "Tema01_ES.pdf").read_bytes() == (second / "Tema01_ES.pdf").read_bytes()
    found = replicas(box)
    assert found["sciencebits|Tema 01|Tema01_ES.pdf"]["version"] == 2
    assert found["sciencebits|Tema 01|Tema01_ES.md"]["version"] == 1


def test_two_folders_of_one_topic_are_never_guessed_between(box: Box, tmp_path: Path):
    (box.base / FYQ / "20261101 - Tema 01 - Repetido").mkdir()
    before = written(box)
    done = place(box, built(tmp_path / "out"))
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == "ambiguous_topic"
    assert written(box) == before


@pytest.mark.parametrize(
    ("subject", "topic", "origin", "reason"),
    [
        ("Ingles", TOPIC, "out", "no_book"),
        ("Musica", TOPIC, "out", "no_book"),
        ("FyQ", "Tema 1 - Materia inventada", "out", "invalid_topic"),
        ("FyQ", "Unidad 01 - Materia inventada", "out", "invalid_topic"),
        ("FyQ", "Tema 01", "out", "invalid_topic"),
        ("FyQ", TOPIC, "missing", "no_origin"),
        ("FyQ", TOPIC, "empty", "nothing_to_place"),
    ],
)
def test_a_refused_placement_writes_nothing(
    box: Box, tmp_path: Path, subject: str, topic: str, origin: str, reason: str
):
    built(tmp_path / "out")
    (tmp_path / "empty").mkdir()
    (tmp_path / "empty" / ".DS_Store").write_bytes(b"oculto")
    before = written(box)
    done = place(box, tmp_path / origin, topic, subject)
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == reason
    assert written(box) == before
    assert str(tmp_path) not in done.stdout + done.stderr


def test_without_the_lock_nothing_is_placed(box: Box, tmp_path: Path):
    box.release()
    origin = built(tmp_path / "out")
    before = written(box)
    done = place(box, origin)
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == "lock_not_held"
    assert written(box) == before
    box.take()


def test_a_base_folder_that_is_not_there_is_not_created(box: Box, tmp_path: Path):
    box.base.rename(tmp_path / "unmounted")
    done = place(box, built(tmp_path / "out"))
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == "drive_not_mounted"
    assert not box.base.exists()


def test_it_writes_only_in_the_students_base_and_data_folders(box: Box, tmp_path: Path):
    """Never outside the student's root, nor in a Dropbox the Mac may still have."""
    fake_home = tmp_path / "mac-home"
    (fake_home / "Dropbox").mkdir(parents=True)
    origin = built(tmp_path / "out")
    outside = {k: v for k, v in tree(box.home).items() if not k.startswith(("drive/sample", "sample/data"))}
    mac = tree(fake_home)
    argv = ("--subject", "FyQ", "--topic", TOPIC, "--origin", str(origin))
    env = {k: v for k, v in os.environ.items() if k != "ALFABETA_RUN"} | {
        "ALFABETA_RUN": box.run,
        "HOME": str(fake_home),
    }
    done = subprocess.run(
        [sys.executable, "-m", "alfabeta", "--home", str(box.home), "book", "place", "--student", "sample", *argv],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert done.returncode == 0, done.stderr
    assert {k: v for k, v in tree(box.home).items() if not k.startswith(("drive/sample", "sample/data"))} == outside
    assert tree(fake_home) == mac


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync is not installed")
def test_the_mirrors_are_brought_up_to_date(box: Box, tmp_path: Path):
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    config = box.home / "sample" / "config.toml"
    config.write_text(config.read_text().replace("mirrors = []", f"mirrors = [{json.dumps(str(mirror))}]"))
    done = place(box, built(tmp_path / "out"))
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["mirrors"] == {"up_to_date": 1, "failed": 0}
    assert (mirror / TOPIC_FOLDER / "sciencebits" / "Tema01_ES.pdf").is_file()
    assert lines(box)[-1]["mirrors"] == {"up_to_date": 1, "failed": 0}
    assert str(mirror) not in done.stdout + done.stderr


def test_a_mirror_that_is_not_mounted_is_counted_never_named(tmp_path: Path):
    calls: list[list[str]] = []

    def runner(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    mounted = tmp_path / "mounted"
    mounted.mkdir()
    counts = book.refresh(tmp_path / "base", [mounted, tmp_path / "absent"], runner)
    assert counts == {"up_to_date": 1, "failed": 1}
    assert calls == [["rsync", "-rlt", "--exclude", ".DS_Store", f"{tmp_path / 'base'}/", f"{mounted}/"]]


@dataclass
class InventedBook:
    """A third, invented book provider: its own subfolder, its own files, nothing else."""

    folder: Path

    @property
    def name(self) -> str:
        return "librosinventados"

    def files(self) -> list[Path]:
        return sorted(self.folder.iterdir())


def test_an_invented_third_provider_plugs_in_as_another_source(tmp_path: Path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "unidad.pdf").write_bytes(b"%PDF unidad inventada")
    provider: BookFiles = InventedBook(tmp_path / "out")
    subject = Subject("Bio", "Biología inventada", book="librosinventados", book_class="Biología inventada")
    placer = BookPlacer(tmp_path / "base", "2026-2027", subject, {}, dt.date(2026, 11, 2))
    folder = placer.place(provider, "Tema 04 - Células inventadas", "Tema 04")
    assert folder == "2026-2027/Bio/20261102 - Tema 04 - Células inventadas/librosinventados"
    assert (tmp_path / "base" / folder / "unidad.pdf").is_file()
    assert set(placer.replicas) == {"librosinventados|Tema 04|unidad.pdf"}
    sciencebits: BookFiles = BookSource("sciencebits", origin=tmp_path / "out")
    assert [p.name for p in sciencebits.files()] == ["unidad.pdf"]


def test_the_topic_and_the_subject_are_checked():
    assert book.book_topic("Tema 07 -  La  célula") == ("Tema 07 - La célula", "Tema 07")
    assert book.book_topic("Tema 07 - Gases/vapores") == ("Tema 07 - Gases-vapores", "Tema 07")  # as every folder name
    for wrong in ("Tema 7 - x", "tema 07 - x", "Tema 07 -", "Tema 07"):
        with pytest.raises(BookError):
            book.book_topic(wrong)
    with pytest.raises(BookError, match="no book"):
        book.book_subject([Subject("Ingles", "Inglés inventado")], "Ingles")


@pytest.mark.parametrize(
    ("args", "shares"),
    [
        (("--result", "created", "--shares", "2,0,1"), {"invited": 2, "already": 0, "failed": 1}),
        (("--result", "unchanged", "--shares", "0,3,0"), {"invited": 0, "already": 3, "failed": 0}),
        (
            (
                "--result",
                "disabled",
            ),
            {"invited": 0, "already": 0, "failed": 0},
        ),
    ],
)
def test_log_notebook_writes_its_line_with_every_result(box: Box, args: tuple[str, ...], shares: dict[str, int]):
    done = notebook(box, *args)
    assert done.returncode == 0, done.stderr
    line = lines(box)[-1]
    assert {k: line[k] for k in ("type", "run", "topic", "result", "shares")} == {
        "type": "notebook",
        "run": box.run,
        "topic": TOPIC,
        "result": args[1],
        "shares": shares,
    }
    assert "reason" not in line


def test_a_failed_notebook_step_carries_its_reason(box: Box):
    done = notebook(box, "--result", "failed", "--reason", "nlm   failed\nafter the upgrade " + "x" * 300)
    assert done.returncode == 0, done.stderr
    line = lines(box)[-1]
    assert line["result"] == "failed" and line["reason"].startswith("nlm failed after the upgrade x")
    assert len(line["reason"]) == book.REASON_CHARS and "\n" not in line["reason"]


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (("--result", "failed"), "missing_reason"),
        (("--result", "failed", "--reason", "  "), "missing_reason"),
        (("--result", "done"), "invalid_result"),
        (("--result", "created", "--shares", "2,1"), "invalid_shares"),
        (("--result", "created", "--shares", "2,-1,0"), "invalid_shares"),
    ],
)
def test_log_notebook_refuses_and_writes_no_line(box: Box, args: tuple[str, ...], reason: str):
    before = lines(box)
    done = notebook(box, *args)
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == reason
    assert lines(box) == before


def test_log_notebook_needs_a_book_topic_and_the_lock(box: Box):
    done = box("log", "notebook", "--student", "sample", "--topic", "Apuntes", "--result", "created")
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == "invalid_topic"
    box.release()
    done = notebook(box, "--result", "created")
    assert done.returncode == 1 and json.loads(done.stdout)["reason"] == "lock_not_held"
    assert not [line for line in lines(box) if line.get("type") == "notebook"]
    box.take()
