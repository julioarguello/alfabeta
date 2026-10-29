"""The Mac lists the cloud's reports and the agenda shows them (spec 005 T036). Every value is invented."""

from __future__ import annotations

import json
from pathlib import Path

from alfabeta.agenda import AgendaBuilder
from alfabeta.classification import Classifier
from alfabeta.notes import watch
from tests.notes_fakes import MemoryDrive


def with_reports(*names: str) -> MemoryDrive:
    drive = MemoryDrive.topic()
    drive.folder("rep", "reports", "raiz")
    for n, name in enumerate(names, start=1):
        drive.put(f"inf-{n}", name, "text/markdown", f"# {name}".encode(), parent="rep")
    return drive


def agenda(reports: list[str]) -> str:
    builder = AgendaBuilder("2026-2027", {}, Classifier(("es",)), [], {}, {}, reports=reports)
    return builder.to_markdown()


def test_each_report_is_recorded_once_and_the_new_ones_are_returned(tmp_path: Path):
    drive = with_reports("Informe 20261028-1605.md")
    first = watch.list_reports(drive, tmp_path)
    assert [r.name for r in first] == ["Informe 20261028-1605.md"]
    assert watch.list_reports(drive, tmp_path) == []
    drive.put("inf-2", "Informe 20261029-0815.md", "text/markdown", b"# otro", parent="rep")
    assert [r.name for r in watch.list_reports(drive, tmp_path)] == ["Informe 20261029-0815.md"]
    record = json.loads((tmp_path / watch.RECORD).read_text())
    assert [r["name"] for r in record["reports"]] == ["Informe 20261028-1605.md", "Informe 20261029-0815.md"]


def test_no_reports_folder_records_nothing(tmp_path: Path):
    assert watch.list_reports(MemoryDrive.topic(), tmp_path) == []
    assert not (tmp_path / watch.RECORD).exists() and watch.report_lines(tmp_path) == []


def test_notices_are_newest_first_in_spanish_with_a_link_and_capped(tmp_path: Path):
    names = [f"Informe 202610{day:02d}-1605.md" for day in range(1, 13)] + ["nota suelta.md"]
    watch.list_reports(with_reports(*names), tmp_path)
    lines = watch.report_lines(tmp_path)
    assert len(lines) == watch.SHOWN
    assert lines[0] == "12 oct, 16:05 · informe de apuntes · [abrir](https://drive.google.com/file/d/inf-12/view)"
    assert lines[-1] == "3 oct, 16:05 · informe de apuntes · [abrir](https://drive.google.com/file/d/inf-3/view)"
    assert watch.report_lines(tmp_path, limit=20)[-1].startswith("nota suelta · informe de apuntes · ")


def test_the_agenda_ends_with_the_reports_and_without_them_has_no_such_section(tmp_path: Path):
    watch.list_reports(with_reports("Informe 20261028-1605.md"), tmp_path)
    md = agenda(watch.report_lines(tmp_path))
    assert md.endswith(
        "## Informes de apuntes\n\n- 28 oct, 16:05 · informe de apuntes · [abrir](https://drive.google.com/file/d/inf-1/view)\n"
    )
    assert md.index("## Publicado") < md.index("## Informes de apuntes")
    assert "Informes de apuntes" not in agenda([])
    with_both = AgendaBuilder("2026-2027", {}, Classifier(("es",)), [], {}, {}, notices=["Aviso x"], reports=["y"])
    assert with_both.to_markdown().index("Aviso x") < with_both.to_markdown().index("## Pendiente")
    assert "y" not in with_both.to_json().split('"entries"')[1]  # the reports never reach agenda.json


def test_an_unreadable_record_counts_as_empty_and_is_written_again(tmp_path: Path):
    (tmp_path / watch.RECORD).write_text("{ esto no es json")
    assert watch.report_lines(tmp_path) == []
    (tmp_path / watch.RECORD).write_text('{"reports": [{"nombre": 1}]}')
    assert watch.report_lines(tmp_path) == []
    assert [r.name for r in watch.list_reports(with_reports("Informe 20261028-1605.md"), tmp_path)] == [
        "Informe 20261028-1605.md"
    ]
    assert len(watch.report_lines(tmp_path)) == 1
