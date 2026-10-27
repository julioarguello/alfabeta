"""Drive, confined to the alfabeta folder (spec 004 FR-009a, FR-012, research R6).

The `drive` scope reaches the whole of the student's Drive; this adapter does not. It resolves the
alfabeta folder once, lists everything under it on every run, and refuses any id outside that set
before a request is sent. No other module calls the Drive API.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from alfabeta.config import StudentConfig
    from alfabeta.google.transport import HttpTransport

API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
# Up to this size an upload is one multipart request; above it, a resumable session (research R6).
MULTIPART_LIMIT = 5 * 1024 * 1024
FIELDS = "id,name,mimeType,parents,size,md5Checksum,trashed"
_BOUNDARY = "alfabeta-part"


class DriveError(Exception):
    """Drive answered with an error status, or with something alfabeta cannot use."""

    def __init__(self, reason: str, status: int | None = None) -> None:
        super().__init__(reason)
        self.status = status


class OutsideFolderError(Exception):
    """An id outside the alfabeta folder; raised before any request (FR-009a)."""

    def __init__(self) -> None:
        # The id is not in the message: it is data, and messages reach logs.
        super().__init__("refused: the id is outside the alfabeta folder")


@dataclass(frozen=True)
class DriveFile:
    """The fields alfabeta reads of a file or folder."""

    id: str
    name: str
    mime_type: str
    parents: tuple[str, ...] = ()
    size: int | None = None
    md5: str | None = None

    @property
    def is_folder(self) -> bool:
        """True for a folder."""
        return self.mime_type == FOLDER

    @classmethod
    def of(cls, data: dict[str, Any]) -> DriveFile:
        """From a Drive v3 file resource; `size` arrives as a string."""
        if not data.get("id"):
            raise DriveError("Drive answered without a file")
        size = data.get("size")
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "")),
            mime_type=str(data.get("mimeType", "")),
            parents=tuple(cast("list[str]", data.get("parents", []))),
            size=int(size) if size is not None else None,
            md5=cast("str | None", data.get("md5Checksum")),
        )


def cache_path(config: StudentConfig) -> Path:
    """Where the root's id is cached between runs."""
    return config.data_dir / "google" / "drive.json"


