#!/usr/bin/env python3
#
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0.3",
#     "sqlglot>=30.12.0",
# ]
# ///
#
# Licensed under the Apache License, Version 2.0.

"""
Verify Ossie semantic models against a real DDL dump.

`validate.py` answers "is this valid Ossie?". This answers "is it TRUE?" —
does every table exist, does every column referenced by a field expression
exist, do the declared datatypes and primary keys match the physical schema.

Usage:
    uv run scripts/verify_ddl.py models/**/*.yaml --ddl .evidence/chinook_pg.sql
    uv run scripts/verify_ddl.py <model> --ddl <dump.sql> --accept scripts/divergences.yaml

Exits non-zero if any model diverges from the DDL.
"""

import re
import sys
from pathlib import Path

import yaml
import sqlglot
from sqlglot import exp

# Physical type -> Ossie datatype. Matched on the leading word of the column type.
TYPE_MAP = {
    "INT": "Integer", "INTEGER": "Integer", "BIGINT": "Integer",
    "SMALLINT": "Integer", "SERIAL": "Integer", "BIGSERIAL": "Integer",
    "NUMERIC": "Decimal", "DECIMAL": "Decimal", "MONEY": "Decimal",
    "REAL": "Float", "FLOAT": "Float", "DOUBLE": "Float",
    "VARCHAR": "String", "CHAR": "String", "TEXT": "String",
    "NVARCHAR": "String", "CHARACTER": "String", "UUID": "String",
    "BOOL": "Boolean", "BOOLEAN": "Boolean",
    "DATE": "Date",
    "TIME": "Time",
    "TIMESTAMP": "DateTime", "DATETIME": "DateTime",
    "TIMESTAMPTZ": "DateTimeTz",
    "JSON": "Opaque", "JSONB": "Opaque", "BYTEA": "Opaque", "BLOB": "Opaque",
}

CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?.*?\)\s*;", re.IGNORECASE | re.DOTALL
)


def parse_ddl(path: Path, dialect: str) -> dict:
    """Return {table_name: {"columns": {name: type_str}, "pk": [cols]}}."""
    text = path.read_text(errors="replace")
    tables = {}
    for block in CREATE_TABLE_RE.findall(text):
        try:
            statement = sqlglot.parse_one(block, dialect=dialect)
        except Exception:
            continue
        if not isinstance(statement, exp.Create):
            continue
        table = statement.find(exp.Table)
        if table is None:
            continue
        name = table.name.lower()

        columns, pk = {}, []
        for coldef in statement.find_all(exp.ColumnDef):
            columns[coldef.name.lower()] = (coldef.args.get("kind").sql(dialect=dialect)
                                            if coldef.args.get("kind") else "")
            for constraint in coldef.constraints:
                if isinstance(constraint.kind, exp.PrimaryKeyColumnConstraint):
                    pk.append(coldef.name.lower())

        for key in statement.find_all(exp.PrimaryKey):
            for column in key.expressions:
                col_name = column.name.lower()
                if col_name and col_name not in pk:
                    pk.append(col_name)

        tables[name] = {"columns": columns, "pk": pk}
    return tables


def physical_to_ossie(type_str: str) -> str | None:
    if not type_str:
        return None
    head = re.split(r"[\s(]", type_str.strip().upper(), maxsplit=1)[0]
    if head == "TIMESTAMP" and "TIME ZONE" in type_str.upper():
        return "DateTimeTz"
    return TYPE_MAP.get(head)


def columns_in(expression: str) -> list[str]:
    """Column identifiers referenced by a field expression."""
    try:
        tree = sqlglot.parse_one(expression)
    except Exception:
        try:
            tree = sqlglot.parse_one(f"SELECT {expression}")
        except Exception:
            return []
    if isinstance(tree, exp.Column):
        return [tree.name.lower()]
    found = [c.name.lower() for c in tree.find_all(exp.Column) if c.name]
    if not found and isinstance(tree, exp.Identifier):
        return [tree.name.lower()]
    return found


def bare_column(expression: str) -> str | None:
    """The column name when the expression is exactly one unqualified column."""
    cols = columns_in(expression)
    if len(cols) == 1 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression.strip()):
        return cols[0]
    return None


