"""Uploads confirmed by size and checksum, updates on the same id (spec 004 FR-012, T024); exports and
Office conversions for the Classroom living file (spec 005 research R6). Invented ids."""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from pathlib import Path

import pytest

from alfabeta.google.drive import MULTIPART_LIMIT, DriveError, OutsideFolderError
from alfabeta.google.transport import Response
from tests.conftest import json_response
from tests.test_google_drive_scope import file, opened


def confirmed(item_id: str, parent: str, content: bytes, name: str = "ficha.pdf") -> Response:
    md5 = hashlib.md5(content).hexdigest()
    return json_response(200, {**file(item_id, parent, name), "size": str(len(content)), "md5Checksum": md5})


def test_a_small_file_is_one_multipart_request(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(confirmed("nuevo-1", "tema-1", b"contenido"))
    made = drive.upload("tema-1", "ficha.pdf", b"contenido", "application/pdf")
    method, url, headers, body = t.calls[-1]
    assert (method, made.id) == ("POST", "nuevo-1")
    assert "/upload/drive/v3/files?uploadType=multipart" in url
    assert headers["Content-Type"].startswith("multipart/related; boundary=")
    assert body is not None and b"contenido" in body and b'"parents": ["tema-1"]' in body
    assert drive.contains("nuevo-1")


def test_above_five_megabytes_the_upload_is_resumable(tmp_path: Path):
    drive, t = opened(tmp_path)
    content = b"x" * (MULTIPART_LIMIT + 1)
    session = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=sesion"
    t.responses += [Response(200, b"", {"Location": session}), confirmed("grande-1", "tema-1", content)]
    drive.upload("tema-1", "grande.pdf", content, "application/pdf")
    (m1, u1, h1, b1), (m2, u2, _, b2) = t.calls[-2:]
    assert (m1, m2) == ("POST", "PUT")
    assert "uploadType=resumable" in u1 and h1["X-Upload-Content-Length"] == str(len(content))
    assert json.loads(b1 or b"{}") == {"name": "grande.pdf", "parents": ["tema-1"]}
    assert (u2, b2) == (session, content)


def test_exactly_five_megabytes_is_still_multipart(tmp_path: Path):
    drive, t = opened(tmp_path)
    content = b"x" * MULTIPART_LIMIT
    t.responses.append(confirmed("justo-1", "tema-1", content))
    drive.upload("tema-1", "justo.pdf", content, "application/pdf")
    assert "uploadType=multipart" in t.calls[-1][1]


GOOD = hashlib.md5(b"contenido").hexdigest()


@pytest.mark.parametrize(
    "reply",
    [
        {"size": "8", "md5Checksum": GOOD},  # same checksum, another size
        {"size": "9", "md5Checksum": "0" * 32},  # same size, another checksum
        {"size": "9"},  # a Google-native document: no checksum, never confirmed
    ],
)
def test_an_upload_counts_only_with_the_same_size_and_checksum(tmp_path: Path, reply: dict[str, str]):
    drive, t = opened(tmp_path)
    t.responses.append(json_response(200, {**file("nuevo-1", "tema-1"), **reply}))
    with pytest.raises(DriveError, match="same size and checksum"):
        drive.upload("tema-1", "ficha.pdf", b"contenido", "application/pdf")
    assert not drive.contains("nuevo-1")


def test_a_changed_file_is_updated_on_the_same_id(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(confirmed("ficha-1", "tema-1", b"nuevo texto"))
    before = len(drive.children("tema-1"))
    made = drive.update("ficha-1", b"nuevo texto", "application/pdf")
    method, url, _, _ = t.calls[-1]
    assert (method, made.id) == ("PATCH", "ficha-1")
    assert "/upload/drive/v3/files/ficha-1?uploadType=multipart" in url
    assert len(drive.children("tema-1")) == before  # never a second file


def test_a_folder_has_no_content_to_update(tmp_path: Path):
    drive, t = opened(tmp_path)
    before = len(t.calls)
    with pytest.raises(DriveError, match="folder"):
        drive.update("tema-1", b"x", "application/pdf")
    assert len(t.calls) == before


def test_a_new_folder_joins_the_tree(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(
        json_response(
            200,
            {"id": "tema-2", "name": "Tema 02", "mimeType": "application/vnd.google-apps.folder", "parents": ["raiz"]},
        )
    )
    made = drive.create_folder("raiz", "Tema 02")
    assert json.loads(t.calls[-1][3] or b"{}")["parents"] == ["raiz"]
    assert made.is_folder and drive.contains("tema-2")
    t.responses.append(confirmed("nuevo-2", "tema-2", b"abc"))
    assert drive.upload("tema-2", "a.pdf", b"abc", "application/pdf").id == "nuevo-2"


def test_an_error_status_is_a_drive_error(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(Response(403, b'{"error": {"code": 403}}'))
    with pytest.raises(DriveError) as err:
        drive.upload("tema-1", "a.pdf", b"abc", "application/pdf")
    assert err.value.status == 403


def test_a_reply_without_a_file_is_a_drive_error(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(Response(200, b""))
    with pytest.raises(DriveError, match="without a file"):
        drive.upload("tema-1", "a.pdf", b"abc", "application/pdf")


def test_properties_go_with_the_upload_and_find_it_again(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(confirmed("tr-1", "tema-1", b"texto"))
    drive.upload("tema-1", "foto.jpg · transcripción.md", b"texto", "text/markdown", {"alfabeta_for": "foto-1"})
    assert b'"properties": {"alfabeta_for": "foto-1"}' in (t.calls[-1][3] or b"")
    reply = {
        **file("tr-1", "tema-1", "foto.jpg · transcripción.md"),
        "properties": {"alfabeta_for": "foto-1", "alfabeta_role": "markdown"},
    }
    t.responses.append(json_response(200, {"files": [reply]}))
    found = drive.made_for("tema-1", {"alfabeta_role": "markdown", "alfabeta_for": "foto-1"})
    assert found is not None and found.id == "tr-1" and found.prop("alfabeta_role") == "markdown"
    q = urllib.parse.parse_qs(urllib.parse.urlparse(t.calls[-1][1]).query)["q"][0]
    assert "properties has { key='alfabeta_for' and value='foto-1' } and properties has { key='alfabeta_role'" in q


def test_sharing_mails_nobody_and_never_a_folder(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(json_response(200, {"id": "permiso"}))
    drive.share_reader("ficha-1", "familia@example.com")
    method, url, _, body = t.calls[-1]
    assert (method, json.loads(body or b"{}")["role"]) == ("POST", "reader")
    assert url.endswith("/files/ficha-1/permissions?sendNotificationEmail=false")
    with pytest.raises(DriveError, match="never a folder"):
        drive.share_reader("tema-1", "familia@example.com")


DOC = "application/vnd.google-apps.document"


def test_a_google_file_is_exported_as_pdf(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses.append(Response(200, b"%PDF exportado"))
    assert drive.export("ficha-1") == b"%PDF exportado"
    method, url, _, _ = t.calls[-1]
    assert (method, url) == (
        "GET",
        "https://www.googleapis.com/drive/v3/files/ficha-1/export?mimeType=application%2Fpdf",
    )
    t.responses.append(Response(403, b'{"error": {"code": 403}}'))  # Drive's export has a size cap
    with pytest.raises(DriveError):
        drive.export("ficha-1")


def test_an_office_file_is_copied_exported_and_its_copy_trashed(tmp_path: Path):
    drive, t = opened(tmp_path)
    props = {"alfabeta_for": "ficha-1", "alfabeta_role": "conversion"}
    left = {**file("vieja", "tema-1"), "mimeType": DOC, "properties": props}  # a stopped run's copy
    t.responses += [
        json_response(200, {"files": [left]}),
        json_response(200, {"id": "vieja"}),
        json_response(200, {**file("copia", "tema-1"), "mimeType": DOC, "properties": props}),
        Response(200, b"%PDF convertido"),
        json_response(200, {"id": "copia"}),
    ]
    assert drive.convert("ficha-1", "tema-1", DOC, props) == b"%PDF convertido"
    methods = [(m, urllib.parse.urlparse(u).path.rsplit("/files", 1)[-1]) for m, u, _, _ in t.calls[-5:]]
    assert methods == [
        ("GET", ""),
        ("PATCH", "/vieja"),
        ("POST", "/ficha-1/copy"),
        ("GET", "/copia/export"),
        ("PATCH", "/copia"),
    ]
    copy = json.loads(t.calls[-3][3] or b"{}")
    assert (copy["mimeType"], copy["parents"], copy["properties"]) == (DOC, ["tema-1"], props)
    assert all(json.loads(t.calls[i][3] or b"{}") == {"trashed": True} for i in (-4, -1))
    assert not drive.contains("copia") and not drive.contains("vieja")


def test_a_failed_export_still_trashes_the_copy(tmp_path: Path):
    drive, t = opened(tmp_path)
    t.responses += [
        json_response(200, {"files": []}),
        json_response(200, {**file("copia", "tema-1"), "mimeType": DOC}),
        Response(500, b"{}"),
        json_response(200, {"id": "copia"}),
    ]
    with pytest.raises(DriveError):
        drive.convert("ficha-1", "tema-1", DOC, {"alfabeta_for": "ficha-1"})
    assert t.calls[-1][0] == "PATCH" and not t.responses


def test_a_conversion_goes_only_into_a_folder_of_the_tree(tmp_path: Path):
    drive, t = opened(tmp_path)
    before = len(t.calls)
    with pytest.raises(OutsideFolderError):
        drive.convert("ficha-1", "fuera-1", DOC, {"alfabeta_for": "ficha-1"})
    with pytest.raises(DriveError, match="not a folder"):
        drive.convert("ficha-1", "ficha-0", DOC, {"alfabeta_for": "ficha-1"})
    assert len(t.calls) == before
