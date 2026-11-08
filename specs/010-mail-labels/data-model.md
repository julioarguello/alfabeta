# Data model: Gmail labels for the notices of shared notebooks

No new configuration key and no new state file. Everything is derived from keys that exist.

| Entity | Fields | Comes from |
|---|---|---|
| **Label plan** | ordered names: `Alfabeta`, `Alfabeta/<grade>`, then `Alfabeta/<grade>/<folder>` per subject in configuration order | `[student] grade_level`, `[[subjects]] folder` |
| **Filter plan** | per subject: `subject` (folder), `label` (name), `query` | `[notebook] title_pattern` cut before `{topic}` (FR-003), the senders of research R1, FR-004 |
| **Mail link** | a `[google.accounts.<alias>]` table with `role = "mail"`, the student's Gmail address, `scopes` of FR-007 | the student's configuration (spec 004's LinkedAccount) |
| **Apply report** | `labels: [{name, status: created\|existing}]`, `filters: [{subject, status: created\|existing\|differs}]`, `existing_mail: [{subject, matched, in_inbox}]` or `existing_mail: {skipped: "<reason>"}` | `mail apply` |

## The mail link in the configuration

The account table follows spec 004's template; only the role and the scopes are new. Invented values:

```toml
[google.accounts.mailbox]
role = "mail"
address = "student@example.com"
scopes = [
  "https://www.googleapis.com/auth/gmail.settings.basic",
  "https://www.googleapis.com/auth/gmail.modify",
  "openid",
  "email",
]
```

`mail apply` uses the one account with role `mail`; none, or more than one, is `invalid_config`. Without `gmail.modify`
among its configured scopes the existing-mail step is `skipped: "no_modify_scope"`.

## Rules

- The query starts with `from:(<sender 1> OR <sender 2>) ` always, the two senders of research R1; the adapter
  refuses any other query (FR-008).
- The labels it may add are those of the label plan; the only label it may remove is `INBOX`.
- Nothing is persisted on the Mac: Gmail holds the labels and filters, and the next run reads them again.
