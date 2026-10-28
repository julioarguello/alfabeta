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
CHANGES = "https://www.googleapis.com/drive/v3/changes"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
# Up to this size an upload is one multipart request; above it, a resumable session (research R6).
MULTIPART_LIMIT = 5 * 1024 * 1024
FIELDS = "id,name,mimeType,parents,size,md5Checksum,modifiedTime,trashed,properties"
# Spec 005 research R2: only what the feed needs; a name is read only for a change the adapter keeps.
CHANGE_FIELDS = "nextPageToken,newStartPageToken,changes(fileId,removed,file(name,mimeType,parents,md5Checksum,modifiedTime,trashed))"
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
    modified: str | None = None
    trashed: bool = False
    properties: tuple[tuple[str, str], ...] = ()

    def prop(self, key: str) -> str | None:
        """A public property's value."""
        return dict(self.properties).get(key)

    @property
    def version(self) -> str:
        """Drive's checksum, or the modification time of a Google-native file (spec 005 data model)."""
        return self.md5 or self.modified or ""

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
            modified=cast("str | None", data.get("modifiedTime")),
            trashed=bool(data.get("trashed", False)),
            properties=tuple(sorted(cast("dict[str, str]", data.get("properties") or {}).items())),
        )


@dataclass(frozen=True)
class Change:
    """One kept change of the feed: a file inside the folder, or a recorded one that left it."""

    file_id: str
    left: bool  # removed, trashed or moved out of the alfabeta folder
    file: DriveFile | None = None


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
        drive = cls(transport, token, root, {root.id: root})
        drive.relist()
        return drive

    def relist(self) -> None:
        """List the tree under the root again; spec 005's first run does, after taking its cursor."""
        self._tree = {self.root.id: self.root}
        for item in self._walk(self.root.id):
            self._tree[item.id] = item

    def _walk(self, folder_id: str) -> list[DriveFile]:
        """Everything under a folder, listed from Drive."""
        found: list[DriveFile] = []
        pending = [folder_id]
        while pending:
            folder = pending.pop()
            for child in self._query(f"{_quote(folder)} in parents and trashed = false"):
                found.append(child)
                if child.is_folder:
                    pending.append(child.id)
        return found

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

    def listed(self, item_id: str) -> DriveFile:
        """The item as this run's listing holds it, with no request."""
        self._inside(item_id)
        return self._tree[item_id]

    def contains(self, item_id: str) -> bool:
        """True if the id is the root or anything under it, as listed this run."""
        return item_id in self._tree

    def children(self, folder_id: str) -> list[DriveFile]:
        """What this run's listing found directly inside the folder, sorted by name."""
        self._folder(folder_id)
        return sorted((f for f in self._tree.values() if folder_id in f.parents), key=lambda f: (f.name, f.id))

    def items(self) -> list[DriveFile]:
        """Everything this run's listing holds under the root, the root excluded."""
        return [f for f in self._tree.values() if f.id != self.root.id]

    def ancestors(self, item_id: str) -> list[DriveFile]:
        """The folders from just below the root down to the item's parent; empty for the root's children."""
        self._inside(item_id)
        chain: list[DriveFile] = []
        parent = next((p for p in self._tree[item_id].parents if p in self._tree), None)
        while parent is not None and parent != self.root.id:
            chain.append(self._tree[parent])
            parent = next((p for p in self._tree[parent].parents if p in self._tree), None)
        return chain[::-1]

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        """The item with that name in the folder, asked of Drive now, not of this run's listing.

        Another writer may have created it since the run started (spec 005 research R4).
        """
        self._folder(folder_id)
        q = f"{_quote(folder_id)} in parents and name = {_quote(name)} and trashed = false"
        found = sorted(self._query(q), key=lambda f: f.id)
        if len(found) > 1:
            raise DriveError("more than one item with that name in the folder")
        for item in found:
            self._tree[item.id] = item
        return found[0] if found else None

    def content(self, file_id: str) -> bytes:
        """The file's bytes."""
        self._inside(file_id)
        resp = self._transport.request("GET", f"{API}/{file_id}?alt=media", headers=self._headers())
        if resp.status >= 400:
            raise DriveError(f"Drive API returned {resp.status}", resp.status)
        return resp.body

    def export(self, file_id: str, mime_type: str = "application/pdf") -> bytes:
        """A Google-native file's content in another format, converted by Drive (spec 005 research R6)."""
        self._inside(file_id)
        query = urllib.parse.urlencode({"mimeType": mime_type})
        resp = self._transport.request("GET", f"{API}/{file_id}/export?{query}", headers=self._headers())
        if resp.status >= 400:
            raise DriveError(f"Drive API returned {resp.status}", resp.status)
        return resp.body

    def head_revision(self, file_id: str) -> str | None:
        """The file's `headRevisionId`, read now (spec 005 research R4)."""
        self._inside(file_id)
        data = self._call("GET", f"{API}/{file_id}?fields=headRevisionId")
        return cast("str | None", data.get("headRevisionId"))

    # --- the change feed (spec 005 research R2; spec 004 FR-009a as amended) ----------------------

    def start_page_token(self) -> str:
        """The cursor of now: changes after it are the next run's."""
        data = self._call("GET", f"{CHANGES}/startPageToken")
        return str(data["startPageToken"])

    def changes(self, page_token: str, known_ids: frozenset[str]) -> tuple[list[Change], str]:
        """The kept changes since the cursor, and the next cursor.

        The feed has no folder filter, so it is the one read of the whole Drive. A change is kept when
        its parents are in the allowlist, or when its file id is recorded (a recorded file that left
        arrives, so it can be marked gone). Everything else is dropped here, unread beyond its parents,
        and nothing about it is kept or logged. A folder that joins the allowlist is listed whole once.
        """
        kept: list[Change] = []
        token: str | None = page_token
        new_start = page_token
        while token:
            params = {
                "pageToken": token,
                "fields": CHANGE_FIELDS,
                "pageSize": "1000",
                "spaces": "drive",
                "includeRemoved": "true",
                "restrictToMyDrive": "true",
            }
            page = self._call("GET", f"{CHANGES}?{urllib.parse.urlencode(params)}")
            for raw in cast("list[dict[str, Any]]", page.get("changes", [])):
                if raw.get("fileId"):  # a change of a shared drive has none
                    kept += self._keep(raw, known_ids)
            token = cast("str | None", page.get("nextPageToken"))
            new_start = cast("str", page.get("newStartPageToken", new_start))
        return kept, new_start

    def _keep(self, raw: dict[str, Any], known_ids: frozenset[str]) -> list[Change]:
        file_id = str(raw["fileId"])
        data = cast("dict[str, Any] | None", raw.get("file"))
        if file_id == self.root.id:
            # Its parent is outside by definition: a rename, a star or a share of the folder changes
            # nothing here, and losing it fails the run (spec 004 T023).
            if raw.get("removed") or data is None or data.get("trashed"):
                raise DriveError("the alfabeta folder is in the trash")
            return []
        parents = cast("list[str]", (data or {}).get("parents", []))
        inside = data is not None and any(p in self._tree for p in parents)
        if raw.get("removed") or data is None or data.get("trashed") or not inside:
            return self._leave(file_id, known_ids)
        item = DriveFile.of({**data, "id": file_id})
        joined = item.is_folder and file_id not in self._tree
        self._tree[file_id] = item
        kept = [Change(file_id, left=False, file=item)]
        if joined:
            for below in self._walk(file_id):
                self._tree[below.id] = below
                kept.append(Change(below.id, left=False, file=below))
        return kept

    def _leave(self, file_id: str, known_ids: frozenset[str]) -> list[Change]:
        """Drop an item and what is under it from the allowlist; the recorded ones arrive as gone."""
        gone: list[Change] = []
        pending = [file_id]
        while pending:
            item = pending.pop()
            if item in known_ids:
                gone.append(Change(item, left=True))
            pending += [f.id for f in self._tree.values() if item in f.parents]
            self._tree.pop(item, None)
        return gone

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

    def upload(
        self, parent_id: str, name: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        """A new file; done only when Drive confirms its size and checksum (FR-012).

        `properties` are Drive's public ones, which every OAuth client of the account can read (spec 005
        research R4: the Mac and the cloud are two clients).
        """
        self._folder(parent_id)
        metadata: dict[str, Any] = {"name": name, "parents": [parent_id]}
        if properties:
            metadata["properties"] = properties
        made = self._send("POST", UPLOAD, metadata, content, mime_type)
        self._tree[made.id] = made
        return made

    def made_for(self, folder_id: str, properties: dict[str, str]) -> DriveFile | None:
        """The file in the folder carrying all these public properties, asked of Drive now (research R4)."""
        found = self._carrying(folder_id, properties)
        return found[0] if found else None

    def convert(self, file_id: str, folder_id: str, google_type: str, properties: dict[str, str]) -> bytes:
        """An Office file as PDF, through a Google copy that goes to the trash at once (spec 005 research R6).

        Drive copies the file into `folder_id` as `google_type` and exports the copy; the file itself is
        only read. The copy carries `properties`. A copy that a stopped run left in the folder carries
        them too and goes to the trash first, so the folder never holds two (research R4). Nothing else
        is ever trashed.
        """
        self._inside(file_id)
        for left in self._carrying(folder_id, properties):
            self._trash(left.id)
        metadata = {"name": self._tree[file_id].name, "mimeType": google_type, "parents": [folder_id]}
        body = json.dumps({**metadata, "properties": properties}).encode()
        copy = DriveFile.of(self._call("POST", f"{API}/{file_id}/copy?fields={FIELDS}", body, "application/json"))
        self._tree[copy.id] = copy
        try:
            return self.export(copy.id)
        finally:
            self._trash(copy.id)

    def _carrying(self, folder_id: str, properties: dict[str, str]) -> list[DriveFile]:
        self._folder(folder_id)
        has = " and ".join(
            f"properties has {{ key={_quote(k)} and value={_quote(v)} }}" for k, v in sorted(properties.items())
        )
        q = f"{_quote(folder_id)} in parents and trashed = false and {has}"
        found = sorted(self._query(q), key=lambda f: f.id)
        for item in found:
            self._tree[item.id] = item
        return found

    def _trash(self, file_id: str) -> None:
        """Put one of alfabeta's own conversions in Drive's trash; only `convert` calls it."""
        body = json.dumps({"trashed": True}).encode()
        self._call("PATCH", f"{API}/{file_id}?fields=id", body, "application/json")
        self._tree.pop(file_id, None)

    def share_reader(self, file_id: str, address: str) -> None:
        """Let one account read one file, without mailing it (spec 005 FR-011, research R9)."""
        self._inside(file_id)
        if self._tree[file_id].is_folder:
            raise DriveError("only a file is shared, never a folder")
        body = json.dumps({"role": "reader", "type": "user", "emailAddress": address}).encode()
        self._call("POST", f"{API}/{file_id}/permissions?sendNotificationEmail=false", body, "application/json")

    def update(
        self, file_id: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        """New content on the same Drive id, never a second file; confirmed like an upload."""
        self._inside(file_id)
        if self._tree[file_id].is_folder:
            raise DriveError("a folder has no content to update")
        made = self._send(
            "PATCH", f"{UPLOAD}/{file_id}", {"properties": properties} if properties else {}, content, mime_type
        )
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
