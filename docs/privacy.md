# Privacy

alfabeta is a tool a family runs on its own Mac to organise a secondary-school student's study
material and calendar. It is not a service: there is no alfabeta server, no account with us, and
nobody outside the family operates it. The code is public in this repository.

This page describes what alfabeta's own Google app does with the data a family lets it reach. The
app is registered in a Google Cloud project by the parent who runs alfabeta, and is used only by
that family's accounts.

## What alfabeta asks Google for, and why

| Permission | What alfabeta does with it |
|---|---|
| See your email address (`openid`, `email`) | Checks, on the family's Mac, that the account that signed in is the one the family configured. The address is never printed, logged or sent anywhere |
| View and edit events on your calendars (`calendar.events`) | Creates and updates events in the family calendar (due dates, exams, material the school posted), with reminders that ring for the account that signed in |
| See, edit, create and delete your Google Drive files (`drive`) | Uploads the student's study material into the `alfabeta` folder of that Drive and checks each file arrived. alfabeta's own code refuses any read or write outside that folder |

## Where the data goes

- **Only between the family's Mac and the family's own Google accounts.** alfabeta sends nothing to
  any other company or person. It has no analytics, no advertising and no telemetry.
- **The authorisation Google returns** (a refresh token) is kept in the macOS keychain of the
  family's Mac. It is never written to this repository, to a configuration file or to a log.
- **Nothing is sold, shared or used to train any model.**
- The student is a minor. alfabeta keeps only what its function needs, and the family decides and
  answers for its use.

alfabeta's use and transfer of information received from Google APIs to any other app will adhere
to the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements.

## How to stop it

- Remove alfabeta from the account's third-party access, in
  [Google Account → Security → Your connections to third-party apps & services](https://myaccount.google.com/connections).
  This revokes the authorisation at once.
- Or, on the family's Mac: `python -m alfabeta google unlink --student <id> --account <alias>`,
  which revokes it and deletes it from the keychain.
- What alfabeta wrote stays in the calendar and the Drive, where the family can keep or delete it.

## Contact

Questions about this page: open an issue in this repository. Do not include personal data in it.

---

## Resumen en español

alfabeta es una herramienta que una familia ejecuta en su propio Mac. No hay servidor ni empresa
detrás. Su aplicación de Google pide tres cosas:

- ver la dirección de la cuenta, solo para comprobar que se ha vinculado la cuenta correcta;
- crear y modificar eventos del calendario familiar, con sus avisos;
- escribir el material de estudio en la carpeta `alfabeta` de Drive, y nunca fuera de ella.

Los datos van solo del Mac de la familia a sus propias cuentas de Google. La autorización se
guarda en el llavero del Mac. No se comparte nada con nadie, no se vende ni se usa para entrenar
modelos. Para cortar el acceso, quita alfabeta en
[las conexiones de terceros de la cuenta de Google](https://myaccount.google.com/connections).
