"""Reading the restored source database (stage 06.2). Root client of the stand MySQL (snapshot `common.Mysql`), every
session READ ONLY, `sql_log_bin=0`, UTC. Values travel as HEX of utf8mb4 (NULL = 'N'), so no client escaping is
involved; nothing read is ever printed. The census counts non-empty values per column with the audit's own
expression (gen_sql.nonempty_expr) — independent of the Python reader, which must arrive at the same numbers.
"""
import secrets
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "snapshot"))
sys.path.insert(0, str(REPO / "scripts" / "audit"))

import codec  # noqa: E402
import gen_sql  # noqa: E402
from common import Mysql, SnapshotError  # noqa: E402

import spec  # noqa: E402
import transforms as T  # noqa: E402

PROLOGUE = "SET SESSION sql_log_bin=0;\nSET SESSION TRANSACTION READ ONLY;\nSET SESSION time_zone='+00:00';\n"
CHECKBOX = "56"


class SourceDb:
    def __init__(self, dbname, logdir):
        if not codec.NAME_RE.match(dbname):
            raise SnapshotError("bad source database name")
        self.dbname, self.logdir = dbname, logdir
        self._columns = None

    def lines(self, sql):
        return Mysql.stand(database=self.dbname).lines(PROLOGUE + sql, self.logdir / "source.log")

    def columns(self):
        """table → [(column, data_type)] of the restored schema (information_schema; identifiers only)."""
        if self._columns is None:
            out = {}
            for line in self.lines(
                    "SELECT table_name, column_name, data_type FROM information_schema.columns "
                    f"WHERE table_schema = '{self.dbname}' ORDER BY table_name, ordinal_position;\n"):
                table, column, data_type = line.decode("ascii").split("\t")
                if not (codec.NAME_RE.match(table) and codec.NAME_RE.match(column)):
                    raise SnapshotError("unexpected identifier in the source schema")
                out.setdefault(table, []).append((column, data_type.lower()))
            self._columns = out
        return self._columns

    def readable(self, table):
        return [(c, t) for c, t in self.columns()[table] if c not in spec.FORBIDDEN.get(table, ())]

    def select(self, from_sql, tables):
        """Rows of all readable columns of `tables` as {'table.column': str | None}."""
        names, exprs = [], []
        for table in tables:
            for column, _ in self.readable(table):
                names.append(f"{table}.{column}")
                c = f"`{table}`.`{column}`" if from_sql else f"`{column}`"
                exprs.append(f"IF({c} IS NULL, 'N', HEX(CONVERT({c} USING utf8mb4)))")
        sql = f"SELECT {', '.join(exprs)} {from_sql or 'FROM `' + tables[0] + '`'};\n"
        rows = []
        for line in self.lines(sql):
            tokens = line.split(b"\t")
            if len(tokens) != len(names):
                raise SnapshotError("unexpected row shape from the source")
            rows.append({n: (None if t == b"N" else bytes.fromhex(t.decode("ascii")).decode("utf-8"))
                         for n, t in zip(names, tokens)})
        return rows

    def census(self, from_sql, tables, uitypes):
        """{'table.column': (nonempty, meaningful)} over the same live rows; meaningful = numeric non-zero,
        checkbox true, otherwise non-empty (build_maps.meaningful). All columns, read or not."""
        marker = "#vtimp#" + secrets.token_hex(6)
        names, exprs = [], []
        for table in tables:
            for column, data_type in self.columns()[table]:
                c = f"`{table}`.`{column}`" if from_sql else f"`{column}`"
                names.append(f"{table}.{column}")
                exprs.append(gen_sql.nonempty_expr(column, data_type, f"`{table}`" if from_sql else ""))
                if uitypes.get((table, column)) == CHECKBOX:
                    exprs.append(f"SUM(LOWER(TRIM({c})) IN ('1', 'on', 'yes'))")
                elif data_type in gen_sql.NUMERIC_TYPES:
                    exprs.append(f"SUM({c} IS NOT NULL AND {c} <> 0)")
                else:
                    exprs.append(exprs[-1])
        sql = f"SELECT '{marker}', {', '.join(f'COALESCE({e}, 0)' for e in exprs)} " \
              f"{from_sql or 'FROM `' + tables[0] + '`'};\n"
        out = [line for line in self.lines(sql) if line.startswith(marker.encode())]
        if len(out) != 1:
            raise SnapshotError("census query failed")
        values = [int(v) for v in out[0].decode("ascii").split("\t")[1:]]
        return {n: (values[2 * i], values[2 * i + 1]) for i, n in enumerate(names)}


