"""The browser's downloads folder, from which a run takes only what is its own (spec 001 T040, R12).

`downloads collect` moves to `data/` the captures of the run in progress (its `run` in the name and
in the field) and the attachments the last plan requested: by their expected name or that name with
the browser's « (n)» suffix, created after the plan, never a half-downloaded `.crdownload`. Two
attachments with the same name are in different batches, and only the lowest batch still pending
for a name can claim a file, so every file has one owner. Everything else stays where it is.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from alfabeta import capture

if TYPE_CHECKING:
    from collections.abc import Callable

PARTIAL = ".crdownload"
_SUFFIX = re.compile(r" \(\d+\)$")


def _created(path: Path) -> float:
    stat = path.stat()
    return float(getattr(stat, "st_birthtime", stat.st_mtime))


def matches(file_name: str, expected: str) -> bool:
    """The expected name, or the same with the « (n)» the browser adds before the extension."""
    if file_name == expected:
        return True
    want, got = PurePosixPath(expected), PurePosixPath(file_name)
    return got.suffix == want.suffix and _SUFFIX.sub("", got.stem) == want.stem and got.stem != want.stem


def inbox_path(data_dir: Path, download: dict[str, Any]) -> Path:
    """Where a collected attachment waits for `apply`."""
    return data_dir / "inbox" / f"{download['item']}__{download['attachment']}" / str(download["expected_name"])


@dataclass(frozen=True)
class DownloadsInbox:
    """One student's view of the downloads folder."""

    folder: Path
    data_dir: Path

    def collect_captures(self, run: str) -> list[str]:
        """Move the captures of `run` to `data/captures/`; returns the classes collected."""
        classes: list[str] = []
        target = self.data_dir / "captures"
        for path in sorted(self.folder.glob(f"alfabeta-capture-{run}-*.json")):
            try:
                data = capture.read(path)
            except capture.CaptureError:
                continue
            if data["run"] != run:
                continue
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), target / path.name)
            if data["type"] == "class":
                classes.append(str(data["class"]["id"]))
        return classes

    def collect_attachments(self, plan: dict[str, Any], plan_time: float) -> tuple[list[str], list[str]]:
        """Move the requested attachments; returns (collected, pending) expected names."""
        downloads = sorted(cast("list[dict[str, Any]]", plan.get("downloads", [])), key=lambda d: int(d["batch"]))
        waiting = [d for d in downloads if not inbox_path(self.data_dir, d).exists()]
        candidates = (
            [
                p
                for p in self.folder.iterdir()
                if p.is_file() and not p.name.endswith(PARTIAL) and _created(p) >= plan_time
            ]
            if self.folder.is_dir()
            else []
        )
        claimed: set[Path] = set()
        collected: list[str] = []
        pending: list[str] = []
        lowest: dict[str, int] = {}
        for download in waiting:
            lowest.setdefault(str(download["expected_name"]), int(download["batch"]))
        for download in waiting:
            name = str(download["expected_name"])
            if int(download["batch"]) != lowest[name]:
                pending.append(name)
                continue
            found = next((p for p in candidates if p not in claimed and matches(p.name, name) and _complete(p)), None)
            if found is None:
                pending.append(name)
                continue
            claimed.add(found)
            destination = inbox_path(self.data_dir, download)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(found), destination)
            collected.append(name)
        return collected, pending


def _complete(path: Path) -> bool:
    """A finished download: not empty, and the browser holds no partial file for it (FR-018)."""
    return path.stat().st_size > 0 and not path.with_name(path.name + PARTIAL).exists()


def collect(
    inbox: DownloadsInbox,
    run: str,
    wait_seconds: int = 0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, list[str]]:
    """One `downloads collect`: the run's captures, then the plan's attachments, waiting up to `wait_seconds`."""
    classes = inbox.collect_captures(run)
    plan_path = inbox.data_dir / "plan.json"
    if not plan_path.is_file():
        return {"classes": classes, "collected": [], "pending": []}
    plan = cast("dict[str, Any]", json.loads(plan_path.read_text()))
    plan_time = dt.datetime.fromisoformat(str(plan["created_at"])).timestamp()
    deadline = clock() + wait_seconds
    collected: list[str] = []
    while True:
        got, pending = inbox.collect_attachments(plan, plan_time)
        collected += got
        if not pending or clock() >= deadline:
            return {"classes": classes, "collected": collected, "pending": pending}
        sleep(1.0)
