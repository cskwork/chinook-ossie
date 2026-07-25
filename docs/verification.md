# Verification: proving the model matches reality

`make validate` answers *"is this valid Ossie?"*. It says nothing about whether
`analytics.public.orders.net_amount` exists, or is a `Decimal`, or is the column
your BI tool actually reads. A spec-valid model that lies about the warehouse is
worse than no model — agents will confidently generate broken SQL.

So every serious domain repo needs a second layer: **verify**. What that layer
is depends on what your source of truth is.

> **In this repo it is already wired up.** The source of truth is the Chinook
> `CREATE TABLE` script; `scripts/verify_ddl.py` parses it with `sqlglot` and
> `make verify` fails the build on any divergence in table, column, datatype or
> primary key. The rest of this page is the general guidance for other sources —
> keep it if you fork this repo for a different database.

## Pick a source of truth

| You have | Verification approach |
| --- | --- |
| A DDL dump (`mysqldump --no-data`, `pg_dump -s`) | Parse the dump, compare table/column existence, datatype, primary key |
| A live warehouse | Query `information_schema.columns` / `INFORMATION_SCHEMA` and diff |
| dbt | Read `target/manifest.json` — nodes, columns, tests |
| An ERD tool (eXERD, dbdiagram, ERwin) | Export to DDL first, then treat as the DDL case |
| Only application code (ORM entities, MyBatis/SQL mappers) | Grep the mappers for each column; mark the model "inferred", not "verified" |
| Nothing | Say so in `docs/overview.md`. Do not imply verification you did not do. |

## Shape of a verifier

Whatever the source, the check is the same three questions per field:

1. Does the table in `dataset.source` exist?
2. Does every column referenced by a field expression exist in it?
3. Does the declared `datatype` match the physical type, and does
   `primary_key` match the real key?

Wire it into the `verify` target in the `Makefile`, replacing the placeholder:

```make
verify:
	uv run scripts/verify_schema.py $(MODELS) --ddl path/to/dump.sql
```

Keep the exit code honest: non-zero on mismatch, so CI fails.

## Divergence is normal — record it

Sources of truth drift (an ERD lags the migration; a dump predates a hotfix).
Rather than silently loosening the check, keep an explicit accept-list:

```yaml
# scripts/divergences.yaml
- model: models/chinook/chinook_example_model.yaml
  dataset: orders
  field: net_amount
  reason: >-
    Column added in migration 2026-05-11; the DDL dump predates it. Confirmed
    present in staging on 2026-06-02.
```

Each entry needs a reason and a date. An accept-list without reasons becomes a
way to hide rot.

## Grade every model

In `docs/overview.md`, mark each model:

- **verified** — checked against a real schema by `make verify`
- **inferred** — reconstructed from application code, never confirmed
- **proposed** — designed ahead of the tables existing

Downstream consumers (agents, dashboards) need to know which of the three they
are trusting.
