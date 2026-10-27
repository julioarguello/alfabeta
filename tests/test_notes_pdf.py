"""Living files as PDF (spec 005 T012). Images are drawn here; no photo of real notes is used."""

from __future__ import annotations

import datetime as dt
import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pypdf import PdfReader

from alfabeta.notes.model import ClassroomEntry, NotesPage, Part, PartKind, Review, Topic
from alfabeta.notes.pdf import RenderedPart, ReportlabPdfBuilder

TOPIC = Topic("carpeta-1", "Tema 01 - Materia inventada")


def drawn(text: str, size: tuple[int, int] = (600, 800)) -> bytes:
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).text((40, 40), text, fill="black")
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def text_of(pdf: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)


@pytest.fixture(scope="module")
def builder() -> ReportlabPdfBuilder:
    return ReportlabPdfBuilder()


def notes_pages() -> list[tuple[NotesPage, bytes]]:
    first = NotesPage(
        "foto-1", "v1", "## Página 1\n\n- Materia ^(entre líneas) ~~tachado~~ [?]\n  - nivel 2 ↓", order=1
    )
    second = NotesPage("foto-2", "v1", "Palabra clave ZORONGO-DOS [dibujo: un círculo]", order=2, review=Review.WRONG)
    return [(second, drawn("dos")), (first, drawn("uno"))]


def test_the_same_records_give_the_same_bytes(builder: ReportlabPdfBuilder):
    a, pages = builder.notes(TOPIC, notes_pages())
    b, _ = builder.notes(TOPIC, notes_pages())
    assert hashlib.md5(a).hexdigest() == hashlib.md5(b).hexdigest()
    assert pages == 5  # cover + (photo + text) per page


def test_pages_follow_their_order_with_their_heading(builder: ReportlabPdfBuilder):
    text = text_of(builder.notes(TOPIC, notes_pages())[0])
    assert text.index("Página 1") < text.index("ZORONGO-DOS")
    assert "Transcripción automática" in text
    assert "En corrección" in text
    assert "Apuntes · Tema 01 - Materia inventada" in text


def test_a_change_in_one_page_changes_the_bytes(builder: ReportlabPdfBuilder):
    before, _ = builder.notes(TOPIC, notes_pages())
    changed = [(page.marked(Review.CHECKED) if page.order == 2 else page, img) for page, img in notes_pages()]
    after, _ = builder.notes(TOPIC, changed)
    assert before != after
    assert "Revisada por el alumno" in text_of(after)


def one_page_pdf(word: str) -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, invariant=1)
    c.drawString(72, 720, word)
    c.save()
    return buf.getvalue()


def test_each_part_kind_becomes_its_pages(builder: ReportlabPdfBuilder):
    entry = ClassroomEntry(
        "item-1",
        "v1",
        "Ficha de repaso",
        dt.date(2026, 10, 5),
        description="Repasad el tema.",
        addresses=("https://example.org/video",),
        parts=(
            Part("p1", "enunciado - Ficha.pdf", PartKind.PDF),
            Part("p2", "notas.md", PartKind.TEXT),
            Part("p3", "mapa.png", PartKind.IMAGE),
            Part("p4", "simulador.html", PartKind.NAMED),
        ),
    )
    rendered = [
        RenderedPart(entry.parts[0], one_page_pdf("PALABRA-PDF")),
        RenderedPart(entry.parts[1], b"Texto PALABRA-MD"),
        RenderedPart(entry.parts[2], drawn("mapa")),
        RenderedPart(entry.parts[3], b""),
    ]
    earlier = ClassroomEntry(
        "item-0", "v1", "Primera ficha", dt.date(2026, 10, 1), parts=(Part("q", "x", PartKind.NAMED),)
    )
    pdf, pages = builder.classroom(TOPIC, [(entry, rendered), (earlier, [RenderedPart(earlier.parts[0], b"")])])
    text = text_of(pdf)
    assert pages == 6  # cover, earlier's cover, entry's cover, pdf, md, image
    assert text.index("Primera ficha") < text.index("Ficha de repaso")
    for word in ("PALABRA-PDF", "PALABRA-MD", "https://example.org/video", "simulador.html", "Repasad el tema."):
        assert word in text
    again, _ = builder.classroom(TOPIC, [(entry, rendered), (earlier, [RenderedPart(earlier.parts[0], b"")])])
    assert again == pdf


def test_a_missing_font_is_a_clear_error(tmp_path: Path):
    from alfabeta.notes.pdf import _register_font

    with pytest.raises(FileNotFoundError, match="DejaVu"):
        _register_font((tmp_path / "none.ttf",), name="AlfabetaMissing")
