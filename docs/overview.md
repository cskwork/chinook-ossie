# Chinook semantic model catalogue

| Model | Scope | Source of truth | Status |
| ----- | ----- | --------------- | ------ |
| `models/chinook/chinook_sales_model.yaml` | Invoices, invoice lines, customers, support reps, and the track / album / artist / genre catalogue | `Chinook_PostgreSql.sql` from [lerocha/chinook-database](https://github.com/lerocha/chinook-database) | **verified** — `make verify` |

Status values: **verified** (checked by `make verify` against a real schema),
**inferred** (reconstructed from application code), **proposed** (designed before the
tables exist).

## Naming conventions

- Datasets are named after the physical table, singular: `invoice`, `invoice_line`.
- Fields keep the physical column name where it is already clear. Where the column name
  is ambiguous out of context the field is renamed and the physical name stays in the
  expression — `track.name` → `track_name`, `invoice.total` → `invoice_total`,
  `employee.title` → `job_title` (it is a job title, not a media title).
- Derived fields state the derivation in the expression rather than hiding it in a view:
  `line_amount = unit_price * quantity`, `duration_seconds = milliseconds / 1000.0`.
- Metrics are named for the business term, not the aggregation: `net_revenue`, not
  `sum_line_amount`.

## Decisions

**Revenue is summed at line grain, never from `invoice.total`.** `invoice.total` is
denormalised in Chinook; summing it across a join to `invoice_line` multiplies revenue by
the line count. Both the metric definition and the model-level `ai_context` say so.
`invoice_total` is still exposed as a field, because it is legitimate when `invoice_line`
is not in the query — that caveat lives on the field's description.

**`billing_country` over `customer.country` for revenue geography.** Billing country is
fixed at purchase time; the customer's country is current-state and silently rewrites
history when they move. Both are modelled, with the choice documented on each.

**`unit_price` appears twice on purpose.** `invoice_line.unit_price` is what was charged;
`track.catalogue_price` is today's list price. They are different facts that happen to
share a column name, and conflating them misprices historical revenue.

**Playlists and media types are excluded.** They exist in the schema and answer none of
the questions this model is for. Adding them later is cheap; carrying them unused makes
the model harder to read now.

**`duration_seconds` is `Float`, prices are `Decimal`.** Money never gets a binary float.
The verifier enforces declared types against physical ones, so this is checked rather
than asserted.

## Cross-model joins

Only one model file exists, so every relationship is expressible as an Ossie
`relationship`. If a second model is added (playlists, say), the joins between files
belong here — Ossie relationships cannot cross model files.

## Evidence

`make evidence` fetches `Chinook_PostgreSql.sql` into `.evidence/` (git-ignored — it is
reproducible from a URL, so committing 15k lines of it would be noise). `make verify`
depends on it. If upstream Chinook changes its schema, `make verify` is what tells you.
