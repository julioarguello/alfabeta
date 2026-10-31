#!/usr/bin/env python3
"""Print a topic's Gemini Notebook study material to A4 PDF.

  print_pack.py report <notebook-id> <artifact-id> <out.pdf> (--student S | --profile P) [--break-before H]
      one report (study guide, practice sheet, parent guide…); with --break-before, a new page
      before its first heading titled H (an exam's problems sheet before «Soluciones»)
  print_pack.py topic <notebook-id> <out.pdf> (--student S | --profile P)
      the whole Studio in one document: an index first, then every report, quiz (answer key at the
      end), flashcards and mind map, in Studio order; videos appear in the index only; the
      notebook's link under the title (spec 002 FR-047)
  print_pack.py link <notebook-id> <out.pdf> (--student S | --profile P)
      one page with the notebook's title and its link, for the topic's notebook/ folder: a shared
      notebook is not listed for the student until opened once by its link (FR-047)

Needs `nlm`, `pandoc`, Graphviz `dot` (mind maps) and Google Chrome (headless, prints the PDF).
With `--student`, the `nlm` profile is `notebook.nlm_profile` of `<home>/<student>/config.toml`
(`--home`, default ~/.alfabeta), read through alfabeta's configuration loader, so run it from the
clone: `uv run --project <tools.repository> python <this file> …`. `--profile` names one instead.
`nlm download` takes no profile and reads nlm's default one, so the run stops unless that is it;
`link` downloads nothing and does not ask.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from alfabeta import config

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/"
CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm;
  @bottom-center { content: counter(page) " / " counter(pages); font: 9pt sans-serif; color: #666; } }
body { font: 11pt/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; max-width: none; }
h1 { font-size: 20pt; margin: 0 0 6mm; }
h2 { font-size: 15pt; margin-top: 8mm; border-bottom: 1px solid #ccc; padding-bottom: 1mm; }
h3 { font-size: 12.5pt; margin-top: 5mm; } h2, h3 { break-after: avoid; }
table { border-collapse: collapse; table-layout: auto; width: 100%; font-size: 10pt; margin: 3mm 0; }
th, td { border: 1px solid #bbb; padding: 1.5mm 2mm; vertical-align: top; }
th { background: #f0f0f0; } tr, li, pre { break-inside: avoid; }
col { width: auto !important; }
pre, code { font-family: Menlo, "DejaVu Sans Mono", monospace; font-size: 9pt; }
pre { background: #f7f7f7; padding: 3mm; white-space: pre; overflow: hidden; }
hr { border: 0; border-top: 1px solid #ddd; margin: 5mm 0; }
.newpage { break-before: page; }
.mindmap svg { display: block; margin: 0 auto; height: 225mm; width: auto; max-width: 100%; }
.question { break-inside: avoid; margin-bottom: 4mm; }
"""
# Measured 2026-10-28 with nlm 0.15.8: every command used here takes --profile but these two, which
# read nlm's default profile (`auth.default_profile`); nlm reads no profile from the environment.
UNPROFILED = frozenset({"download", "config"})
LIST_ITEM = re.compile(r"\s*([*+-]|\d+[.)])\s")


def profile_of(home: str, student: str) -> str:
    """The student's `notebook.nlm_profile`; a missing or invalid configuration stops the run."""
    try:
        return config.load(Path(home).expanduser(), student, ("notebook",)).nlm_profile
    except config.ConfigError as err:
        sys.exit(f"print_pack: {err}")


