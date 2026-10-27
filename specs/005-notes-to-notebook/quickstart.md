# Quickstart: proving that notes and Classroom material reach the notebook by themselves

Each step proves one thing on the real accounts and says what to record. Steps 1 to 4 need only the
Mac; steps 5 to 8 need the cloud job. Test content is invented except in step 2, which uses the four
photos of 2026-10-26 and never leaves the operator's machine and the alfabeta workspace.

## Prerequisites

- Spec 004's link of the student's Gmail is `ok` (`python -m alfabeta google check --student <id>`)
  and its scoped Drive adapter is built.
- The student's alfabeta folder in Drive is shared read-only with the notebook owner's account.
- Two API keys in the Claude Console workspace `alfabeta` of the organisation Server Startup, one for
  the Mac's keychain and one for the cloud's secret store. Check first, in *Settings → Profile*, that
  the Console shows the company account.
- A second OAuth Desktop client for the cloud in the same Google Cloud project, its JSON downloaded.
- `nlm login --check --profile <profile>` reports the notebook owner.

## 1. A test topic with its living files

```bash
python -m alfabeta notebook setup --student <id> --topic "<subject>/<test topic folder>"
```

Expect: `{ok: true}` with both sources set; the notebook lists exactly two Drive sources. Run it
again: nothing changes.

## 2. Choose the model on the real notes

Transcribe the four photos of 2026-10-26 with each candidate model and compare each result with the
checked Markdown of that day, line by line.

Record per model: lines that differ in meaning, invented readings (a guess where the checked text
has `[?]`), and `usage` in and out per photo. Choose the cheapest model with no invented reading and
put it in `[notes] model`. Record the cost per page; it replaces the estimate in research R5.

## 3. A photo becomes a page, on the Mac

Upload one invented photo of handwritten notes to the test topic's `apuntes/`, then:

```bash
python -m alfabeta notes run --student <id>
```

Expect: a PDF and a Markdown next to the photo; one page in `Apuntes · <topic>.pdf` headed
«Transcripción automática»; `pages_added: 1`. Open the notebook, wait two minutes, ask about a word
only that page holds. Run again: `pages_added: 0`, and the living file's revision does not change.

## 4. The student's marks

Rename the transcription PDF adding « (mal)», run `notes run`: the page reads «En corrección» and
the report names it. Rename it to « (revisada)», run again: the page reads «Revisada por el alumno».

## 5. The cloud job

Deploy as `docs/how-to/notes-cloud-run.md` says (written with slice 2), including the cloud's own
link: `python -m alfabeta google link --student <id> --account student --client-file <cloud client
JSON> --scopes drive --print-token` piped into `gcloud secrets versions add <google_link_secret>
--data-file=-`, then delete the JSON. Record what each free tier of research R11 showed at setup. Then, with the Mac
**off**, upload a second invented photo from the phone.

Expect, within one hour: the page in the living file and a report in `Informes/`. Record the time
from upload to page. This is SC-001's first measurement.

## 6. A Classroom item

Put an invented PDF named `YYYYMMDD - Prueba` into the test topic's `classroom/` in Drive. Within the
next cloud run: its cover page and pages in `Classroom · <topic>.pdf`; the notebook answers about it
two minutes after being opened. Record the time from upload to the living file (SC-003). Replace the
PDF with a changed one: its pages are replaced, not added. Repeat with an item folder holding a PDF,
a Word file, `descripcion.md` and `enlaces.md`: one entry. Repeat with an assignment folder holding
`enunciado - Prueba.pdf`, `entrega - Prueba.pdf` and `correccion.md`: only the statement's pages
enter.

## 7. Limits and budget

- Read Google's current limit for one notebook source and record it in research R12.
- Set the workspace's spend limit to 0.01 USD for one run: `notes run` exits 0 with `budget_wait > 0`,
  the report says transcription waits, the Classroom step still runs; the next runs that day do not
  report it again. Restore the 10 USD limit.
- Stop the Scheduler job for three hours with the Mac on: the agenda warns that the cloud has not run.

## 8. Two weeks of real use

Record aggregates only, never per-photo times of the student (constitution III): pages uploaded,
the longest and the median delay from upload to living file, pages marked, and whether any notebook
gained a source other than its two living files (SC-005). SC-001 passes when the longest delay is
under an hour. Remove the test
topic, its notebook and its Drive folder by hand at the end; alfabeta removes nothing.
