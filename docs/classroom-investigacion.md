# classroom-sync: investigation (October 2026)

Test run with the account of a 3º ESO student (under 18) at a school with Google Workspace for Education.

| Route | Result | Notes |
|---|---|---|
| **Classroom API via OAuth Playground** | ❌ `Servicio no permitido` (service not allowed) | The school disables Google's developer tools for students. |
| **Classroom API with our own OAuth client** (standard Google Cloud client, read-only scopes) | ❌ `Error 400: access_not_configured` | «El administrador de tu institución debe revisar» (your institution's administrator must review) the app. Google's policy for minors: third-party apps not configured by the school are blocked. It is only unblocked if the school explicitly authorises a specific OAuth client. |
| **Built-in browser with the student's account** (read-only) | ✅ works | It reads the classes, *Tareas pendientes* (to-do) with due dates (this week / next week / later / no due date) and *Trabajo de clase* (Classwork) organised by topic, with the Drive links of every material. Reliable download of Drive attachments is still unsolved. |
| **Email summaries for guardians** | ⏳ not tested | Requires the school to invite the parent as a guardian. Gives pending assignments, upcoming ones and announcements; does not give attachments. It would be read with the Gmail connector. |

## Conclusion

For schools that do not authorise third-party apps (the usual case with under-age students), the API is not an option
without the school's cooperation. `classroom-sync` is built on:

1. **Read-only browser** → assignments, due dates and materials per topic.
2. **Guardian summaries via Gmail** → fallback for due dates and announcements, if the school registers the guardian.
3. **API** only if the school approves an OAuth client of alfabeta's own (formal request to the IT lead).

Rules: never turn in assignments, never open assessments, never modify anything in Classroom.
