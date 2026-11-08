"""Spec 010: the label and filter plan, and the school account's import file. Invented grades and subjects."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from alfabeta import mail

PATTERN = "{grade}. {subject}. {topic}"
ATOM = "{http://www.w3.org/2005/Atom}"
APPS = "{http://schemas.google.com/apps/2006}"


def test_labels_nest_grade_then_subjects_parents_first():
    p = mail.plan("1º ESO", ("Mates", "Lengua"), PATTERN)
    assert p.labels == ("Alfabeta", "Alfabeta/1º ESO", "Alfabeta/1º ESO/Mates", "Alfabeta/1º ESO/Lengua")
    assert [f.label for f in p.filters] == ["Alfabeta/1º ESO/Mates", "Alfabeta/1º ESO/Lengua"]


def test_query_names_the_senders_and_the_title_prefix():
    (spec,) = mail.plan("1º ESO", ("Mates",), PATTERN).filters
    assert spec.query == mail.SENDER_CLAUSE + ' subject:"1º ESO. Mates."'
    assert spec.query.startswith("from:(GeminiNotebook-noreply@")
    assert " OR NotebookLM-noreply@" in spec.query


@pytest.mark.parametrize(
    ("pattern", "prefix"),
    [
        ("{grade}. {subject}. {topic}", "2º ESO. Bio."),
        ("Cuaderno {grade} - {subject} - {topic} (copia)", "Cuaderno 2º ESO - Bio -"),
    ],
)
def test_prefix_is_the_pattern_cut_before_the_topic(pattern: str, prefix: str):
    assert mail.title_prefix(pattern, "2º ESO", "Bio") == prefix


@pytest.mark.parametrize("pattern", ["{subject}. {topic}", "{grade}. {topic}. {subject}", "{grade} {subject}"])
def test_a_pattern_that_cannot_tell_subjects_apart_is_refused(pattern: str):
    with pytest.raises(mail.MailError) as err:
        mail.plan("2º ESO", ("Bio",), pattern)
    assert err.value.reason == "invalid_title_pattern"


def test_a_subject_whose_words_start_another_excludes_the_longer_one():
    p = mail.plan("1º ESO", ("Mates", "Mates Avanzadas", "Matematicas"), PATTERN)
    short, long_, other = p.filters
    assert short.query.endswith(' subject:"1º ESO. Mates." -subject:"1º ESO. Mates Avanzadas."')
    assert "-subject" not in long_.query
    assert "-subject" not in other.query


def test_the_import_file_holds_one_entry_per_subject(tmp_path: Path):
    p = mail.plan("1º ESO", ("Mates", "Lengua"), PATTERN)
    out = tmp_path / "filtros.xml"
    mail.write_import_file(p, out)
    root = ET.parse(out).getroot()
    assert root.tag == f"{ATOM}feed"
    entries = root.findall(f"{ATOM}entry")
    assert len(entries) == 2
    for entry, spec in zip(entries, p.filters, strict=True):
        assert entry.find(f"{ATOM}category").get("term") == "filter"  # type: ignore[union-attr]
        props = {e.get("name"): e.get("value") for e in entry.findall(f"{APPS}property")}
        assert props == {"hasTheWord": spec.query, "label": spec.label, "shouldArchive": "true"}


def test_the_import_file_holds_no_address_but_the_senders():
    text = mail.import_file(mail.plan("1º ESO", ("Mates",), PATTERN)).decode()
    assert text.count("@") == len(mail.SENDERS)


def test_an_unwritable_out_is_invalid_out(tmp_path: Path):
    with pytest.raises(mail.MailError) as err:
        mail.write_import_file(mail.plan("1º ESO", ("Mates",), PATTERN), tmp_path / "no" / "such" / "f.xml")
    assert err.value.reason == "invalid_out"
