"""Synthetic pages (spec 001 T016). The page is invented; it plants a title, a name and ids."""

from __future__ import annotations

import base64
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from alfabeta import anonymize

if TYPE_CHECKING:
    from pathlib import Path

TITLE = "Ejercicios de la fotosíntesis"
NAME = "Iñigo Inventado"
# Built at run time, like the guardrail's own planted values: a literal would trip the commit hook.
CLASS_ID = base64.b64encode(("9912" + "34567890").encode()).decode()
ITEM_ID = base64.b64encode(("8776" + "65544332").encode()).decode()
LEAK = 'class="' + "persona.real" + "@" + 'colegio-real.es"'
PAGE = f"""<!DOCTYPE html>
<html><head><style>.YVvGBb {{ color: red }}</style><script>var data = ["{NAME}", "{TITLE}"];</script></head>
<body>
<nav class="tab-bar"><a href="/u/5/c/{CLASS_ID}/t/all" aria-label="Trabajo de clase">Trabajo de clase</a></nav>
<div class="item YVvGBb" data-id="{ITEM_ID}">
  <a href="https://classroom.google.com/u/5/c/{CLASS_ID}/a/{ITEM_ID}/details?hl=es">{TITLE}</a>
  <span class="due">Fecha de entrega: 13 oct, 8:00</span>
  <span class="author" title="{NAME}">{NAME} ha publicado</span>
  <img src="https://lh3.googleusercontent.com/a/{ITEM_ID}=s40" alt="{NAME}"/>
  <!-- {NAME} -->
</div>
</body></html>
"""


def test_keeps_structure_and_labels_and_invents_the_rest():
    out = anonymize.anonymize(PAGE)
    for planted in (TITLE, NAME, CLASS_ID, ITEM_ID, "Inventado"):
        assert planted not in out
    assert 'class="item YVvGBb"' in out and '<nav class="tab-bar">' in out and "<style></style>" in out
    assert 'aria-label="Trabajo de clase">Trabajo de clase</a>' in out
    assert "Fecha de entrega: " in out and "13 oct" not in out
    assert "https://classroom.google.com/u/synth-" in out and "/c/synth-" in out and "/a/synth-" in out
    assert out.count("/details") == 1 and "ha publicado</span>" in out
    assert "hl=es" not in out and "lh3.googleusercontent.com" not in out


def test_values_are_stable():
    once, twice = anonymize.anonymize(PAGE), anonymize.anonymize(PAGE)
    assert once == twice
    # The same item id gets the same synthetic id in the attribute and in the URL.
    synthetic = once.split('data-id="', 1)[1].split('"', 1)[0]
    assert synthetic.startswith("synth-") and f"/a/{synthetic}/details" in once


def test_refuses_when_a_text_would_survive(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(anonymize, "LABELS", anonymize.LABELS | {TITLE})

    def keep_everything(self: anonymize._Inventor, original: str) -> str:  # a broken inventor
        return original

    monkeypatch.setattr(anonymize._Inventor, "value", keep_everything)
    with pytest.raises(anonymize.AnonymizeError, match="survive"):
        anonymize.anonymize(PAGE)


def test_refuses_when_the_guardrail_finds_something():
    leaky = PAGE.replace('class="due"', LEAK)
    with pytest.raises(anonymize.AnonymizeError, match="guardrail finds email"):
        anonymize.anonymize(leaky)


def test_command_writes_nothing_on_refusal(tmp_path: Path):
    source, target = tmp_path / "in.html", tmp_path / "out" / "page.html"
    source.write_text(PAGE)

    def cli() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "alfabeta", "--home", str(tmp_path), "anonymize", str(source), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )

    done = cli()
    assert done.returncode == 0, done.stderr
    assert target.is_file() and TITLE not in target.read_text()
    target.unlink()
    source.write_text(PAGE.replace('class="due"', LEAK))
    done = cli()
    assert done.returncode == 1 and not target.exists()


def test_structure_the_extractor_reads_is_kept():
    page = (
        '<li data-stream-item-type="2" data-visibility="1" aria-current="page">'
        f'<a href="/u/0/c/{CLASS_ID}/mc/{ITEM_ID}/details">{TITLE}</a><span>100 puntos</span></li>'
    )
    out = anonymize.anonymize(page)
    assert 'data-stream-item-type="2"' in out and 'data-visibility="1"' in out and 'aria-current="page"' in out
    assert "/mc/synth-" in out and "/details" in out and "100 puntos" in out and TITLE not in out
