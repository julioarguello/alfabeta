"""Uploads confirmed by size and checksum, updates on the same id (spec 004 FR-012, T024). Invented ids."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from alfabeta.google.drive import MULTIPART_LIMIT, DriveError
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
