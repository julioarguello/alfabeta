"""Living files as PDF (spec 005 research R6): the same records always give the same bytes.

A notes file is a cover page, then per page the photo and its literal transcription. A Classroom file
is a cover page, then per item a cover page and the pages of each of its parts. The student's work,
its grading and previous versions never reach here: `ClassroomEntry` refuses them.
"""

from __future__ import annotations

import hashlib
import html
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject, NameObject
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from alfabeta.notes.model import PartKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reportlab.platypus import Flowable

    from alfabeta.notes.model import ClassroomEntry, NotesPage, Part, Topic

# A font with the arrows and symbols the notes use (↓, →, └); Helvetica has none of them.
FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
)
FONT = "AlfabetaText"
BLUE = colors.HexColor("#1f3a68")
MARGIN = 2 * cm


@dataclass(frozen=True)
class RenderedPart:
    """A part's content: PDF bytes for `pdf`, `export` and `office`, Markdown for `text`, image bytes for `image`."""

    part: Part
    content: bytes


class PdfBuilder(Protocol):
    """Builds living files; returns their bytes and page count."""

    def notes(self, topic: Topic, pages: Sequence[tuple[NotesPage, bytes]]) -> tuple[bytes, int]:
        """The notes living file: each page with its photo."""
        ...

    def classroom(
        self, topic: Topic, entries: Sequence[tuple[ClassroomEntry, Sequence[RenderedPart]]]
    ) -> tuple[bytes, int]:
        """The Classroom living file: each entry with its parts."""
        ...

    def page(self, page: NotesPage, image: bytes) -> bytes:
        """One page's own PDF."""
        ...


def _register_font(candidates: Sequence[Path], name: str = FONT) -> str:
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    for path in candidates:
        if path.is_file():
            # reportlab ships no type information for registerFont's return value.
            pdfmetrics.registerFont(TTFont(name, str(path)))  # pyright: ignore[reportUnknownMemberType]
            return name
    raise FileNotFoundError("no font with the symbols the notes use; install DejaVu Sans")


_SUPER = re.compile(r"\^\(([^)]*)\)")
_STRIKE = re.compile(r"~~(.+?)~~")
_DOUBT = re.compile(r"\[(\?|ilegible[^\]]*)\]")
_NOTE = re.compile(r"\[(dibujo:[^\]]*|recuadro)\]")
_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _markup(line: str) -> str:
    """One Markdown line as reportlab markup, with the transcription conventions of research R5."""
    text = html.escape(line, quote=False)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _SUPER.sub(r"<super>\1</super>", text)
    text = _STRIKE.sub(r"<strike>\1</strike>", text)
    text = _DOUBT.sub(r'<font color="#b00020">[\1]</font>', text)
    return _NOTE.sub(r'<font color="#666666"><i>[\1]</i></font>', text)


def _paragraph(line: str, style: ParagraphStyle, bullet: str | None = None) -> Paragraph:
    """A paragraph with markup; plain text when the marks overlap, so one bad line never stops a file."""
    try:
        return Paragraph(_markup(line), style, bulletText=bullet)
    except ValueError:
        return Paragraph(html.escape(line, quote=False), style, bulletText=bullet)


