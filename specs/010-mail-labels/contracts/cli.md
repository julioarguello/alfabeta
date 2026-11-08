# Contract: the `mail` commands

A new group, `mail`: the student's mailbox, its labels and filters for alfabeta's notices. Every command takes
`--student <id>`. Exit codes as the rest of the CLI: 0 ok, 1 invalid, 2 link.

| Command | Does | Stderr | Stdout (JSON) | Exit |
|---|---|---|---|---|
| `mail plan --student <id>` | Computes the label and filter plans from the configuration. No network, no link. | one line per label, then per filter: subject and label | `{ok, labels: [name], filters: [{subject, label, query}]}` | 0 · 1 on `invalid_title_pattern` or `invalid_config` |
| `mail apply --student <id>` | As the account with role `mail`: creates missing labels and filters, then, with `gmail.modify`, labels the notices already there and takes them out of the inbox (FR-005 to FR-009). | per label and filter its status; per subject `matched` and `in_inbox`; or why the step was skipped | the apply report of [data-model.md](../data-model.md), with `ok` | 0 · 1 on `invalid_title_pattern` or `invalid_config` · 2 on `revoked`, `expired`, `no_token`, `missing_scope`, `network` |
| `mail build --student <id> --out <file>` | Writes the plan as Gmail's filter import file (FR-010), for an account alfabeta cannot link. No network, no link. | the number of filters and the labels to create by hand if the import does not | `{ok, filters: <n>, out: <file>}` | 0 · 1 as `mail plan`, or `invalid_out` when the file cannot be written |

On exit 2 the message names the alias and says `google account link --student <id> --account <alias>`.

No output holds an address, a token, a message id or a word of a message.
