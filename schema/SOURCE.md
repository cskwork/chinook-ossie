# Vendored upstream files

Two files in this repository are copies of [Apache Ossie (incubating)][ossie]
sources, vendored so that validation works standalone:

| Local path            | Upstream path                 |
| --------------------- | ----------------------------- |
| `schema/osi-schema.json` | `core-spec/osi-schema.json` |
| `scripts/validate.py`    | `validation/validate.py`    |

- Origin: local clone: /Users/<user>/Documents/Git/AIDT/ossie
- Ref: `main`
- Commit: `07d1db73f506f92b1ba7baaafa1cc66e642a4485`
- Vendored on: 2026-07-26
- Licence: Apache License 2.0 (see `LICENSE`, `NOTICE`)

The spec version pinned by this schema is **`0.2.0.dev0`** — the schema
declares `version` as a `const`, so every model in `models/` must carry exactly
that string. Bumping the schema means bumping every model.

## Updating

```bash
# from a local apache/ossie clone
cp ../ossie/core-spec/osi-schema.json schema/osi-schema.json
cp ../ossie/validation/validate.py    scripts/validate.py

# or straight from GitHub (pin a ref you can name in the commit message)
REF=main
curl -fsSL "https://raw.githubusercontent.com/apache/ossie/$REF/core-spec/osi-schema.json" -o schema/osi-schema.json
curl -fsSL "https://raw.githubusercontent.com/apache/ossie/$REF/validation/validate.py"    -o scripts/validate.py
```

Then, in the same commit:

1. Update the ref/commit/date above.
2. Re-run `make validate` — a spec bump usually breaks the `version` const first.
3. Note the upstream commit hash in the commit message.

Ossie is an incubating project; the schema still changes. Pin a tag rather than
`main` once tagged releases exist for your risk appetite.

[ossie]: https://github.com/apache/ossie