class ReportlabPdfBuilder:
    """`PdfBuilder` with reportlab for the pages it draws and pypdf for the pages it copies."""

    def __init__(self, fonts: Sequence[Path] = FONT_CANDIDATES) -> None:
        font = _register_font(fonts)
        self._body = ParagraphStyle("body", fontName=font, fontSize=10.5, leading=14)
        self._title = ParagraphStyle("title", fontName=font, fontSize=20, leading=26, textColor=BLUE)
        self._heading = ParagraphStyle("heading", fontName=font, fontSize=13, leading=18, textColor=BLUE)

    def _drawn(self, story: list[Flowable], title: str) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
            title=title,
            author="alfabeta",
            invariant=1,
        )
        doc.build(story)
        return buf.getvalue()

    def _cover(self, title: str, lines: Sequence[str]) -> list[Flowable]:
        story: list[Flowable] = [Paragraph(html.escape(title), self._title), Spacer(1, 0.6 * cm)]
        story += [_paragraph(line, self._body) for line in lines]
        return [*story, PageBreak()]

    def _text(self, markdown: str) -> list[Flowable]:
        story: list[Flowable] = []
        for raw in markdown.splitlines():
            line = raw.rstrip()
            if not line:
                story.append(Spacer(1, 0.25 * cm))
            elif line.startswith("#"):
                story.append(_paragraph(line.lstrip("#").strip(), self._heading))
            elif line.lstrip().startswith(("- ", "* ")):
                depth = (len(line) - len(line.lstrip())) // 2
                style = ParagraphStyle(
                    f"li{depth}", parent=self._body, leftIndent=12 + 12 * depth, bulletIndent=12 * depth
                )
                story.append(_paragraph(line.lstrip()[2:], style, bullet="•"))
            else:
                story.append(_paragraph(line, self._body))
        return story

    def _photo(self, image: bytes) -> Image:
        width, height = ImageReader(io.BytesIO(image)).getSize()
        box_w, box_h = A4[0] - 2 * MARGIN, A4[1] - 2 * MARGIN - 2 * cm
        scale = min(box_w / width, box_h / height)
        return Image(io.BytesIO(image), width=width * scale, height=height * scale)

    def notes(self, topic: Topic, pages: Sequence[tuple[NotesPage, bytes]]) -> tuple[bytes, int]:
        """The notes living file: cover, then per page its heading, photo and transcription."""
        story = self._cover(
            f"Apuntes · {topic.name}", ["Transcripción literal de los apuntes de clase, página a página."]
        )
        for page, image in sorted(pages, key=lambda p: p[0].order):
            story += self._page(page, image)
        return _finish([self._drawn(story, f"Apuntes · {topic.name}")])

    def _page(self, page: NotesPage, image: bytes) -> list[Flowable]:
        return [
            Paragraph(page.heading, self._heading),
            Spacer(1, 0.3 * cm),
            self._photo(image),
            PageBreak(),
            Paragraph(page.heading, self._heading),
            *self._text(page.markdown),
            PageBreak(),
        ]

    def page(self, page: NotesPage, image: bytes) -> bytes:
        """One page's own PDF, `<photo name> · transcripción.pdf`: the photo and its transcription."""
        return _finish([self._drawn(self._page(page, image), "transcripción")])[0]

    def classroom(
        self, topic: Topic, entries: Sequence[tuple[ClassroomEntry, Sequence[RenderedPart]]]
    ) -> tuple[bytes, int]:
        """The Classroom living file: cover, then per entry its cover and its parts, in posting order."""
        pieces = [
            self._drawn(self._cover(f"Classroom · {topic.name}", ["Material del profesor, por fecha."]), topic.name)
        ]
        for entry, parts in sorted(entries, key=lambda e: (e[0].posted, e[0].title)):
            own: list[bytes] = []
            named: list[str] = []
            for rendered in sorted(parts, key=lambda p: p.part.name):
                drawn = self._part(rendered)
                if drawn is None:
                    named.append(rendered.part.name)
                else:
                    own.append(drawn)
            lines = [entry.posted.isoformat()]
            if entry.description:
                lines += ["", *entry.description.splitlines()]
            lines += [*entry.addresses, *named]
            pieces += [self._drawn(self._cover(entry.title, lines), entry.title), *own]
        return _finish(pieces)

    def _part(self, rendered: RenderedPart) -> bytes | None:
        """A part's pages; None for a part only named on the cover, as is one whose bytes cannot be read.

        One unreadable file of the teacher's never stops the topic's file (as `_paragraph` for a line).
        """
        kind = rendered.part.kind
        if kind == PartKind.TEXT:
            text = rendered.content.decode(errors="replace")
            return self._drawn([*self._text(text), PageBreak()], rendered.part.name)
        if kind not in (PartKind.PDF, PartKind.EXPORT, PartKind.OFFICE, PartKind.IMAGE):
            return None  # NAMED: only on the cover
        # Only reading the teacher's bytes may fail here; drawing stays outside, so a bug still fails the run.
        # pypdf and Pillow raise many types for a damaged file.
        if kind == PartKind.IMAGE:
            try:
                image = self._photo(rendered.content)
            except Exception:
                return None
            return self._drawn([image], rendered.part.name)
        try:
            pages = len(PdfReader(io.BytesIO(rendered.content)).pages)
        except Exception:
            return None
        return rendered.content if pages else None


def _finish(pieces: Sequence[bytes]) -> tuple[bytes, int]:
    """Join the pieces into one PDF whose id is derived from its content, so equal input gives equal bytes."""
    writer = PdfWriter()
    for piece in pieces:
        writer.append(PdfReader(io.BytesIO(piece)))
    digest = hashlib.sha256(b"".join(pieces)).digest()[:16]
    writer._ID = ArrayObject([ByteStringObject(digest), ByteStringObject(digest)])  # type: ignore[attr-defined]
    writer.add_metadata({NameObject("/Producer"): "alfabeta"})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), len(writer.pages)
