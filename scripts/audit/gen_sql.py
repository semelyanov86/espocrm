#!/usr/bin/env python3
"""Generate read-only audit SQL from previously captured schema metadata.

Usage:
  gen_sql.py table-counts  OUTDIR  > counts.sql
  gen_sql.py column-counts OUTDIR  > column_counts.sql
  gen_sql.py field-live-counts OUTDIR > field_live_counts.sql
  gen_sql.py reference-targets OUTDIR > reference_targets.sql
  gen_sql.py picklist-values OUTDIR > picklist_values.sql
  gen_sql.py table-live-counts OUTDIR > table_live_counts.sql

The generated SQL returns only counts, never row values.
"""
import csv
import sys
from pathlib import Path

STRING_TYPES = {"char", "varchar", "text", "tinytext", "mediumtext", "longtext", "enum", "set"}
BLOB_TYPES = {"blob", "tinyblob", "mediumblob", "longblob", "binary", "varbinary"}
NUMERIC_TYPES = {"int", "tinyint", "smallint", "mediumint", "bigint", "decimal", "float", "double", "bit"}
DATE_TYPES = {"date", "datetime", "timestamp", "time", "year"}


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


def q(ident):
    return "`" + ident.replace("`", "``") + "`"


def nonempty_expr(col, data_type, alias=""):
    c = (alias + "." if alias else "") + q(col)
    if data_type in STRING_TYPES:
        return f"SUM({c} IS NOT NULL AND TRIM({c})<>'')"
    if data_type in BLOB_TYPES:
        return f"SUM({c} IS NOT NULL AND LENGTH({c})>0)"
    if data_type in DATE_TYPES:
        return f"SUM({c} IS NOT NULL AND CAST({c} AS CHAR) NOT LIKE '0000-00-00%')"
    return f"SUM({c} IS NOT NULL)"


def nonzero_expr(col, data_type):
    if data_type in NUMERIC_TYPES:
        return f"SUM({q(col)} IS NOT NULL AND {q(col)}<>0)"
    return "NULL"


def table_counts(outdir):
    tables = read_tsv(outdir / "04_tables.tsv")
    parts = [f"SELECT '{t['TABLE_NAME']}' tbl, COUNT(*) n FROM {q(t['TABLE_NAME'])}" for t in tables]
    print("\nUNION ALL\n".join(parts) + ";")


def column_counts(outdir):
    counts = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}
    cols = {}
    for r in read_tsv(outdir / "03_columns.tsv"):
        cols.setdefault(r["TABLE_NAME"], []).append(r)
    for tbl in sorted(cols):
        if counts.get(tbl, 0) == 0:
            continue
        # One scan per table; one output row per column via JSON to keep it compact.
        pairs = []
        for c in cols[tbl]:
            pairs.append(f"'{c['COLUMN_NAME']}', JSON_ARRAY({nonempty_expr(c['COLUMN_NAME'], c['DATA_TYPE'])}, "
                         f"{nonzero_expr(c['COLUMN_NAME'], c['DATA_TYPE'])})")
        print(f"SELECT '{tbl}' tbl, COUNT(*) n, JSON_OBJECT({', '.join(pairs)}) cols FROM {q(tbl)};")


# Column that links a module table row to vtiger_crmentity.crmid, when it is not the PK.
LINK_KEY_OVERRIDES = {
    "vtiger_crmentity": "crmid",
    "vtiger_crmentity_user_field": "recordid",
    "vtiger_modcomments": "modcommentsid",
    "vtiger_servicecontracts": "servicecontractsid",
    "vtiger_inventoryproductrel": "id",
    "vtiger_activity_reminder": "activity_id",
    "vtiger_seactivityrel": "activityid",
    "vtiger_cntactivityrel": "activityid",
    "vtiger_invoice_recurring_info": "salesorderid",
    "vtiger_email_track": "mailid",
    "vtiger_sp_socialconnector": "socialconnectorid",
}
# Extra predicate on vtiger_activity for modules sharing it.
ACTIVITY_FILTER = {
    "Calendar": "a.activitytype='Task'",
    "Events": "a.activitytype NOT IN ('Task','Emails')",
    "Emails": "a.activitytype='Emails'",
}
SETYPE = {"Events": "Calendar"}
# Tables whose rows belong to a different setype than the module declaring the field.
SETYPE_BY_TABLE = {("Emails", "vtiger_attachments"): "Emails Attachment"}


def setype_for(module, tbl):
    return SETYPE_BY_TABLE.get((module, tbl), SETYPE.get(module, module))


