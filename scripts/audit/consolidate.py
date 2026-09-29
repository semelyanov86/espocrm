#!/usr/bin/env python3
"""Merge private audit outputs into one per-column table (still private: it stays in OUTDIR).

Usage: consolidate.py OUTDIR  -> writes OUTDIR/columns.tsv

Columns: module, table, column, fieldname, label, uitype, typeofdata, generatedtype, presence,
displaytype, db_type, table_rows, nonempty_all, nonzero_all, live_rows, nonempty_live, nonzero_live, in_vtiger_field
Only counts and metadata are handled; no row values exist in the inputs.
"""
import csv
import json
import sys
from pathlib import Path


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


def read_json_rows(path, key_fields):
    """Parse mysql --batch output of statements returning (<keys...>, n, cols JSON); headers repeat."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if parts[0] in ("tbl", "module") or len(parts) < len(key_fields) + 2:
                continue
            keys = parts[:len(key_fields)]
            n = int(parts[len(key_fields)])
            cols = json.loads(parts[len(key_fields) + 1])
            rows.append((keys, n, cols))
    return rows


def main():
    outdir = Path(sys.argv[1])
    fields = read_tsv(outdir / "02_fields.tsv")
    columns = read_tsv(outdir / "03_columns.tsv")
    table_rows = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}

    all_counts = {}
    for (tbl,), n, cols in read_json_rows(outdir / "11_column_counts.raw", ["tbl"]):
        for col, (nonempty, nonzero) in cols.items():
            all_counts[(tbl, col)] = (nonempty, nonzero)

    live = {}
    live_rows = {}
    for (module, tbl), n, cols in read_json_rows(outdir / "12_field_live_counts.raw", ["module", "tbl"]):
        live_rows[(module, tbl)] = n
        for col, v in cols.items():
            live[(module, tbl, col)] = v if isinstance(v, list) else [v, None]

    tlive, tlive_rows = {}, {}
    raw = outdir / "15_table_live_counts.raw"
    if raw.exists():
        for (tbl,), n, cols in read_json_rows(raw, ["tbl"]):
            tlive_rows[tbl] = n
            for col, (ne, nz) in cols.items():
                tlive[(tbl, col)] = (ne, nz)

    dtype = {(c["TABLE_NAME"], c["COLUMN_NAME"]): c["COLUMN_TYPE"] for c in columns}
    out = []
    seen = set()
    for f in fields:
        key = (f["tablename"], f["columnname"])
        nonempty, nonzero = all_counts.get(key, (0, None))
        mod = f["module"]
        lr = live_rows.get((mod, f["tablename"]))
        nl, nzl = live.get((mod, f["tablename"], f["columnname"]), [None, None])
        if mod == "Users":
            lr, nl, nzl = table_rows.get(f["tablename"], 0), nonempty, nonzero
        if lr is None:
            lr, nl = 0, 0
        out.append([mod, f["tablename"], f["columnname"], f["fieldname"], f["fieldlabel"], f["uitype"], f["typeofdata"],
                    f["generatedtype"], f["presence"], f["displaytype"], dtype.get(key, "MISSING"),
                    table_rows.get(f["tablename"], 0), nonempty or 0, "" if nonzero is None else nonzero, lr, nl or 0,
                    "" if nzl is None else nzl, "1"])
        seen.add(key)
    # Physical columns of non-empty tables that are not declared as fields.
    for c in columns:
        key = (c["TABLE_NAME"], c["COLUMN_NAME"])
        if key in seen or table_rows.get(c["TABLE_NAME"], 0) == 0:
            continue
        nonempty, nonzero = all_counts.get(key, (0, None))
        # Live counts exist only for module tables linked to vtiger_crmentity; service tables have none.
        lr = tlive_rows.get(c["TABLE_NAME"], "")
        lne, lnz = tlive.get(key, ("", None))
        out.append(["", c["TABLE_NAME"], c["COLUMN_NAME"], "", "", "", "", "", "", "", c["COLUMN_TYPE"],
                    table_rows[c["TABLE_NAME"]], nonempty or 0, "" if nonzero is None else nonzero,
                    lr, "" if lne is None else lne, "" if lnz is None else lnz, "0"])
    header = ["module", "table", "column", "fieldname", "label", "uitype", "typeofdata", "generatedtype", "presence",
              "displaytype", "db_type", "table_rows", "nonempty_all", "nonzero_all", "live_rows", "nonempty_live", "nonzero_live", "in_vtiger_field"]
    with open(outdir / "columns.tsv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(out)
    print(f"columns.tsv: {len(out)} rows ({len(seen)} declared fields)")


if __name__ == "__main__":
    main()