def load(db, uitypes):
    """Everything the plan needs, plus the census of every column of every table read (counts only) and the reader's
    own counts of the same columns (transport check)."""
    data, census, reader = {}, {}, {}

    def read(module, from_sql, tables, census_module=None):
        rows = db.select(from_sql, tables)
        target = census_module or module
        census.setdefault(target, {}).update(db.census(from_sql, tables, uitypes.get(target, {})))
        for k, v in reader_counts(rows).items():
            reader.setdefault(target, {})[k] = reader.get(target, {}).get(k, 0) + v
        return rows

    for module, src in spec.SOURCES.items():
        data[module] = read(module, src.from_sql(), src.tables())
    data["lines"] = []
    for module in spec.LINE_MODULES:  # lines of the live documents: census under their module (field-map rows)
        data["lines"] += read(module, LINES.format(module=module), ("vtiger_inventoryproductrel",))
    for module, tables in spec.PLAIN_MODULES.items():
        for table in tables:
            data[table] = read(module, PLAIN_ROWS[table], (table,))
    for table in spec.TABLES:
        data[table] = db.select(LINK_ROWS.get(table, ""), (table,))
    census["Users"] = db.census(LINK_ROWS["vtiger_users"], ("vtiger_users",), uitypes.get("Users", {}))
    census["Users"].update(db.census(LINK_ROWS["vtiger_user2role"], ("vtiger_user2role",), {}))
    reader["Users"] = {**reader_counts(data["vtiger_users"]), **reader_counts(data["vtiger_user2role"])}
    data["link_census"] = link_census(db)
    data["orphans"] = orphans(db)
    census["links"] = {}
    for table in spec.LINK_COLUMNS:
        census["links"].update(db.census(LINK_ROWS[table], (table,), {}))
    reader["links"] = {k: v for t in spec.LINK_COLUMNS for k, v in reader_counts(data[t]).items()}
    data["crm"] = {crmid: (setype, deleted) for crmid, setype, deleted in _crm(db)}
    data["activity_type"] = _activity_types(db)
    data["modentity_num"] = [{k.split(".", 1)[1]: v for k, v in r.items()}
                             for r in db.select(COUNTERS, ("vtiger_modentity_num",))]
    data["excluded_files"] = _counts(db, EXCLUDED_FILES)
    data["census_deleted"] = deleted_census(db, uitypes)
    data["reader"] = reader
    return data, census


def deleted_census(db, uitypes):
    """Non-empty values of the rows of records deleted in Vtiger, per module (stage 06.4, counts only): the same tables
    and predicates as the live census with `deleted = 1` (D-07: not imported). The whole-snapshot ledger shows them as a
    part of their columns of their own."""
    out = {}
    for module, src in spec.SOURCES.items():
        out.setdefault(module, {}).update(db.census(src.from_sql(deleted=True), src.tables(), uitypes.get(module, {})))
    for module in spec.LINE_MODULES:
        for k, v in db.census(LINES_DELETED.format(module=module), ("vtiger_inventoryproductrel",), {}).items():
            a, b = out.setdefault(module, {}).get(k, (0, 0))
            out[module][k] = (a + v[0], b + v[1])
    out["Users"] = db.census("FROM vtiger_users WHERE deleted = 1", ("vtiger_users",), uitypes.get("Users", {}))
    out["Attachments"] = db.census(DELETED_ATTACHMENTS, ("vtiger_attachments",), {})
    return out


def column_counts(db):
    """table → {column: [nonempty, nonzero]} of a source database by the snapshot's own expressions (codec.stat_sql),
    for a synthetic source without a snapshot (the stage tests)."""
    out = {}
    for table, columns in db.columns().items():
        exprs = []
        for column, data_type in columns:
            exprs.append(f"COALESCE({gen_sql.nonempty_expr(column, data_type, '')}, 0)")
            exprs.append(f"COALESCE(SUM(`{column}` IS NOT NULL AND `{column}` <> 0), 0)"
                         if data_type in gen_sql.NUMERIC_TYPES else "NULL")
        line = db.lines(f"SELECT {', '.join(exprs)} FROM `{table}`;\n")[0].decode("ascii").split("\t")
        out[table] = {c: [int(line[2 * i]), None if line[2 * i + 1] == "NULL" else int(line[2 * i + 1])]
                      for i, (c, _) in enumerate(columns)}
    return out


