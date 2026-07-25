# Chinook Semantic Models

A **worked example** of an [Apache Ossie (incubating)][ossie] semantic model: the
[Chinook][chinook] sample database — a digital music store — modelled as datasets,
relationships and metrics, and **verified against the real DDL** rather than merely
being valid YAML.

Generated with [ossie-domain-kit](https://github.com/cskwork/ossie-domain-kit).

```bash
make validate   # is it valid Ossie?   → schema, unique names, references, SQL
make verify     # is it TRUE?          → tables, columns, datatypes, primary keys
make check      # both
```

Both pass on a clean checkout. `make verify` fetches the upstream Chinook DDL into
`.evidence/` first — nothing to install beyond [uv](https://docs.astral.sh/uv/).

## What's modelled

| | |
| --- | --- |
| **Sales** | `invoice`, `invoice_line` — the grain of every revenue metric |
| **Customers** | `customer`, `employee` (the support rep who owns each account) |
| **Catalogue** | `track`, `album`, `artist`, `genre` |
| **Metrics** | `net_revenue`, `tracks_sold`, `invoice_count`, `purchasing_customers`, `average_invoice_value`, `revenue_per_customer`, `catalogue_tracks` |

Not modelled: `media_type`, `playlist`, `playlist_track`. They exist in the schema and
answer none of the questions this model is for. A semantic model is a curated interface,
not a mirror of the database.

## The one thing this model exists to prevent

Chinook stores `invoice.total` as a denormalised copy of the sum of its lines. So this
looks right and is wrong:

```sql
SELECT SUM(i.total)
FROM invoice i JOIN invoice_line il ON il.invoice_id = i.invoice_id;   -- inflated
```

Each invoice is counted once per line. The `net_revenue` metric sums at line grain
instead, and the trap is written into the model so an agent reading it is warned before
it writes the query:

```yaml
- name: net_revenue
  ai_context:
    instructions: >-
      Always compute revenue this way. Summing invoice.total instead looks
      equivalent and is not: joining invoice to invoice_line and summing total
      counts each invoice once per line, inflating revenue several-fold.
  expression:
    dialects:
      - dialect: ANSI_SQL
        expression: SUM(invoice_line.unit_price * invoice_line.quantity)
```

That sentence is the part no schema dump contains, and the reason a semantic layer is
worth maintaining at all.

## Verification, concretely

`scripts/verify_ddl.py` parses the Chinook `CREATE TABLE` statements with `sqlglot` and
checks, for every dataset and every field:

1. the table named in `source` exists;
2. every column referenced by a field expression exists in it — expressions are parsed,
   so `unit_price * quantity` is checked as two columns, not as a string;
3. the declared `datatype` matches the physical type, for plain column fields;
4. `primary_key` matches the DDL's primary key.

It is not a rubber stamp. Injecting four faults into a copy of the model produces:

```
FAIL /tmp/bad-model.yaml — 4 divergence(s):
  [column] invoice.billing_country: 'billing_nation' not in invoice (billing_nation)
  [pk] invoice_line: model says ['invoice_id'], DDL says ['invoice_line_id']
  [datatype] invoice_line.unit_price: model says Integer, invoice_line.unit_price is DECIMAL(10, 2) → Decimal
  [table] genre: 'chinook.public.genres' not found in DDL
```

Exit code 1, so CI fails. `--accept scripts/divergences.yaml` exists for divergences you
have consciously decided to live with; each entry needs a written reason or it is ignored.

## Layout

```
models/chinook/chinook_sales_model.yaml   the model
schema/osi-schema.json                    vendored Ossie schema (see schema/SOURCE.md)
scripts/validate.py                       vendored Ossie validator
scripts/verify_ddl.py                     DDL verifier — this repo's own contribution
docs/overview.md                          catalogue, conventions, decisions
.evidence/                                fetched DDL, git-ignored
```

## Licence

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Chinook itself is a
separate project ([lerocha/chinook-database][chinook], MIT); no Chinook data or schema is
redistributed here — `make evidence` fetches it at build time.

[ossie]: https://github.com/apache/ossie
[chinook]: https://github.com/lerocha/chinook-database