def nlm(profile: str, *args: str) -> str:
    extra = () if args[0] in UNPROFILED else ("--profile", profile)
    done = subprocess.run(["nlm", *args, *extra], capture_output=True, text=True)
    if done.returncode:
        sys.exit(f"nlm {args[0]} {args[1]} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def require_default(profile: str) -> None:
    """Stop unless `profile` is nlm's default one, the profile `nlm download` reads."""
    default = nlm(profile, "config", "get", "auth.default_profile").strip()
    if default != profile:
        sys.exit(
            "print_pack: nlm download reads nlm's default profile, which is not the student's"
            " notebook.nlm_profile; make it so with `nlm config set auth.default_profile <profile>`"
        )


def download(profile: str, kind: str, nb: str, art: str, work: Path, *extra: str) -> Path:
    out = work / f"{art}.{'md' if kind == 'report' else 'json'}"
    nlm(profile, "download", kind, nb, "--id", art, "-o", str(out), *extra)
    return out


def fix_lists(md: str) -> str:
    """Gemini Notebook omits the blank line pandoc needs before a list; add it."""
    out: list[str] = []
    for line in md.split("\n"):
        if LIST_ITEM.match(line) and out and out[-1].strip() and not LIST_ITEM.match(out[-1]):
            out.append("")
        out.append(line)
    return "\n".join(out)


def break_before(md: str, heading: str) -> str:
    """A page break before the first heading whose text is `heading`.

    Whatever its level, numbering (`5.`, `5)`), bold, quotes or a closing colon: `## **5. Soluciones:**`.
    """
    lines = md.split("\n")
    for n, line in enumerate(lines):
        found = re.match(r"#{1,6}\s+(.*)$", line)
        text = found.group(1).strip(' *_«»"') if found else ""
        if found and re.sub(r"^\d+[.)]\s*", "", text).rstrip(":").strip(' *_«»"') == heading:
            return "\n".join([*lines[:n], '<div class="newpage"></div>', "", *lines[n:]])
    print(f"print_pack: no heading «{heading}»; no page break added", file=sys.stderr)
    return md


def demote(md: str) -> str:
    """Push a report's headings one level down so its own title sits under the piece's heading."""
    return re.sub(r"^(#{1,5}) ", r"#\1 ", md, flags=re.M)


def cell(text: str) -> str:
    """Make text safe inside a pipe-table cell."""
    return text.replace("|", "\\|").replace("\n", "<br>")


def card_text(side: dict) -> str:
    return " ".join(b.get("content", "") for b in side.get("flashcardContentBlock", []))


def quiz_md(data: dict) -> str:
    lines, key = [], []
    for n, q in enumerate(data["questions"], 1):
        lines += ["::: question", f"**{n}.** {q['question']}", ""]
        for letter, opt in zip("abcdefgh", q["answerOptions"]):
            lines.append(f"- {letter}) {opt['text']}")
            if opt.get("isCorrect"):
                key.append(f"| {n} | {letter} | {cell(opt.get('rationale', ''))} |")
        lines += [":::", ""]
    return "\n".join(lines + ["### Erantzunak", "", "| # | | |", "|---|---|---|", *key, ""])


def flashcards_md(data: dict) -> str:
    rows = [f"| {cell(card_text(c['front']))} | {cell(card_text(c['back']))} |" for c in data["cards"]]
    return "\n".join(["| | |", "|---|---|", *rows, ""])


def wrap(label: str, width: int = 30) -> str:
    """Break a mind-map label into lines so the graph stays narrow enough to read on paper."""
    return "\\n".join(textwrap.wrap(label.replace('"', "'"), width)) or " "


def mindmap_html(data: dict, work: Path) -> str:
    edges, labels = [], {}

    def walk(node: dict, parent: str | None) -> None:
        nid = f"n{len(labels)}"
        labels[nid] = node["name"]
        if parent:
            edges.append(f"{parent} -> {nid};")
        for child in node.get("children", []):
            walk(child, nid)

    walk(data, None)
    nodes = [f'{k} [label="{wrap(v)}"];' for k, v in labels.items()]
    dot = (
        "digraph M { rankdir=LR; nodesep=0.12; ranksep=0.35;"
        'node [shape=box style="rounded,filled" fillcolor="#f4f6fb" color="#9aa7c7" '
        'fontname="Helvetica" fontsize=10]; edge [color="#9aa7c7" arrowhead=none];'
        + "".join(nodes)
        + "".join(edges)
        + "}"
    )
    svg = subprocess.run(["dot", "-Tsvg"], input=dot, capture_output=True, text=True, check=True).stdout
    return '<div class="mindmap">' + svg[svg.index("<svg") :] + "</div>"


def render(md: str, out: Path, work: Path) -> None:
    src, page, css = work / "doc.md", work / "doc.html", work / "print.css"
    src.write_text(md)
    css.write_text(CSS)
    subprocess.run(
        [
            "pandoc",
            str(src),
            "-f",
            "markdown-fancy_lists+tex_math_dollars",
            "-t",
            "html5",
            "-s",
            f"--math-method=katex:{KATEX}",
            "--metadata",
            "title= ",
            "-c",
            str(css),
            "-o",
            str(page),
        ],
        check=True,
    )
    out.parent.mkdir(parents=True, exist_ok=True)  # the topic's notebook/ or exam/ may not exist yet
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=15000",
            "--run-all-compositor-stages-before-draw",
            f"--print-to-pdf={out}",
            page.as_uri(),
        ],
        check=True,
        capture_output=True,
    )


def notebook_of(profile: str, nb: str) -> tuple[str, str]:
    """The notebook's title and its link, as nlm returns them; alfabeta never builds the link."""
    got = json.loads(nlm(profile, "notebook", "get", nb, "--json"))
    if not got.get("url"):
        sys.exit("print_pack: nlm notebook get returned no url for the notebook")
    return got.get("title", ""), got["url"]