# Rows of the plain tables that belong to the scope (D-07: deleted source records are not imported). The same
# predicates count the rows independently of the planner (`link_census`): every row must get exactly one outcome.
LIVE = "SELECT crmid FROM vtiger_crmentity WHERE deleted = 0"
LIVE_ACTIVITY = (f"SELECT activityid FROM vtiger_activity WHERE activitytype IN ('Task', 'Call', 'Meeting', 'Письмо') "
                 f"AND activityid IN ({LIVE} AND setype = 'Calendar')")
# activities and archived e-mails (stage 06.3: the e-mails' parents, recipients, users)
LIVE_ACTIVITY_OR_EMAIL = f"{LIVE_ACTIVITY} UNION SELECT crmid FROM vtiger_crmentity WHERE deleted = 0 AND setype = 'Emails'"
LIVE_USER = "SELECT id FROM vtiger_users WHERE deleted = 0"
SCOPE_MODULES = "', '".join(spec.SCOPE)
# setypes of the attachments in scope (MailManager cache: excluded, Q-13)
ATTACHMENT_SETYPES = "', '".join(("Documents Attachment", "Contacts Image", "ModComments Attachment",
                                  "Emails Attachment", "Users Image"))
LIVE_ATTACHMENT = f"{LIVE} AND setype IN ('{ATTACHMENT_SETYPES}')"
DELETED_ATTACHMENTS = ("FROM vtiger_attachments WHERE attachmentsid IN (SELECT crmid FROM vtiger_crmentity WHERE "
                       f"deleted = 1 AND setype IN ('{ATTACHMENT_SETYPES}'))")
LINES = ("FROM vtiger_inventoryproductrel WHERE id IN "
         f"({LIVE} AND setype = '{{module}}')")
LINES_DELETED = ("FROM vtiger_inventoryproductrel WHERE id IN "
                 "(SELECT crmid FROM vtiger_crmentity WHERE deleted = 1 AND setype = '{module}')")
PLAIN_ROWS = {
    # a live attachment of a live owner (stage 06.4: Vtiger keeps the attachments of a deleted record live — they are
    # not imported, the whole-snapshot ledger counts them outside the scope)
    "vtiger_attachments": f"FROM vtiger_attachments WHERE attachmentsid IN ({LIVE_ATTACHMENT}) AND (attachmentsid IN "
                          f"(SELECT attachmentsid FROM vtiger_seattachmentsrel WHERE crmid IN ({LIVE})) OR attachmentsid "
                          f"IN (SELECT attachmentsid FROM vtiger_salesmanattachmentsrel WHERE smid IN ({LIVE_USER})))",
    "vtiger_organizationdetails": "FROM vtiger_organizationdetails",
    "vtiger_attachmentsfolder": "FROM vtiger_attachmentsfolder",
}
COUNTERS = ("FROM vtiger_modentity_num WHERE semodule IN ('Quotes', 'SalesOrder', 'Invoice', 'Act', 'SPPayments') "
            "ORDER BY num_id")
