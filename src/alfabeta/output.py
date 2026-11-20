"""The one writer of lines for people: `alfabeta: <YYYY-MM-DDTHH:MM:SS> <message>` on stderr.

Constitution 2.12.0 (Technical constraints > Language) and python-cli-output §6: every line a person
reads is English and carries the local time, so a run can be followed and placed in time from the
terminal or an agent's log. Each command module has its own helper (`_say`, `_fail`) and it calls
`say`; no call adds the time by hand, and no other module prints to stderr
(`tests/test_output_language.py`).
"""

from __future__ import annotations

import datetime as dt
import sys

from alfabeta.dates import MADRID  # principle VIII: local time is always Madrid

PROGRAM = "alfabeta"


def line(message: str, now: dt.datetime | None = None) -> str:
    """`message` as a line for people: the program's name, the Madrid time to the second, the message."""
    when = (now or dt.datetime.now(MADRID)).astimezone(MADRID)
    return f"{PROGRAM}: {when:%Y-%m-%dT%H:%M:%S} {message}"


def say(message: str) -> None:
    """Print `message` on stderr as a line for people."""
    print(line(message), file=sys.stderr)
