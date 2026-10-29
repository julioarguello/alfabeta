# Roadmap

## classroom-sync (proof of concept)

Goal: Classroom feeds each topic's folder and notebook on its own, and due dates reach the calendar.

Routes, from most to least official:

1. **Google Classroom API** (OAuth). The ideal option (assignments, due dates, materials, announcements), but on
   Google Workspace for Education accounts of **under-18s** third-party apps are blocked unless the
   school's administrator authorises them. It has to be tested school by school.
2. **Email summaries for guardians** (official, no risk): pending assignments, upcoming due dates
   and announcements, daily or weekly, to the parent's Gmail. The school or the teachers must invite the guardian.
   Attachments are not included.
3. **Chrome with the Claude extension and the student's account** (read-only): go through the classes, read the
   *Trabajo de clase* (Classwork) tab and download the materials to the topic folder.

Result of the test: the API is blocked for under-age students (see [classroom-investigacion.md](classroom-investigacion.md)); the build is based on route 3 + route 2.

## Calendar

- Source: assignments, exams and posted material from `classroom-sync`.
- Output: events in one calendar per student, owned by a parent and shared with every account in
  `calendar.shared_with` (the student's personal and school accounts), each able to see event details. Only
  objective facts from Classroom, plus warnings that restate those facts at the home slot
  ([spec 003](../specs/003-due-date-warnings/spec.md)); study time is planned by hand.

## Study pack

- Source: the topic folder (class notes, Classroom material, the textbook).
- Output: a few pieces per topic in its notebook — explainer videos, a glossary, practice in the
  subject's language — and a guide for the parent in the Drive.
- Design and evidence: [About preparing study material in advance](explanation/study-material.md).
- From [#20](https://github.com/julioarguello/alfabeta/issues/20) on, the
  [`study-pack` skill](../skills/study-pack/SKILL.md) runs it on request; starting it by itself when
  Classroom moves to a new topic waits for `classroom-sync`.

## Other ideas

- Audio overviews per block of notes, optional; Basque audio quality is poor (see the
  [study-material page](explanation/study-material.md#what-other-people-do)).
- More digital textbook platforms (Santillana, Anaya, Edelvives, Vicens Vives…).
- An English version of the topics the platform does not offer, by translating the Markdown.
