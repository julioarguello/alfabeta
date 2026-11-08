# Quickstart: Gmail labels for the notices of shared notebooks

Prerequisite: spec 004's app and client (`google set-client`), and the student's notebooks shared as today.

1. **See the plan.** `python -m alfabeta mail plan --student <id>`. It lists the labels and, per subject, the filter's
   query. The family confirms it before step 3.
2. **Add and link the mail account.** Add to `~/.alfabeta/<id>/config.toml` (keep a copy first) a table
   `[google.accounts.<alias>]` with `role = "mail"`, the student's Gmail as `address`, and the scopes of
   [data-model.md](data-model.md). Then `python -m alfabeta google account link --student <id> --account <alias>`: sign
   in as the student's Gmail; if the account is supervised, a parent approves. Google shows the unverified-app screen
   and the two Gmail permissions; alfabeta uses only what FR-008 lists. Record whether the supervision allowed it.
3. **Apply.** `python -m alfabeta mail apply --student <id>`. Expected: every label and filter `created`, and per subject
   the notices matched and moved out of the inbox.
4. **Apply again.** Expected: everything `existing`, `in_inbox` 0 (SC-002).
5. **The school account.** `python -m alfabeta mail build --student <id> --out ~/Downloads/alfabeta-filtros.xml`. In
   the school account's Gmail, on a computer: the gear → «Ver todos los ajustes» → «Filtros y direcciones bloqueadas» →
   «Importar filtros» → choose the file → «Abrir archivo» → tick «Aplicar los filtros nuevos a los correos existentes»
   → «Crear filtros». Then check the labels in the left column: if any of the labels `mail build` printed is missing,
   create it (`Alfabeta`, then `<grade>` nested under it, then each subject nested under that) and import again. Record
   what the import did. Delete the file after.
6. **The next notebook.** When the next notebook is shared, it lands under its subject's label in both accounts, out of
   the inbox (SC-003).
