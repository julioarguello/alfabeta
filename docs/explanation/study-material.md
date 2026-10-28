# About preparing study material in advance

**If you are deciding what alfabeta should generate for a student**, from which sources, in which
language and when, start at [The problem](#the-problem). **If you are checking whether a rule is
backed by evidence or is a guess**, go to [The design, rule by rule](#the-design-rule-by-rule). The
steps themselves live in the skills and the [specification](../../specs/001-classroom-sync/spec.md).

**Read first**: [roadmap](../roadmap.md) — what each component is for.

| Section | You are… |
|---|---|
| [The problem](#the-problem) | wondering why this needs a design at all |
| [Three sources, one order of trust](#three-sources-one-order-of-trust) | deciding what to believe when the notes, Classroom and the book disagree |
| [What the evidence says](#what-the-evidence-says) | asking which study techniques are worth generating material for |
| [What other people do](#what-other-people-do) | looking for someone who already tried it |
| [What we measured on Gemini Notebook](#what-we-measured-on-gemini-notebook) | about to rely on a platform behaviour |
| [The design, rule by rule](#the-design-rule-by-rule) | implementing or reviewing the study-pack job |
| [Alternatives we rejected](#alternatives-we-rejected) | about to propose one of them |
| [Open questions](#open-questions) | planning the next measurement |

---

## The problem

A secondary-school student studies different subjects in two or three languages, and the parent who
helps at home does not speak one of them. The material arrives from three places at different
speeds: what the student writes in class, what the teacher posts in Google Classroom, and a digital
textbook.

Preparing for an exam the night before means reading everything, in three languages, with no idea
of what actually matters. Generating study material with an AI the night before is worse: a pile of
summaries, videos and quizzes nobody can tell apart, some of them wrong, in whatever language the
tool picked.

The point of alfabeta is to move that work earlier and make it smaller: prepare the material as the
teacher posts it, keep only what the exam is likely to ask, and make the student *practise*, not
re-read.

## Three sources, one order of trust

| Source | What it tells us | Trust |
|---|---|---|
| The student's own class notes (photos of the notebook) | What was actually taught, in the words used in class | Highest |
| Google Classroom (the teacher's posts, handouts, exercise sheets, exam announcements) | What the teacher chose to stress and to assess | Middle |
| The digital textbook (Science Bits) | The full curriculum unit, well explained | Lowest for scope, highest for explanation |

The order is about **scope**, not about truth. The textbook explains better than anything else, but
it is the worst guide to what will be asked. A worked case from 2026-10-26: the textbook unit on
pure substances and mixtures never mentions concentration, while the teacher's two exercise sheets
drill about thirty concentration and density problems — the core of the exam.

Teacher material **prioritises** the scope; it does not limit it. What the textbook covers and the
teacher never touched still exists, at low priority.

Trust also has limits in the other direction. On the same date, the teacher's answer key had three
wrong answers out of eighteen: the key gave 25.85 % where the answer is 5.08 %, 0.13 g/mL where the
density is 1.095 g/mL, and the wrong sign on an exponent. Material generated for the student never copies an answer key:
every numeric answer is recomputed.

## What the evidence says

Labels: **[MA]** meta-analysis or systematic review, **[RCT]** randomised trial, **[EXP]** single
experiment.

| Technique | Evidence | What it means for the material |
|---|---|---|
| Retrieval practice (quizzes, flashcards, recalling without looking) | [MA] classroom quizzing g = 0.50 across 222 studies ([Yang et al. 2021](https://scholars.hkbu.edu.hk/en/publications/testing-quizzing-boosts-classroom-learning-a-systematic-and-meta-/)); [EXP] one week later 61 % vs 40 %, while re-readers felt *more* confident ([Roediger & Karpicke 2006](https://psychology.ecu.edu/wp-content/pv-uploads/sites/216/2019/03/Roediger-Karpicke-2006.pdf)); rated high utility by [Dunlosky et al. 2013](https://www.psychologicalscience.org/news/releases/which-study-strategies-make-the-grade.html) | Practice is the main course; summaries are the starter |
| Spacing | [MA] the best gap grows with the retention interval ([Cepeda et al. 2006](https://digitalcommons.usf.edu/psy_facpub/1771/)); high utility (Dunlosky) | Several short sessions before an exam, not one long one |
| Interleaving | [RCT] 7th-grade maths, 61 % vs 38 % a month later ([Rohrer, Dedrick, Hartwig & Cheung 2020](https://doi.org/10.1037/edu0000367)); [MA] positive for maths, negative for vocabulary ([Brunmair & Richter 2019](https://www.psychologie.uni-wuerzburg.de/fileadmin/06020400/2019/Brunmair_Richter_in_press__2019_META-ANALYSIS_OF_INTERLEAVED_LEARNING.pdf)) | Mix problem types once each is known; never mix glossary lists |
| Worked examples, then faded ones | [MA] Barbieri et al. 2023, 55 studies in mathematics, as summarised by [The Learning Scientists](https://www.learningscientists.org/blog/2024/1/25-1); the benefit fades as expertise grows ([Kalyuga](https://my.chartered.college/?p=5912)) | For numeric topics: one solved example, two with the last steps blank, then a mixed set |
| Short, segmented video | [MA] segmenting helps ([Rey et al. 2019](https://is.mpg.de/publications/rey2018segmenting)); edX data suggests keeping videos under six minutes ([Guo, Kim & Rubin 2014](https://www.cs.rochester.edu/hci/pubs/pdfs/edX-MOOC-video-production-and-engagement_LAS-2014.pdf)) | One short video per block of content, never a long one per topic |
| Passive review | Re-reading, highlighting and summarising: low utility (Dunlosky) | Overviews and study guides only as a way in, each ending with questions |
| Unrestricted AI help | [RCT] ~1,000 high-school maths students: unrestricted GPT raised practice scores and lowered exam scores by 17 %; a tutor that gave hints largely avoided the harm ([Bastani et al., PNAS 2025](https://ideas.repec.org/a/nas/journl/v122y2025pe2422633122.html)) | The tutor gives hints, never the answer first |
| Learning in one language, tested in another | [EXP] arithmetic learned in one language is slower and more error-prone in the other ([Saalbach et al. 2013](https://boris.unibe.ch/45901/)) | Explain in the family's language if it helps understanding; practise in the subject's language |

The last row is the weakest link in the design: the switching-cost studies are about arithmetic,
not science, and nobody we found measured a bilingual glossary in secondary science.

## What other people do

Cases opened and read on 2026-10-26. SEO listicles were discarded. **None of the cases we found
describes a parent who does not speak the language of instruction**, so that part of the design rests
on no precedent we know of.

| Who | What they do | What we take from it | Credibility |
|---|---|---|---|
| [HABE / Irakasbil, 2025-05-27](https://www.ikasten.ikasbil.eus/mod/habecms/view.php/irakasbil/didakteka/notebooklm_irakasleentzako_gida_praktikoa) — Basque Government guide for teachers | Set the output language to Basque, upload structured documents, generate podcasts and maps | Basque output works with language errors; everything needs review | High |
| [Sustatu, 2025-04-30](https://sustatu.eus/1745999735), with linguist Ekaitz Santazilia | Audio overviews in Basque from Basque sources | Pronunciation and dates are poor; Spanish works clearly better — a reason to keep videos in Spanish | Medium-high |
| [Profesor Productivo, 2026-01-05](https://profesorproductivo.com/blog/como-transformar-apuntes-manuscritos-con-notebooklm/) | Photos of handwritten notes → literal transcription → compare → upload the corrected text as a source | Transcribe and verify before trusting notes; drawings are not digitised | Medium |
| [AI Family Network, 2026-02-24](https://aifamilynetwork.substack.com/p/notebooklm-study-plan) — a parent with a 6th-grader | One notebook per unit, key topics chosen together, three evenings of 20–25 minutes, extra material only where gaps appear | The closest case to ours: a parent as home tutor | Medium |
| [Tufino, arXiv 2504.09720](https://arxiv.org/abs/2504.09720) (accepted in *The Physics Educator*) | A written "training manual" that makes the notebook ask instead of answer, for physics | The basis for the tutor's instructions; motivation is the hard part | High |
| [Ed Price, UW-Milwaukee, 2025-07-05](https://uwm.edu/advancing-learning/notebooklms-audio-overview-feature-a-powerful-learning-tool/) | One audio overview per block of notes, optional | Generate per block, not per topic | High |
| [David Roca, 2026-05-25](https://davidroca.substack.com/p/guia-notebooklm-para-profesionales-4df) | One notebook per unit, few good sources, descriptive dated names, talk to the notebook before generating | His typical failures — too many sources, summaries without practice — are the ones we design against | Medium |
| [Android Authority, 2025-10-04](https://www.androidauthority.com/notebooklm-lacks-crucial-feature-3603778/) vs [Google, 2025-04-03](https://blog.google/technology/google-labs/notebooklm-studying-help/) | Figures in PDFs are lost / are understood | Unresolved; to be measured on the textbook | Medium / vendor |

## What we measured on Gemini Notebook

Measured 2026-10-26 with [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli)
0.15.7 (`nlm`) and the web interface, on an adult Google AI Pro account. Gemini Notebook is the
name NotebookLM took on 2026-07-16
([Workspace Updates](https://workspaceupdates.googleblog.com/2026/07/notebooklm-now-gemini-notebook.html)).

| What | Result |
|---|---|
| Language of quizzes and flashcards | `nlm` has no `--language` flag for them and sends `hl=en` unless `NOTEBOOKLM_HL` is set; a quiz asked for "in Basque" in its focus prompt came out in English. With the web setting *Idioma de destino* (output language override) on Basque, a quiz created through `nlm` came out entirely in Basque, title included. |
| Scope of that setting | Account-wide, not per notebook: changing it in one notebook changed it in another, and that notebook's overview re-rendered in Basque. |

> [!WARNING]
> The output language override applies to every notebook of the account. Switch it back after
> generating, or the owner's other notebooks start answering in the subject's language.
| Reports | `--language eu` produces a report entirely in Basque, whatever the language of the prompt. |
| Order of the Studio list | By last modification: renaming an item moves it to the top. |
| Renaming and deleting | A rename keeps any title verbatim (`Paso 2 · Quiz · …`); a delete removes the item cleanly, so one live version per item can be enforced. |
| Custom chat instructions | Stored per notebook and applied for the owner (Spanish, hints instead of answers). In one sample the chat invented that a note had been written by the teacher. |
| Notes | One measurement found the chat ignoring a note's content; the same day the interface announced that notes can be chatted with and cited. Unsettled. |

Documented, not measured by us: Spanish and Basque are supported for Explainer and Short video
overviews; cinematic video is English-only and 18+; only owners and editors generate, viewers
consume; a viewer's chat history is private
([video](https://support.google.com/notebooklm/answer/16454555),
[chat](https://support.google.com/notebooklm/answer/16179559),
[sharing](https://support.google.com/notebooklm/answer/16206563)). Usage limits are compute-based,
refreshed every five hours up to a weekly cap
([usage limits](https://support.google.com/gemininotebook/answer/17670842)).

## The design, rule by rule

Each rule names what supports it. **Hypothesis** means nothing measured or published backs it yet.

| Rule | Support |
|---|---|
| One notebook per topic, owned by an adult account and shared as a viewer with every account in `notebook.share_with` (the student's personal and school accounts) | Sharing outside a company domain depends on its admin ([admin help](https://knowledge.workspace.google.com/admin/generative-ai/gemini-notebook/manage-gemini-notebook-sharing-settings)); measured 2026-10-26, the student's school domain allowed a notebook owned by a personal Gmail account to be shared with the school account as viewer, and it opened there. An adult owner avoids the 18+ limit on cinematic video |
| Notes > Classroom > textbook for scope | The worked case above; Profesor Productivo for the notes |
| Every source carries its kind and date in its name (`APUNTES · 2026-10-14 · p2`, `CLASSROOM · …`, `LIBRO · …`), and the tutor is told the order of trust | Roca for names; the tutor instruction is a **hypothesis** |
| Notes are transcribed literally and checked before they become a source; the student checks their own handwriting | Profesor Productivo; the student as checker is a **hypothesis** (the parent may not read the language of the notes) |
| When material arrives: add it as a source, generate nothing | Roca (talk before generating) |
| When the teacher opens a new topic in Classroom, the previous one is closed: generate its explainer videos, one per block of content, plus the glossary | Segmenting and video length (evidence table); the topic-jump signal is a **hypothesis** to check across subjects |
| When an exam is announced: practice in the subject's language (worked → faded → mixed problems, a quiz, flashcards) and a short plan of a few 20–25-minute sessions, kept as a note for the family — never in the calendar | Retrieval, spacing, worked examples; AI Family Network for the session length |
| Videos and the parent's material in Spanish; practice in the subject's language | Sustatu and HABE on Basque audio quality; Saalbach on switching; the split itself is a **hypothesis** |
| Few pieces for the student, each named by what it is, what about and how long (`Vídeo 4 min · Kontzentrazioa`) | Choice overload ([Chernev et al. 2015](https://www.kellogg.northwestern.edu/faculty/research/detail/2015/when-product-assortment-leads-to-choice-overload-a-conceptual)); the count is a **hypothesis** |
| The parent's material (topic map, recomputed answer key, translated exercises, a questioning guide with the Basque term) lives in a `docente/` folder of the Drive, not in the notebook | A viewer sees everything in Studio (sharing help) |
| Numeric answers are recomputed before any material reaches the student, except the exam sheets of `exam prep`, whose numbers the notebook computes (an accepted risk, spec 002 FR-036) | The answer-key errors above |
| The tutor gives hints before answers and never attributes authorship | Bastani et al.; the invented attribution measured above |
| The calendar holds only objective Classroom facts — assignments, exams, posted material — never study blocks | A family decision: study time is planned by hand |

## Alternatives we rejected

- **A second notebook for the parent.** It doubles the sources to maintain; a Drive folder does the
  job without another notebook to keep in step.
- **One video per textbook lesson.** Lessons are the book's structure, not the teacher's; some never
  reach the exam and others hold content the book lacks.
- **Generating everything on every sync.** One topic would have regenerated the same video three
  times in a week as the teacher added sheets, each time replacing what the student had already
  watched.
- **Generating only when an exam is announced.** Too late for spaced practice, and some exams are
  only announced in class.
- **Explaining and practising in Spanish only.** Comfortable for the parent, but the exam is not in
  Spanish.
- **Downloading attachments with `curl` outside the browser.** It needs the school session's cookies,
  a secret no tool may handle ([research R12](../../specs/001-classroom-sync/research.md#r12-from-the-browser-to-disk)).

## Open questions

- What the student sees as a viewer: the Studio order, the notes, whether their chat inherits the
  owner's custom instructions, whether they can take the quizzes.
- How many transcription errors a page of a teenager's handwriting produces.
- Whether figures in the textbook's PDFs survive as sources.
- Whether notes are read by the chat (two contradictory signals on the same day).
- Whether setting `NOTEBOOKLM_HL` changes the language of quizzes and flashcards created through `nlm`.
- Whether the topic-jump signal holds for teachers who reuse old topics or post out of order.
- Whether the school's own Google Workspace for Education account offers Gemini Notebook to the
  student; since August 2025 it is a core service for all ages, which a school admin can switch off
  ([heise](https://www.heise.de/en/news/Google-opens-NotebookLM-to-younger-users-10509578.html?view=print)).

## Read next

- [Roadmap](../roadmap.md) — the order in which these pieces get built.
- [Specification 001](../../specs/001-classroom-sync/spec.md) and its
  [research notes](../../specs/001-classroom-sync/research.md) — the Classroom sync this design sits on.