def activity_filtered(module, tbl):
    """Calendar/Events/Emails rows live in vtiger_activity, except tables mapped to another setype."""
    return module in ACTIVITY_FILTER and (module, tbl) not in SETYPE_BY_TABLE


def field_live_counts(outdir):
    """Per module field: non-empty values among live (deleted=0) records of that module."""
    fields = read_tsv(outdir / "02_fields.tsv")
    pks = {r["TABLE_NAME"]: r["pk"].split(",")[0] for r in read_tsv(outdir / "05_primary_keys.tsv")}
    types = {(r["TABLE_NAME"], r["COLUMN_NAME"]): r["DATA_TYPE"] for r in read_tsv(outdir / "03_columns.tsv")}
    counts = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}
    groups = {}
    for f in fields:
        if f["module"] == "Users":
            continue
        groups.setdefault((f["module"], f["tablename"]), []).append(f["columnname"])
    for (module, tbl), columns in sorted(groups.items()):
        if counts.get(tbl, 0) == 0:
            continue
        key = LINK_KEY_OVERRIDES.get(tbl, pks.get(tbl))
        if not key:
            continue
        exprs = []
        for col in dict.fromkeys(columns):
            dt = types.get((tbl, col))
            if dt is None:
                exprs.append(f"'{col}', 'MISSING_COLUMN'")
                continue
            nz = f"SUM(t.{q(col)} IS NOT NULL AND t.{q(col)}<>0)" if dt in NUMERIC_TYPES else "NULL"
            exprs.append(f"'{col}', JSON_ARRAY({nonempty_expr(col, dt, 't')}, {nz})")
        where = [f"c.setype='{setype_for(module, tbl)}'", "c.deleted=0"]
        join_activity = ""
        if activity_filtered(module, tbl):
            join_activity = "JOIN vtiger_activity a ON a.activityid=c.crmid"
            where.append(ACTIVITY_FILTER[module])
        print(f"SELECT '{module}' module, '{tbl}' tbl, COUNT(*) n, JSON_OBJECT({', '.join(exprs)}) cols "
              f"FROM {q(tbl)} t JOIN vtiger_crmentity c ON c.crmid=t.{q(key)} {join_activity} "
              f"WHERE {' AND '.join(where)};")


REFERENCE_UITYPES = {"10", "51", "57", "58", "59", "66", "68", "73", "75", "76", "78", "80", "81"}
OWNER_UITYPES = {"52", "53", "77", "101"}


def reference_targets(outdir):
    """Per reference field: count of values by target module (setype) and dangling refs."""
    fields = read_tsv(outdir / "02_fields.tsv")
    pks = {r["TABLE_NAME"]: r["pk"].split(",")[0] for r in read_tsv(outdir / "05_primary_keys.tsv")}
    counts = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}
    for f in fields:
        tbl, col, module = f["tablename"], f["columnname"], f["module"]
        if counts.get(tbl, 0) == 0 or module == "Users":
            continue
        key = LINK_KEY_OVERRIDES.get(tbl, pks.get(tbl))
        if not key:
            continue
        # Calendar and Events share vtiger_activity/vtiger_crmentity(setype='Calendar'): split by activitytype.
        act_join = act_where = ""
        if activity_filtered(module, tbl):
            act_join = " JOIN vtiger_activity a ON a.activityid=c.crmid"
            act_where = " WHERE " + ACTIVITY_FILTER[module]
        if f["uitype"] in REFERENCE_UITYPES:
            print(f"SELECT '{module}' module, '{tbl}' tbl, '{col}' col, '{f['uitype']}' uitype, "
                  f"IFNULL(r.setype, IF(t.{q(col)} IS NULL OR t.{q(col)} IN ('', '0'), '(empty)', '(dangling)')) target, "
                  f"IFNULL(r.deleted, '') target_deleted, COUNT(*) n "
                  f"FROM {q(tbl)} t JOIN vtiger_crmentity c ON c.crmid=t.{q(key)} AND c.deleted=0 AND c.setype='{setype_for(module, tbl)}'{act_join} "
                  f"LEFT JOIN vtiger_crmentity r ON r.crmid=t.{q(col)}{act_where} "
                  f"GROUP BY 5, 6;")
        elif f["uitype"] in OWNER_UITYPES:
            print(f"SELECT '{module}' module, '{tbl}' tbl, '{col}' col, '{f['uitype']}' uitype, "
                  f"CASE WHEN u.id IS NOT NULL THEN CONCAT('user:', u.status) WHEN g.groupid IS NOT NULL THEN 'group' "
                  f"WHEN t.{q(col)} IS NULL OR t.{q(col)} IN ('', '0') THEN '(empty)' ELSE '(dangling)' END target, '' target_deleted, COUNT(*) n "
                  f"FROM {q(tbl)} t JOIN vtiger_crmentity c ON c.crmid=t.{q(key)} AND c.deleted=0 AND c.setype='{setype_for(module, tbl)}'{act_join} "
                  f"LEFT JOIN vtiger_users u ON u.id=t.{q(col)} LEFT JOIN vtiger_groups g ON g.groupid=t.{q(col)}{act_where} "
                  f"GROUP BY 5;")