def link(args: argparse.Namespace, work: Path) -> None:
    """Written only when absent or carrying another link, so an up-to-date mirror gets no write."""
    out = Path(args.out).expanduser()
    if not out.is_absolute():  # a path relative to storage.base would land beside the clone, outside Drive
        sys.exit("print_pack: link needs an absolute path to the topic's notebook/ folder")
    title, url = notebook_of(args.profile, args.notebook)
    # Chrome writes each link as a `/URI (<url>)` annotation (measured 2026-10-31).
    if out.is_file() and f"/URI ({url})".encode() in out.read_bytes():
        print(f"print_pack: {out.name} already carries the notebook's link; not written", file=sys.stderr)
        return
    md = f"""# {title}

La primera vez, abre tu cuaderno con este enlace. Después aparecerá en tu lista de cuadernos.

**[Abrir el cuaderno]({url})**

{url}
"""
    render(md, out, work)


def report(args: argparse.Namespace, work: Path) -> None:
    md = fix_lists(download(args.profile, "report", args.notebook, args.artifact, work).read_text())
    if args.break_before:
        md = break_before(md, args.break_before)
    render(md, Path(args.out).expanduser(), work)


def topic(args: argparse.Namespace, work: Path) -> None:
    arts = json.loads(nlm(args.profile, "studio", "status", args.notebook, "--full", "--json"))
    arts = [
        a for a in (arts.get("artifacts", arts) if isinstance(arts, dict) else arts) if a.get("status") == "completed"
    ]
    # Studio order is last-modified; a leading "N ·" in the title is the intended order.
    arts.sort(key=lambda a: int(m.group(1)) if (m := re.match(r"(\d+)\s*·", a.get("title") or "")) else 99)
    title, url = notebook_of(args.profile, args.notebook)
    index = ["| | Pieza | Dónde |", "|---|---|---|"]
    # The start note ("0 · …") opens the index and is printed right after it.
    notes = json.loads(nlm(args.profile, "note", "list", args.notebook, "--json"))
    start = [n for n in notes.get("notes", []) if re.match(r"0\s*·", n.get("title") or "")]
    index += [f"| ✎ | {cell(n['title'])} | en este documento |" for n in start]
    body: list[str] = [f"## {n['title']}\n\n{n.get('content', '')}\n" for n in start]
    for a in arts:
        name, kind = a.get("title") or a["type"], a["type"]
        if kind == "video":
            index.append(f"| ▶ | {name} | en la carpeta del tema (Drive) |")
            continue
        index.append(f"| ✎ | {name} | en este documento |")
        body += ['<div class="newpage"></div>', "", f"## {name}", ""]
        if kind == "report":
            body.append(demote(fix_lists(download(args.profile, "report", args.notebook, a["id"], work).read_text())))
        elif kind == "quiz":
            body.append(
                quiz_md(
                    json.loads(
                        download(
                            args.profile,
                            "quiz",
                            args.notebook,
                            a["id"],
                            work,
                            "-f",
                            "json",
                        ).read_text()
                    )
                )
            )
        elif kind == "flashcards":
            body.append(
                flashcards_md(
                    json.loads(
                        download(
                            args.profile,
                            "flashcards",
                            args.notebook,
                            a["id"],
                            work,
                            "-f",
                            "json",
                        ).read_text()
                    )
                )
            )
        elif kind == "mind_map":
            body.append(
                mindmap_html(
                    json.loads(download(args.profile, "mind-map", args.notebook, a["id"], work).read_text()),
                    work,
                )
            )
        else:
            body.append(f"*{html.escape(kind)}: no se imprime.*")
        body.append("")
    md = "\n".join([f"# {title}", "", f"Tu cuaderno: [{url}]({url})", "", *index, "", *body])
    render(md, Path(args.out).expanduser(), work)


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("notebook"), r.add_argument("artifact"), r.add_argument("out")
    r.add_argument("--break-before", metavar="HEADING", help="a new page before this heading")
    t = sub.add_parser("topic")
    t.add_argument("notebook"), t.add_argument("out")
    k = sub.add_parser("link")
    k.add_argument("notebook"), k.add_argument("out")
    for s in (r, t, k):
        who = s.add_mutually_exclusive_group(required=True)
        who.add_argument("--student", help="the student whose notebook.nlm_profile is used")
        who.add_argument("--profile", help="an nlm profile, instead of the student's")
        s.add_argument("--home", default="~/.alfabeta", help="folder of student configurations")
    args = p.parse_args(argv)
    if args.student:
        args.profile = profile_of(args.home, args.student)
    return args


def main() -> None:
    args = parse()
    if args.cmd != "link":
        require_default(args.profile)
    with tempfile.TemporaryDirectory() as tmp:
        {"report": report, "topic": topic, "link": link}[args.cmd](args, Path(tmp))
    print(Path(args.out).expanduser())


if __name__ == "__main__":
    main()
