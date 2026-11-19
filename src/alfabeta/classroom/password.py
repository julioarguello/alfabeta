"""The school account's password for the scripted sign-in (spec 006 FR-031, FR-027).

The password lives in the keychain under its own service, so it can never overwrite one of spec
004's Google links, and is typed by the family at a prompt that does not echo it, from a terminal
only. It is never printed, logged, or taken from an option, an argument or an environment variable.
The `wrong_password` mark is a file in the student's data folder holding only the date it was set:
while it exists the scripted sign-in is not tried again (FR-027), and storing a password clears it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import datetime as dt
    from pathlib import Path

    from alfabeta.google.keychain import TokenStore

SERVICE = "alfabeta.classroom"
MARK = "classroom-wrong-password"


class PasswordError(Exception):
    """The password cannot be asked for or stored; `reason` is the contract's code."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class Prompt(Protocol):
    """Asks for a secret without echoing it (`getpass.getpass`)."""

    def __call__(self, prompt: str) -> str:
        """The answer, without its line end."""
        ...


@dataclass(frozen=True)
class PasswordStore:
    """One student's password in the keychain, and its `wrong_password` mark."""

    store: TokenStore
    data_dir: Path
    student: str

    @property
    def mark_path(self) -> Path:
        """`data/classroom-wrong-password` (spec 006 data-model)."""
        return self.data_dir / MARK

    def get(self) -> str | None:
        """The stored password, or None."""
        return self.store.get(self.student)

    def marked(self) -> bool:
        """Whether the last scripted sign-in stopped with `wrong_password`."""
        return self.mark_path.exists()

    def mark(self, today: dt.date) -> None:
        """Record a `wrong_password` stop; the file holds only its date."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.mark_path.write_text(today.isoformat() + "\n")

    def ask(self, prompt: Prompt, is_tty: bool) -> str:
        """Ask for the password, from a terminal only; holds no lock while the family types."""
        if not is_tty:
            raise PasswordError("invalid_config", "the password is asked only from a terminal")
        try:
            value = prompt("School account password (not shown): ")
        except (EOFError, KeyboardInterrupt):
            raise PasswordError("invalid_config", "no password typed; nothing stored") from None
        if not value:
            raise PasswordError("invalid_config", "no password typed; nothing stored")
        return value

    def store_password(self, value: str) -> None:
        """Store an answer of `ask` and clear the mark."""
        self.store.set(self.student, value)
        self.mark_path.unlink(missing_ok=True)

    def delete(self) -> bool:
        """Remove the password and the mark; whether a password was there."""
        had = self.store.get(self.student) is not None
        self.store.delete(self.student)
        self.mark_path.unlink(missing_ok=True)
        return had
