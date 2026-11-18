"""Constitution 2.12.0 (Technical constraints > Language): every command prints English, each line with the time.

The gates python-cli-output §1 and §6 promise for the whole program arrive with #261; until then
they are skipped tests carrying the reason (the rule's «Proving the gates»), not an absence.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="#261: no stderr string literal in src/ holds Spanish, family-facing writers excluded")
def test_no_command_prints_spanish() -> None:
    raise AssertionError("#261")


@pytest.mark.skip(reason="#261: every module's stderr helper prefixes `alfabeta: <YYYY-MM-DDTHH:MM:SS> `")
def test_every_line_for_people_carries_the_time() -> None:
    raise AssertionError("#261")
