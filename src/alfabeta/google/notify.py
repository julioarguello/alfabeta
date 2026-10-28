"""The second channel when a link fails: a notification on the family's Mac (spec 004 T015, FR-014, research R9).

It needs no Google link, so it still works when the link is what failed. It names the account by
its alias in the configuration, never by its address. A Mac that cannot show it (no `osascript`, as
on CI) loses only this channel: the run still reports the failure and exits 2 (channel 1).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

TITLE = "alfabeta"
# The text and the title travel as arguments, so nothing the text says can become AppleScript.
_SCRIPT = ("on run argv", "display notification (item 1 of argv) with title (item 2 of argv)", "end run")
# What each status of `accounts.STATUSES` means to the family, and what to do about it.
_REASONS = {
    "revoked": "el permiso se retiró; vuelve a vincularla con «alfabeta google link»",
    "expired": "el permiso caducó; vuelve a vincularla con «alfabeta google link»",
    "missing_scope": "le falta un permiso; vuelve a vincularla con «alfabeta google link»",
    "no_token": "no está vinculada; vincúlala con «alfabeta google link»",
    "no_client": "falta el cliente de alfabeta; guárdalo con «alfabeta google client set»",
    "network": "Google no respondió; se vuelve a intentar en la siguiente ejecución",
}


class Notifier(Protocol):
    """Somewhere the family sees a failure without Google."""

    def notify(self, text: str) -> None:
        """Show `text`."""
        ...


def link_failed(alias: str, status: str) -> str:
    """What the family reads when the account `alias` is not `ok`, in Spanish."""
    return f"alfabeta no puede usar la cuenta «{alias}»: {_REASONS.get(status, 'estado desconocido')}"


def _osascript(argv: list[str]) -> None:
    subprocess.run(argv, check=True, capture_output=True, timeout=10)


@dataclass(frozen=True)
class MacNotifier:
    """A macOS notification through `osascript`."""

    run: Callable[[list[str]], object] = _osascript

    def notify(self, text: str) -> None:
        """Show `text` as a notification titled «alfabeta»; if the Mac cannot, say so on stderr."""
        argv = ["osascript", *(part for line in _SCRIPT for part in ("-e", line)), text, TITLE]
        try:
            self.run(argv)
        except (OSError, subprocess.SubprocessError):
            print("alfabeta: no se pudo mostrar el aviso en el Mac", file=sys.stderr)
