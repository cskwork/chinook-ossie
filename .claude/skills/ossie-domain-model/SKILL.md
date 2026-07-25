---
name: ossie-domain-model
description: Author, validate, and review Apache Ossie (formerly OSI) semantic models for a business domain — datasets, fields, relationships, and metrics in vendor-agnostic YAML that agents and BI tools share. Use when creating or editing files under models/**/*.yaml in an Ossie repo, bootstrapping a new domain semantic-model repository, converting a DDL dump / dbt manifest / SQL mappers into a semantic model, defining or reconciling metric definitions across tools, or when the user mentions Ossie, OSI, osi-schema.json, or "semantic model".
---

# Ossie domain semantic models

Ossie models are the shared answer to *"what is net revenue?"*. They are cheap
to write and expensive to get wrong: a plausible-but-fictional column ships
broken SQL to every consumer downstream. Evidence first, YAML second.

## Which situation are you in?

**No repository yet** → bootstrap one:

```bash
git clone https://github.com/cskwork/ossie-domain-kit
./ossie-domain-kit/bootstrap-ossie-domain.sh <domain> <target-dir>
cd <target-dir> && make validate      # example model must PASS
```

**Repository exists** → read `AGENTS.md` and `docs/overview.md` first. They
carry the repo's conventions, existing models, and past decisions. Follow those
over anything here.

## Authoring loop

1. **Find the source of truth before writing any YAML.** DDL dump,
   `information_schema`, dbt `manifest.json`, ORM entities, SQL mappers — in
   that order of trust. See `references/evidence.md`.
2. **Draft the model** — datasets → fields → relationships → metrics. Shape and
   every enum: `references/spec-reference.md`.
3. **Record evidence in the file header**: what you read, which commit or
   snapshot, and whether each dataset is *verified*, *inferred*, or *proposed*.
4. **Validate**: `make validate FILE=<file>` (or
   `uv run scripts/validate.py <file> --schema schema/osi-schema.json`).
   Iterate until PASS — never report done on a failing model.
5. **Verify against reality** if the repo has a verifier: `make verify`.
6. **Update `docs/overview.md`** — catalogue row, plus any decision that the
   YAML cannot express (why a metric excludes a status, why two tables merged).

## Rules that matter more than the schema

- **Never invent a column, table, or datatype.** Not found in an artefact →
  leave it out and say so. This is the failure mode that destroys trust in a
  semantic layer.
- **`version:` is a `const`** in the schema. Copy the exact string from
  `schema/SOURCE.md`; anything else fails immediately.
- **`additionalProperties: false` everywhere.** An unknown or misspelled key is
  an error, not a warning.
- **Relationships are model-file-local.** They may only reference datasets in
  the same file; cross-file joins get documented in `docs/`.
- **Do not edit `schema/osi-schema.json` or `scripts/validate.py`** — vendored
  upstream. To update, follow `schema/SOURCE.md` and record the new commit.
- **Do not loosen a check to get green.** Fix the model, or add a dated,
  reasoned divergence entry.

## What makes a model worth having

A model that only restates column names is a schema dump with extra steps. The
value is in the parts a tool cannot infer:

- **Metrics encode the business rule** — the exclusion, the deduplication, the
  currency conversion. `SUM(amount)` alone is not a definition.
- **`ai_context.synonyms`** capture what people actually say ("GMV", "sales",
  "top line") so an agent resolves them to one metric.
- **`ai_context.instructions`** name the trap: *"do not sum gross_amount, it
  double-counts discounts"*.
- **`description`** explains when a row exists and what it means — not that
  `order_id` is the order id.

## Reviewing someone else's model

Check in this order — cheapest disqualifier first:

1. Does `make validate` pass?
2. Does every `source` table and every referenced column exist in the evidence?
3. Do two metrics compute the same number under different names?
4. Does each metric's SQL match its prose description?
5. Are `datatype`s consistent with the physical schema (especially `Decimal` vs
   `Float` for money, `DateTimeTz` vs `DateTime`)?
6. Is the verification status in `docs/overview.md` honest?

## References

- `references/spec-reference.md` — full field-by-field shape, enums, and the
  errors each mistake produces.
- `references/evidence.md` — turning DDL dumps, dbt manifests, ORM entities and
  SQL mappers into datasets; grading verified / inferred / proposed.
