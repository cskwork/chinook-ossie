# Ossie core spec — working reference

Derived from `core-spec/osi-schema.json` in apache/ossie (spec version
`0.2.0.dev0`). The vendored schema in your repo is authoritative; when they
disagree, believe the schema and update this file.

## Top level

```yaml
version: "0.2.0.dev0"   # const — must equal the version pinned by your schema
semantic_model: [ ... ] # required, array of models
```

Only these two keys exist at the root. `additionalProperties: false` applies at
every level of the schema.

## SemanticModel

Required: `name`, `datasets`.

| Key | Notes |
| --- | --- |
| `name` | Unique within the file |
| `description` | Prose; what this model covers |
| `ai_context` | String, or object `{instructions, synonyms[], examples[]}` |
| `datasets` | Required, array |
| `relationships` | Joins between datasets **in this model only** |
| `metrics` | Model-level; may reference any dataset in the model |
| `custom_extensions` | Vendor-specific escape hatch |

## Dataset

Required: `name`, `source`.

| Key | Notes |
| --- | --- |
| `name` | Logical name; unique within the model |
| `source` | Physical reference — `database.schema.table`, a view, or a query |
| `primary_key` | Array of column names (composite keys: list them all) |
| `unique_keys` | Additional uniqueness constraints |
| `description`, `ai_context` | As above |
| `fields` | Array of Field |

`source` is a free string. Be consistent across the repo — either always
fully-qualified or always schema-relative, never mixed.

## Field

Required: `name`, `expression`.

| Key | Notes |
| --- | --- |
| `name` | Unique within the dataset |
| `expression` | Required — `{dialects: [{dialect, expression}]}` |
| `datatype` | Enum, below |
| `dimension` | `{is_time: true}` — mark time dimensions, nothing else goes here |
| `label` | Human-facing name; use when `name` mirrors a cryptic column |
| `description`, `ai_context` | As above |

A field expression is usually just the column name, but it can be any
expression over the dataset's source (`gross_amount - discount_amount`,
`LOWER(email)`).

## Metric

Required: `name`, `expression`. Optional: `description`, `datatype`,
`ai_context`, `custom_extensions`.

Metrics are aggregations. Qualify columns with the dataset name
(`SUM(orders.net_amount)`) so the definition is unambiguous.

## Relationship

Required: **all five** of `name`, `from`, `to`, `from_columns`, `to_columns`.

```yaml
- name: orders_to_customers
  from: orders                # dataset name in THIS model
  to: customers               # dataset name in THIS model
  from_columns: [customer_id] # minItems: 1
  to_columns: [customer_id]
```

Composite keys: list the columns in matching order in both arrays.

## Enums

**`datatype`** — `String`, `Integer`, `Decimal`, `Float`, `Boolean`, `Date`,
`Time`, `DateTime`, `DateTimeTz`, `Opaque`.

Money is `Decimal`, never `Float`. Anything with a timezone is `DateTimeTz`.
`Opaque` is for types the spec cannot express (JSON blobs, geometry) — use it
rather than lying with `String`.

**`dialect`** — `ANSI_SQL`, `SNOWFLAKE`, `MDX`, `TABLEAU`, `DATABRICKS`,
`MAQL`, `BIGQUERY`.

Write `ANSI_SQL` unless you need engine-specific syntax; add other dialects
alongside it rather than replacing it. `MDX`, `TABLEAU` and `MAQL` expressions
are skipped by the SQL parser.

## What the validator checks

`scripts/validate.py` (vendored from `validation/validate.py`) runs four passes:

1. **Schema** — structure, types, enums, required keys, `additionalProperties`.
2. **Unique names** — datasets and metrics and relationships within a model;
   fields within a dataset.
3. **References** — `from`/`to` name datasets that exist in the same model.
4. **SQL** — each dialect expression parses via `sqlglot`, first standalone,
   then as `SELECT <expr>`. Best-effort: missing `sqlglot` yields a warning, not
   an error.

The upstream validator takes **one file at a time** and defaults its schema
path to `../core-spec/osi-schema.json` relative to itself — which does not exist
in a domain repo. Always pass `--schema schema/osi-schema.json`; the generated
`Makefile` loops over files and does this for you.

## Error → cause

| Message | Cause |
| --- | --- |
| `[Schema] (root): '0.2.0.dev0' was expected` | `version` mismatch with the vendored schema |
| `[Schema] ...: Additional properties are not allowed` | typo'd or non-spec key |
| `[Schema] ...: 'expression' is a required property` | field/metric without `expression.dialects` |
| `[Schema] ...: '<x>' is not one of [...]` | bad `datatype` or `dialect` |
| `[Unique] Duplicate ...` | repeated name at the same level |
| `[Reference] ... references unknown dataset` | relationship crosses model files, or dataset typo |
| `[SQL] ...` | expression fails to parse in its dialect |
| `Error: Schema not found` | `--schema` missing |
| `Missing dependencies` | run under `uv`, or `pip install pyyaml jsonschema sqlglot` |

## Beyond the core spec

`custom_extensions` exists for vendor concepts the core spec has no room for.
Prefer it over inventing top-level keys — the latter fails validation, the
former is explicitly allowed. Anything you put there is, by definition, not
portable; note it in `docs/overview.md`.