# files the import leaves in the snapshot (decisions): counted for the report
EXCLUDED_FILES = {
    "mailmanager_attachments": f"SELECT COUNT(*) FROM vtiger_attachments WHERE attachmentsid IN ({LIVE} "
                               "AND setype = 'MailManager Attachment')",
}
LINK_ROWS = {
    "vtiger_users": "FROM vtiger_users WHERE deleted = 0",
    "vtiger_user2role": f"FROM vtiger_user2role WHERE userid IN ({LIVE_USER})",
    "vtiger_users2group": f"FROM vtiger_users2group WHERE userid IN ({LIVE_USER})",
    "vtiger_seactivityrel": f"FROM vtiger_seactivityrel WHERE activityid IN ({LIVE_ACTIVITY_OR_EMAIL})",
    "vtiger_cntactivityrel": f"FROM vtiger_cntactivityrel WHERE activityid IN ({LIVE_ACTIVITY_OR_EMAIL})",
    "vtiger_salesmanactivityrel": f"FROM vtiger_salesmanactivityrel WHERE activityid IN ({LIVE_ACTIVITY_OR_EMAIL})",
    "vtiger_contpotentialrel": f"FROM vtiger_contpotentialrel WHERE potentialid IN ({LIVE} AND setype = 'Potentials')",
    "vtiger_crmentityrel": f"FROM vtiger_crmentityrel WHERE crmid IN ({LIVE}) AND relcrmid IN ({LIVE}) "
                           f"AND (module IN ('{SCOPE_MODULES}') OR relmodule IN ('{SCOPE_MODULES}', 'Calendar'))",
    "vtiger_freetagged_objects": f"FROM vtiger_freetagged_objects WHERE module IN ('HelpDesk', 'ProjectTask', 'Faq') "
                                 f"AND object_id IN ({LIVE})",
    "vtiger_groups": "FROM vtiger_groups",
    "vtiger_senotesrel": f"FROM vtiger_senotesrel WHERE notesid IN ({LIVE} AND setype = 'Documents') "
                         f"AND crmid IN ({LIVE})",
    "vtiger_seattachmentsrel": f"FROM vtiger_seattachmentsrel WHERE attachmentsid IN ({LIVE_ATTACHMENT}) "
                               f"AND crmid IN ({LIVE})",
    "vtiger_salesmanattachmentsrel": f"FROM vtiger_salesmanattachmentsrel WHERE attachmentsid IN ({LIVE_ATTACHMENT}) "
                                     f"AND smid IN ({LIVE_USER})",
    "vtiger_email_track": f"FROM vtiger_email_track WHERE mailid IN ({LIVE} AND setype = 'Emails')",
}


LINK_ROWS["vtiger_freetags"] = (f"FROM vtiger_freetags WHERE id IN "
                               f"(SELECT tag_id {LINK_ROWS['vtiger_freetagged_objects']})")
PAIR_TABLES = [t for t in LINK_ROWS if t not in ("vtiger_users", "vtiger_groups", "vtiger_freetags")]


def _counts(db, queries):
    return {name: int(db.lines(sql + ";\n")[0]) for name, sql in queries.items()}


def link_census(db):
    """table → rows in scope, counted by SQL (the planner must give each of them one outcome)."""
    return {table: int(db.lines(f"SELECT COUNT(*) {LINK_ROWS[table]};\n")[0]) for table in PAIR_TABLES}


def orphans(db):
    """Live source records of each module without a row in its base table: an INNER JOIN would drop them silently."""
    out = {}
    for module, src in spec.SOURCES.items():
        table, key = src.base
        sql = (f"SELECT COUNT(*) FROM vtiger_crmentity LEFT JOIN `{table}` ON `{table}`.`{key}` = vtiger_crmentity.crmid "
               f"WHERE vtiger_crmentity.deleted = 0 AND vtiger_crmentity.setype = '{src.setype or module}' "
               f"AND `{table}`.`{key}` IS NULL;\n")
        out[src.setype or module] = int(db.lines(sql)[0])
    return out


def _crm(db):
    """(crmid, setype, deleted) of every source record: classifies references (live, deleted, missing, module)."""
    out = []
    for line in db.lines("SELECT crmid, HEX(setype), deleted FROM vtiger_crmentity;\n"):
        crmid, setype, deleted = line.decode("ascii").split("\t")
        out.append((int(crmid), bytes.fromhex(setype).decode("utf-8"), deleted != "0"))
    return out


def _activity_types(db):
    out = {}
    for line in db.lines("SELECT activityid, HEX(activitytype) FROM vtiger_activity;\n"):
        activity, atype = line.decode("ascii").split("\t")
        out[int(activity)] = bytes.fromhex(atype).decode("utf-8") if atype != "NULL" else None
    return out


def reader_counts(rows, keys=None):
    """Non-empty values per column among the rows read — must equal the SQL census (transport check)."""
    counts = {}
    for row in rows:
        for name, value in row.items():
            if keys is not None and name not in keys:
                continue
            counts[name] = counts.get(name, 0) + (0 if T.is_empty(value) else 1)
    return counts
