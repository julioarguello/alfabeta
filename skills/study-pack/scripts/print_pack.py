#!/usr/bin/env python3
"""Print a topic's Gemini Notebook study material to A4 PDF.

  print_pack.py report <notebook-id> <artifact-id> <out.pdf> [--profile P]
      one report (study guide, practice sheet, parent guide…)
  print_pack.py topic <notebook-id> <out.pdf> [--profile P]
      the whole Studio in one document: an index first, then every report, quiz (answer key at the
      end), flashcards and mind map, in Studio order; videos appear in the index only

Needs `nlm`, `pandoc`, Graphviz `dot` (mind maps) and Google Chrome (headless, prints the PDF).
The profile defaults to `notebook.nlm_profile` in ~/.alfabeta/config.json, else nlm's default.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

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
LIST_ITEM = re.compile(r"\s*([*+-]|\d+[.)])\s")


def profile_default() -> str:
    try:
        cfg = json.loads(Path("~/.alfabeta/config.json").expanduser().read_text())
    except OSError:
        return "default"
    return cfg.get("notebook", {}).get("nlm_profile", "default")


def nlm(profile: str, *args: str) -> str:
    env = {**os.environ, "NLM_PROFILE": profile}
    done = subprocess.run(["nlm", *args], env=env, capture_output=True, text=True)
    if done.returncode:
        sys.exit(
            f"nlm {args[0]} {args[1]} failed: {done.stderr.strip() or done.stdout.strip()}"
        )
    return done.stdout


def download(
    profile: str, kind: str, nb: str, art: str, work: Path, *extra: str
) -> Path:
    out = work / f"{art}.{'md' if kind == 'report' else 'json'}"
    nlm(profile, "download", kind, nb, "--id", art, "-o", str(out), *extra)
    return out


def fix_lists(md: str) -> str:
    """Gemini Notebook omits the blank line pandoc needs before a list; add it."""
    out: list[str] = []
    for line in md.split("\n"):
        if (
            LIST_ITEM.match(line)
            and out
            and out[-1].strip()
            and not LIST_ITEM.match(out[-1])
        ):
            out.append("")
        out.append(line)
    return "\n".join(out)


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
    return "\n".join(
        lines + ["### Erantzunak", "", "| # | | |", "|---|---|---|", *key, ""]
    )


def flashcards_md(data: dict) -> str:
    rows = [
        f"| {cell(card_text(c['front']))} | {cell(card_text(c['back']))} |"
        for c in data["cards"]
    ]
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
    svg = subprocess.run(
        ["dot", "-Tsvg"], input=dot, capture_output=True, text=True, check=True
    ).stdout
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


def report(args: argparse.Namespace, work: Path) -> None:
    md = download(
        args.profile, "report", args.notebook, args.artifact, work
    ).read_text()
    render(fix_lists(md), Path(args.out).expanduser(), work)


def topic(args: argparse.Namespace, work: Path) -> None:
    arts = json.loads(
        nlm(args.profile, "studio", "status", args.notebook, "--full", "--json")
    )
    arts = [
        a
        for a in (arts.get("artifacts", arts) if isinstance(arts, dict) else arts)
        if a.get("status") == "completed"
    ]
    # Studio order is last-modified; a leading "N ·" in the title is the intended order.
    arts.sort(
        key=lambda a: (
            int(m.group(1))
            if (m := re.match(r"(\d+)\s*·", a.get("title") or ""))
            else 99
        )
    )
    title = json.loads(
        nlm(args.profile, "notebook", "get", args.notebook, "--json")
    ).get("title", "")
    index = ["| | Pieza | Dónde |", "|---|---|---|"]
    # The start note ("0 · …") opens the index and is printed right after it.
    notes = json.loads(nlm(args.profile, "note", "list", args.notebook, "--json"))
    start = [
        n for n in notes.get("notes", []) if re.match(r"0\s*·", n.get("title") or "")
    ]
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
            body.append(
                demote(
                    fix_lists(
                        download(
                            args.profile, "report", args.notebook, a["id"], work
                        ).read_text()
                    )
                )
            )
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
                    json.loads(
                        download(
                            args.profile, "mind-map", args.notebook, a["id"], work
                        ).read_text()
                    ),
                    work,
                )
            )
        else:
            body.append(f"*{html.escape(kind)}: no se imprime.*")
        body.append("")
    md = "\n".join([f"# {title}", "", *index, "", *body])
    render(md, Path(args.out).expanduser(), work)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("notebook"), r.add_argument("artifact"), r.add_argument("out")
    t = sub.add_parser("topic")
    t.add_argument("notebook"), t.add_argument("out")
    for s in (r, t):
        s.add_argument("--profile", default=profile_default())
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        (report if args.cmd == "report" else topic)(args, Path(tmp))
    print(Path(args.out).expanduser())


if __name__ == "__main__":
    main()
