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
3. **Built-in browser with the student's account** (read-only): go through the classes, read the
   *Trabajo de clase* (Classwork) tab and download the materials to the topic folder.

Result of the test: the API is blocked for under-age students (see [classroom-investigacion.md](classroom-investigacion.md)); the build is based on route 3 + route 2.

## plan-de-estudio

- Source: assignments and exams from `classroom-sync`.
- Output: Google Calendar events (assignment/exam) and spaced review blocks before each exam,
  linking to the topic's notebook.

## Other ideas

- Automatically generate in the notebook: audio overview, flashcards and quiz per topic.
- More digital textbook platforms (Santillana, Anaya, Edelvives, Vicens Vives…).
- An English version of the topics the platform does not offer, by translating the Markdown.
