# AGENTS.md — Chinook semantic models

Instructions for coding agents working in this repository. Humans: this is a
useful summary too, but the long form is in `README.md` and `docs/`.

## What this repository is

Semantic models for the **Chinook** domain in the
[Apache Ossie](https://github.com/apache/ossie) format — the agreed definitions
of the domain's datasets, fields, relationships, and metrics. Downstream agents
and BI tools read these instead of guessing SQL.

The output is `models/**/*.yaml`. Everything else is scaffolding.

## Hard rules

1. **Never invent a column.** Every field expression must reference a column you
   have seen in a real artefact — a DDL dump, `information_schema`, an ORM
   entity, a SQL mapper. If you cannot find it, say so and mark the model
   `inferred`, or leave the field out. A plausible-looking wrong column is the
   single most damaging thing you can add here.
2. **Cite evidence in the file header.** Source of truth, snapshot/commit, and
   verification status go in the comment block at the top of each model file.
3. **`make validate` must pass before you claim done.** Not "should pass".
4. **Do not edit `schema/osi-schema.json` or `scripts/validate.py`.** They are
   vendored from upstream; changing them locally makes the repo lie. To update,
   follow `schema/SOURCE.md` and record the new upstream commit.
5. **`version:` must match the pinned spec version** in `schema/SOURCE.md`. The
   schema declares it as a `const`; any other value fails validation.
6. **Do not weaken a check to make it pass.** If `make verify` flags a
   mismatch, either fix the model or add a dated, reasoned entry to the
   divergence accept-list. Never delete the check.

## Workflow for adding or changing a model

```
1. Read docs/overview.md            → conventions, existing models, decisions
2. Read the source of truth         → DDL / information_schema / mappers / dbt
3. Write or edit models/chinook/<name>.yaml
4. make validate FILE=<that file>   → fix until PASS
5. make verify                      → if a verifier is wired up
6. Update docs/overview.md          → catalogue row + any decision worth keeping
```

## Model shape (Ossie core)

```yaml
version: "0.2.0.dev0"
semantic_model:
  - name: <model_name>              # required
    description: ...
    ai_context: {instructions, synonyms, examples}
    datasets:                       # required
      - name: <dataset>             # required
        source: <db.schema.table>   # required
        primary_key: [<col>]
        fields:
          - name: <field>           # required
            datatype: String | Integer | Decimal | Float | Boolean |
                      Date | Time | DateTime | DateTimeTz | Opaque
            dimension: {is_time: true}      # time dimensions only
            expression:             # required
              dialects:
                - dialect: ANSI_SQL | SNOWFLAKE | BIGQUERY | DATABRICKS |
                           MDX | TABLEAU | MAQL
                  expression: <sql>
    relationships:
      - name: ...                   # all five keys required
        from: <dataset>
        to: <dataset>
        from_columns: [<col>]
        to_columns: [<col>]
    metrics:
      - name: ...                   # required
        expression: {dialects: [...]}   # required
        datatype: ...
```

`additionalProperties: false` applies throughout — an unknown key is an error,
not a warning. Relationships may only reference datasets **inside the same
model file**; cross-file joins go in `docs/overview.md`.

## Writing good definitions, not just valid YAML

- **Metrics carry the business rule.** `net_revenue` excluding cancelled orders
  is the whole point; a metric that is just `SUM(col)` adds nothing a BI tool
  didn't already have.
- **`ai_context` is for disambiguation.** Use `synonyms` for what users actually
  say ("revenue", "sales", "GMV") and `instructions` for the trap someone would
  otherwise fall into ("do not sum gross_amount, it double-counts discounts").
- **`description` explains meaning, not syntax.** Not "the order id column" —
  rather, what an order is and when a row appears.
- **One definition, one place.** If two metrics would compute the same number,
  delete one. Duplicated-but-drifting definitions are the exact problem this
  repository exists to prevent.

## Things that commonly break validation

| Symptom | Cause |
| --- | --- |
| `[Schema] (root): 'x' was expected` | `version` doesn't match the pinned const |
| `[Schema] ... additionalProperties` | typo'd or non-spec key |
| `[Unique] Duplicate ...` | two datasets/fields/metrics share a name |
| `[Reference] ... unknown dataset` | relationship points outside this model file |
| `[SQL] ...` | expression doesn't parse in the declared dialect |
| `Error: Schema not found` | validator run without `--schema schema/osi-schema.json` |