PICKLIST_UITYPES = {"15", "16", "33", "56", "26", "27", "115", "117"}


def picklist_values(outdir):
    """Distribution of controlled-vocabulary values (picklists, checkboxes) in live records."""
    fields = read_tsv(outdir / "02_fields.tsv")
    pks = {r["TABLE_NAME"]: r["pk"].split(",")[0] for r in read_tsv(outdir / "05_primary_keys.tsv")}
    counts = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}
    for f in fields:
        tbl, col, module = f["tablename"], f["columnname"], f["module"]
        if f["uitype"] not in PICKLIST_UITYPES or counts.get(tbl, 0) == 0:
            continue
        if module == "Users":
            print(f"SELECT '{module}' module, '{f['fieldname']}' field, '{f['uitype']}' uitype, "
                  f"IFNULL(CAST(t.{q(col)} AS CHAR), '(null)') value, COUNT(*) n FROM {q(tbl)} t GROUP BY 4;")
            continue
        key = LINK_KEY_OVERRIDES.get(tbl, pks.get(tbl))
        if not key:
            continue
        extra = ""
        join_activity = ""
        if activity_filtered(module, tbl):
            join_activity = "JOIN vtiger_activity a ON a.activityid=c.crmid"
            extra = " AND " + ACTIVITY_FILTER[module]
        print(f"SELECT '{module}' module, '{f['fieldname']}' field, '{f['uitype']}' uitype, "
              f"IFNULL(CAST(t.{q(col)} AS CHAR), '(null)') value, COUNT(*) n "
              f"FROM {q(tbl)} t JOIN vtiger_crmentity c ON c.crmid=t.{q(key)} {join_activity} "
              f"WHERE c.deleted=0 AND c.setype='{setype_for(module, tbl)}'{extra} GROUP BY 4;")


def table_live_counts(outdir):
    """For every non-empty module table (referenced by vtiger_field) that links to vtiger_crmentity:
    rows belonging to live records (deleted=0, any setype) and non-empty/non-zero counts per column.
    Used for physical columns without a vtiger_field entry."""
    fields = read_tsv(outdir / "02_fields.tsv")
    pks = {r["TABLE_NAME"]: r["pk"].split(",")[0] for r in read_tsv(outdir / "05_primary_keys.tsv")}
    counts = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}
    cols = {}
    for r in read_tsv(outdir / "03_columns.tsv"):
        cols.setdefault(r["TABLE_NAME"], []).append(r)
    for tbl in sorted({f["tablename"] for f in fields if f["module"] != "Users"}):
        key = LINK_KEY_OVERRIDES.get(tbl, pks.get(tbl))
        if counts.get(tbl, 0) == 0 or not key:
            continue
        pairs = []
        for c in cols[tbl]:
            nz = f"SUM(t.{q(c['COLUMN_NAME'])} IS NOT NULL AND t.{q(c['COLUMN_NAME'])}<>0)" if c["DATA_TYPE"] in NUMERIC_TYPES else "NULL"
            pairs.append(f"'{c['COLUMN_NAME']}', JSON_ARRAY({nonempty_expr(c['COLUMN_NAME'], c['DATA_TYPE'], 't')}, {nz})")
        print(f"SELECT '{tbl}' tbl, COUNT(*) n, JSON_OBJECT({', '.join(pairs)}) cols FROM {q(tbl)} t "
              f"JOIN vtiger_crmentity c ON c.crmid=t.{q(key)} AND c.deleted=0;")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cmd, outdir = sys.argv[1], Path(sys.argv[2])
    {"table-counts": table_counts, "column-counts": column_counts,
     "field-live-counts": field_live_counts, "reference-targets": reference_targets,
     "picklist-values": picklist_values, "table-live-counts": table_live_counts}[cmd](outdir)


if __name__ == "__main__":
    main()