def _quote(value: str) -> str:
    """A string literal for a Drive query."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


class ScopedDrive:
    """The student's Drive, seen only through the alfabeta folder. Build it with `open`."""

    def __init__(self, transport: HttpTransport, token: str, root: DriveFile, tree: dict[str, DriveFile]) -> None:
        self._transport = transport
        self._token = token
        self.root = root
        self._tree = tree

    # --- set-up -----------------------------------------------------------------------------------

    @classmethod
    def open(cls, transport: HttpTransport, token: str, root_path: str, cache: Path) -> ScopedDrive:
        """Resolve the root (cached in `cache`), then list the tree under it for this run's allowlist."""
        probe = cls(transport, token, DriveFile("", "", FOLDER), {})
        root = probe._cached_root(cache, root_path) or probe._resolve(root_path)
        write_atomic(cache, json.dumps({"root_id": root.id, "root_path": root_path}, indent=1) + "\n")
        tree = {root.id: root}
        pending = [root.id]
        while pending:
            folder = pending.pop()
            for child in probe._query(f"{_quote(folder)} in parents and trashed = false"):
                tree[child.id] = child
                if child.is_folder:
                    pending.append(child.id)
        return cls(transport, token, root, tree)

    def _cached_root(self, cache: Path, root_path: str) -> DriveFile | None:
        if not cache.is_file():
            return None
        cached = json.loads(cache.read_text())
        if cached.get("root_path") != root_path:
            return None  # the configured folder changed: resolve it again, never keep the old one
        root_id = str(cached["root_id"])
        data = self._call("GET", f"{API}/{root_id}?{urllib.parse.urlencode({'fields': FIELDS})}")
        if data.get("trashed"):
            raise DriveError("the alfabeta folder is in the trash")
        root = DriveFile.of(data)
        if not root.is_folder:
            raise DriveError("the cached root is not a folder")
        return root

    def _resolve(self, root_path: str) -> DriveFile:
        parts = [p for p in root_path.strip("/").split("/") if p]
        if not parts:
            raise DriveError("[drive] root must name a folder, never the root of My Drive")
        parent = "root"
        found: DriveFile | None = None
        for part in parts:
            q = f"{_quote(parent)} in parents and name = {_quote(part)} and mimeType = {_quote(FOLDER)}"
            matches = list(self._query(f"{q} and trashed = false"))
            if len(matches) != 1:
                raise DriveError(f"expected one folder for [drive] root, found {len(matches)}")
            found = matches[0]
            parent = found.id
        assert found is not None
        return found

    # --- reads ------------------------------------------------------------------------------------

    def contains(self, item_id: str) -> bool:
        """True if the id is the root or anything under it, as listed this run."""
        return item_id in self._tree

    def children(self, folder_id: str) -> list[DriveFile]:
        """What this run's listing found directly inside the folder, sorted by name."""
        self._folder(folder_id)
        return sorted((f for f in self._tree.values() if folder_id in f.parents), key=lambda f: (f.name, f.id))

    def get(self, file_id: str) -> DriveFile:
        """The file as Drive holds it now."""
        self._inside(file_id)
        return DriveFile.of(self._call("GET", f"{API}/{file_id}?{urllib.parse.urlencode({'fields': FIELDS})}"))

    # --- writes -----------------------------------------------------------------------------------

    def create_folder(self, parent_id: str, name: str) -> DriveFile:
        """A new folder inside a folder of the tree."""
        self._folder(parent_id)
        body = json.dumps({"name": name, "mimeType": FOLDER, "parents": [parent_id]}).encode()
        made = DriveFile.of(self._call("POST", f"{API}?fields={FIELDS}", body, "application/json"))
        self._tree[made.id] = made
        return made

    def upload(self, parent_id: str, name: str, content: bytes, mime_type: str) -> DriveFile:
        """A new file; done only when Drive confirms its size and checksum (FR-012)."""
        self._folder(parent_id)
        made = self._send("POST", UPLOAD, {"name": name, "parents": [parent_id]}, content, mime_type)
        self._tree[made.id] = made
        return made

    def update(self, file_id: str, content: bytes, mime_type: str) -> DriveFile:
        """New content on the same Drive id, never a second file; confirmed like an upload."""
        self._inside(file_id)
        if self._tree[file_id].is_folder:
            raise DriveError("a folder has no content to update")
        made = self._send("PATCH", f"{UPLOAD}/{file_id}", {}, content, mime_type)
        self._tree[file_id] = made
        return made

    # --- plumbing ---------------------------------------------------------------------------------

    def _inside(self, item_id: str) -> None:
        if item_id not in self._tree:
            raise OutsideFolderError

    def _folder(self, folder_id: str) -> None:
        self._inside(folder_id)
        if not self._tree[folder_id].is_folder:
            raise DriveError("not a folder")

    def _send(self, method: str, url: str, metadata: dict[str, Any], content: bytes, mime_type: str) -> DriveFile:
        if len(content) <= MULTIPART_LIMIT:
            body = _multipart(metadata, content, mime_type)
            data = self._call(
                method,
                f"{url}?uploadType=multipart&fields={FIELDS}",
                body,
                f"multipart/related; boundary={_BOUNDARY}",
            )
        else:
            data = self._resumable(method, url, metadata, content, mime_type)
        made = DriveFile.of(data)
        if made.size != len(content) or made.md5 != hashlib.md5(content).hexdigest():
            raise DriveError("Drive did not confirm the upload with the same size and checksum")
        return made

    def _resumable(self, method: str, url: str, metadata: dict[str, Any], content: bytes, mime_type: str) -> Any:
        headers = self._headers("application/json; charset=UTF-8")
        headers |= {"X-Upload-Content-Type": mime_type, "X-Upload-Content-Length": str(len(content))}
        resp = self._transport.request(
            method, f"{url}?uploadType=resumable&fields={FIELDS}", headers=headers, body=json.dumps(metadata).encode()
        )
        if resp.status >= 400:
            raise DriveError("Drive refused the upload session", resp.status)
        session = {k.lower(): v for k, v in resp.headers.items()}.get("location")
        if not session:
            raise DriveError("Drive opened no upload session")
        return self._call("PUT", session, content, mime_type)

    def _query(self, q: str) -> Iterator[DriveFile]:
        token: str | None = None
        while True:
            params = {"q": q, "fields": f"nextPageToken,files({FIELDS})", "pageSize": "1000", "spaces": "drive"}
            if token:
                params["pageToken"] = token
            page = self._call("GET", f"{API}?{urllib.parse.urlencode(params)}")
            for item in cast("list[dict[str, Any]]", page.get("files", [])):
                yield DriveFile.of(item)
            token = cast("str | None", page.get("nextPageToken"))
            if not token:
                return

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _call(self, method: str, url: str, body: bytes | None = None, content_type: str | None = None) -> Any:
        resp = self._transport.request(method, url, headers=self._headers(content_type), body=body)
        if resp.status >= 400:
            raise DriveError(f"Drive API returned {resp.status}", resp.status)
        return json.loads(resp.body) if resp.body else {}


def _multipart(metadata: dict[str, Any], content: bytes, mime_type: str) -> bytes:
    head = (
        f"--{_BOUNDARY}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n--{_BOUNDARY}\r\nContent-Type: {mime_type}\r\n\r\n"
    )
    return head.encode() + content + f"\r\n--{_BOUNDARY}--\r\n".encode()