def ansi_expression(node: dict) -> str | None:
    for dialect_expr in (node.get("expression") or {}).get("dialects", []):
        if dialect_expr.get("dialect") == "ANSI_SQL":
            return dialect_expr.get("expression")
    return None


def load_accepted(path: Path | None) -> set:
    """Accepted divergences: list of {dataset, field?, reason}."""
    if not path:
        return set()
    entries = yaml.safe_load(path.read_text()) or []
    accepted = set()
    for entry in entries:
        if not entry.get("reason"):
            print(f"  [accept] entry for {entry.get('dataset')} has no reason — ignored")
            continue
        accepted.add((entry.get("dataset"), entry.get("field")))
    return accepted


def verify_model(model_path: Path, tables: dict, accepted: set) -> list[str]:
    data = yaml.safe_load(model_path.read_text())
    problems = []

    for model in data.get("semantic_model", []):
        for dataset in model.get("datasets", []):
            ds_name = dataset.get("name", "<unnamed>")
            source = (dataset.get("source") or "").strip('"')
            table_name = source.split(".")[-1].lower()

            if (ds_name, None) in accepted:
                continue

            table = tables.get(table_name)
            if table is None:
                problems.append(f"[table] {ds_name}: '{source}' not found in DDL")
                continue

            declared_pk = [c.lower() for c in dataset.get("primary_key", [])]
            if declared_pk and set(declared_pk) != set(table["pk"]):
                problems.append(
                    f"[pk] {ds_name}: model says {declared_pk}, DDL says {table['pk']}"
                )

            for field in dataset.get("fields", []):
                f_name = field.get("name", "<unnamed>")
                if (ds_name, f_name) in accepted:
                    continue
                expression = ansi_expression(field)
                if not expression:
                    problems.append(f"[expr] {ds_name}.{f_name}: no ANSI_SQL expression")
                    continue

                referenced = columns_in(expression)
                if not referenced:
                    problems.append(
                        f"[expr] {ds_name}.{f_name}: could not read any column out of "
                        f"'{expression}'"
                    )
                for column in referenced:
                    if column not in table["columns"]:
                        problems.append(
                            f"[column] {ds_name}.{f_name}: '{column}' not in "
                            f"{table_name} ({expression})"
                        )

                declared = field.get("datatype")
                single = bare_column(expression)
                if declared and single and single in table["columns"]:
                    physical = physical_to_ossie(table["columns"][single])
                    if physical and physical != declared:
                        problems.append(
                            f"[datatype] {ds_name}.{f_name}: model says {declared}, "
                            f"{table_name}.{single} is {table['columns'][single]} "
                            f"→ {physical}"
                        )
    return problems


def main():
    args = sys.argv[1:]
    models, ddl_path, accept_path, dialect = [], None, None, "postgres"

    i = 0
    while i < len(args):
        if args[i] == "--ddl":
            ddl_path = Path(args[i + 1]); i += 2
        elif args[i] == "--accept":
            accept_path = Path(args[i + 1]); i += 2
        elif args[i] == "--dialect":
            dialect = args[i + 1]; i += 2
        elif args[i].startswith("-"):
            print(f"unknown option: {args[i]}"); sys.exit(2)
        else:
            models.append(Path(args[i])); i += 1

    if not models or ddl_path is None:
        print(__doc__)
        sys.exit(2)
    if not ddl_path.exists():
        print(f"Error: DDL not found: {ddl_path}\nRun `make evidence` first.")
        sys.exit(2)

    tables = parse_ddl(ddl_path, dialect)
    if not tables:
        print(f"Error: no CREATE TABLE statements parsed out of {ddl_path}")
        sys.exit(2)
    print(f"DDL: {ddl_path} — {len(tables)} tables")

    total = 0
    for model_path in models:
        if not model_path.exists():
            print(f"FAIL {model_path}: file not found")
            total += 1
            continue
        problems = verify_model(model_path, tables, load_accepted(accept_path))
        if problems:
            total += len(problems)
            print(f"FAIL {model_path} — {len(problems)} divergence(s):")
            for p in problems:
                print(f"  {p}")
        else:
            print(f"PASS {model_path.name} — matches the DDL")

    if total:
        print(f"\nVerification FAILED with {total} divergence(s).")
        sys.exit(1)
    print(f"\nVerification PASSED for {len(models)} model(s).")


if __name__ == "__main__":
    main()
