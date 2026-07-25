# Evidence: building a model from what actually exists

The rule: **every dataset, field, and datatype in a model traces to something
you read.** This file is about where to read it and how much to trust it.

## Trust ordering

| Rank | Artefact | Gives you | Watch out for |
| --- | --- | --- | --- |
| 1 | Live `information_schema` / `INFORMATION_SCHEMA` | tables, columns, types, nullability, keys | needs credentials; snapshot the query output |
| 2 | Structure-only DDL dump (`mysqldump --no-data`, `pg_dump -s`) | same, minus drift since the dump | dumps go stale; check the date |
| 3 | dbt `target/manifest.json` | models, columns, descriptions, tests, lineage | describes dbt's view, not necessarily the warehouse |
| 4 | ERD exports (eXERD, ERwin, dbdiagram) | types, PKs, intended relationships | design artefacts lag migrations |
| 5 | ORM entities / migrations | columns, types | migrations may be unapplied in some environments |
| 6 | SQL mappers, handwritten queries (MyBatis, raw SQL) | column *existence* and usage only | no types, no PKs — never infer a datatype from these |
| 7 | API responses, UI screens | business meaning, synonyms | field names are renamed on the way out |

Anything at rank 5 or below produces an **inferred** model, not a verified one.

## Extraction recipes

**DDL dump → dataset skeleton.** Parse `CREATE TABLE` statements; each becomes a
candidate dataset, each column a candidate field, `PRIMARY KEY (...)` becomes
`primary_key`. Map physical types to the spec enum — `DECIMAL`/`NUMERIC` →
`Decimal`, `TIMESTAMP WITH TIME ZONE` → `DateTimeTz`, `TIMESTAMP` → `DateTime`,
`JSON`/`GEOMETRY` → `Opaque`.

**Warehouse → dataset skeleton.**

```sql
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'analytics'
ORDER BY table_name, ordinal_position;
```

Save the output into the repo (git-ignored is fine) so the model is reviewable
against a fixed snapshot rather than a moving database.

**dbt → model.** `manifest.json` → `nodes[*].columns` for names and
descriptions, `nodes[*].relation_name` for `source`. dbt tests
(`unique`, `not_null`, `relationships`) are good evidence for `primary_key` and
for Ossie `relationships`.

**Application code → model.** Grep the mappers/queries for each table, collect
the columns actually selected, and take *only existence* from them. Get types
from a rank 1–4 artefact, or declare the model inferred and say the datatypes
are unconfirmed.

## Don't model everything

A dump of 400 tables is not 400 datasets. Include a table when it carries a
concept someone asks questions about. Skip audit columns, sync scaffolding,
staging clones, and soft-delete bookkeeping unless a metric depends on them.
The model is a curated interface, not a mirror.

## Metrics come from people, not schemas

No artefact contains "net revenue excludes cancelled orders". That lives in
dashboards, SQL that analysts actually run, and someone's head. Sources, in
order of usefulness:

- Existing BI/dashboard definitions (Looker LookML, Tableau calcs, Metabase
  questions) — these are the definitions currently in use, drift included.
- Recurring report queries in the codebase or a scheduler.
- The team. When definitions conflict between tools, that conflict *is* the
  finding — record both in `docs/overview.md` and get a decision rather than
  silently picking one.

## Grading, and being honest about it

Mark every model in `docs/overview.md`:

- **verified** — an automated check (`make verify`) compares it to a real schema
  and passes.
- **inferred** — reconstructed from code or stale artefacts; plausible,
  unconfirmed.
- **proposed** — the tables do not exist yet.

Never upgrade a grade because the model *looks* right. Downstream consumers
choose how much to trust a definition based on this column; inflating it is the
one unrecoverable mistake in a semantic layer.

## File header template

```yaml
# <Domain> — <scope of this model>
#
# Source of truth: information_schema @ analytics-prod
# Evidence:        .evidence/columns-2026-07-25.csv
# Verified:        yes — `make verify` (datatypes + PKs)
# Notes:           tb_legacy_* excluded; superseded by orders_v2 in 2026-03
```
