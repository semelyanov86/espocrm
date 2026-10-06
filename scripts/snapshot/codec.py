"""Row codec and SQL shapes of snapshot format v1 (docs/migration/snapshot.md, «Формат»).

A row is one line of TAB-separated tokens in column order; a token is `N` for SQL NULL or the
uppercase hex of the value: raw stored bytes for strings (in the column charset) and binary
columns, the MySQL text form (CAST AS CHAR) for numbers and dates. TIMESTAMP is read and written
with session time_zone '+00:00'. The same SQL computes, inside the export transaction and later on
the restored copy, COUNT(*), an order-independent digest of the encoded lines and the audit's
non-empty/non-zero counts per column.
"""
import hashlib
import re
import sys

from common import NAME_RE, SnapshotError, REPO

sys.path.insert(0, str(REPO / "scripts" / "audit"))
from gen_sql import NUMERIC_TYPES, nonempty_expr  # noqa: E402  (same «non-empty» as field-map.csv)

STRING = {"char", "varchar", "tinytext", "text", "mediumtext", "longtext"}
BINARY = {"binary", "varbinary", "tinyblob", "blob", "mediumblob", "longblob"}
EXACT = {"tinyint", "smallint", "mediumint", "int", "bigint", "decimal", "year"}
TEMPORAL = {"date", "datetime", "timestamp", "time"}
CHARSETS = {"latin1", "utf8mb3", "utf8mb4", "ascii"}
ENGINES = {"InnoDB", "MyISAM"}            # MyISAM is outside the read view: checked as a stable window
SEP = "CHAR(9 USING utf8mb4)"

# sql_mode tokens under which the DDL scan and the restore literals mean what MySQL executes:
# no NO_BACKSLASH_ESCAPES / ANSI_QUOTES / ANSI (they change how quotes and backslashes are read).
SAFE_SQL_MODES = {"ERROR_FOR_DIVISION_BY_ZERO", "NO_ENGINE_SUBSTITUTION", "STRICT_TRANS_TABLES", "STRICT_ALL_TABLES",
                  "NO_ZERO_DATE", "NO_ZERO_IN_DATE", "ONLY_FULL_GROUP_BY", "NO_AUTO_VALUE_ON_ZERO",
                  "ALLOW_INVALID_DATES", "NO_UNSIGNED_SUBTRACTION"}
CLASSES = ("string", "binary", "exact", "temporal")

TOKEN_RE = re.compile(rb"^(?:N|(?:[0-9A-F]{2})*)$")
EXACT_RE = re.compile(rb"^-?[0-9]+(?:\.[0-9]+)?$")
TEMPORAL_RE = re.compile(rb"^-?[0-9]{1,4}[-:0-9 .]*$")


def classify(col):
    dt = col["data_type"]
    for cls, types in (("string", STRING), ("binary", BINARY), ("exact", EXACT), ("temporal", TEMPORAL)):
        if dt in types:
            return cls
    return None


def safe_sql_mode(mode):
    return isinstance(mode, str) and all(t in SAFE_SQL_MODES for t in mode.split(",") if t)


def valid_columns(cols):
    """Column metadata read back from a snapshot goes into SQL: re-check it against the codec."""
    return bool(cols) and all(
        isinstance(c.get("name"), str) and NAME_RE.match(c["name"]) and c.get("class") in CLASSES
        and classify({"data_type": c.get("data_type")}) == c["class"]
        and (c["class"] != "string" or c.get("charset") in CHARSETS) for c in cols)


def ident(name):
    if not NAME_RE.match(name):
        raise SnapshotError("unsupported identifier in the source schema")
    return f"`{name}`"


# --- export ----------------------------------------------------------------------------------

def token_sql(col, alias=None):
    c = (f"{alias}." if alias else "") + ident(col["name"])
    value = f"HEX({c})" if col["class"] in ("string", "binary") else f"HEX(CAST({c} AS CHAR))"
    # IF, never IFNULL(HEX(...)): an over-long value makes HEX NULL, which then prints as the invalid
    # token `NULL` and fails the export instead of silently becoming SQL NULL.
    return f"IF({c} IS NULL,'N',{value})"


def line_sql(cols, alias=None):
    return f"CONCAT_WS({SEP},{','.join(token_sql(c, alias) for c in cols)})"


def rows_sql(schema, table, cols):
    """Tokens as separate columns: the client joins them with a real TAB (a TAB inside one value would
    be escaped by --batch), and tokens hold nothing to escape. The bytes equal line_sql()."""
    return f"SELECT {','.join(token_sql(c) for c in cols)} FROM {ident(schema)}.{ident(table)};"


def stat_sql(schema, table, cols, marker):
    """One line: marker, COUNT(*), four digest lanes, JSON {column: [non-empty, non-zero]}."""
    lanes = ",".join(f"IFNULL(SUM(CAST(CONV(SUBSTRING(x.`__vtsnap_h`,{1 + 16 * i},16),16,10) AS UNSIGNED)),0)"
                     for i in range(4))
    counts = []
    for c in cols:
        nz = (f"SUM(x.{ident(c['name'])} IS NOT NULL AND x.{ident(c['name'])}<>0)"
              if c["data_type"] in NUMERIC_TYPES else "NULL")
        counts.append(f"'{c['name']}',JSON_ARRAY({nonempty_expr(c['name'], c['data_type'], 'x')},{nz})")
    inner = ",".join(f"t.{ident(c['name'])}" for c in cols)
    return (f"SELECT '{marker}',COUNT(*),{lanes},JSON_OBJECT({','.join(counts)}) FROM "
            f"(SELECT SHA2({line_sql(cols, 't')},256) `__vtsnap_h`,{inner} FROM {ident(schema)}.{ident(table)} t) x;")


def lanes_of(lines):
    """Python twin of the SQL digest: per line sha256, four 64-bit lanes summed (order-independent)."""
    s = [0, 0, 0, 0]
    for line in lines:
        h = hashlib.sha256(line).hexdigest()
        for i in range(4):
            s[i] += int(h[16 * i:16 * i + 16], 16)
    return [str(v) for v in s]


def check_line(line, ncols):
    tokens = line.split(b"\t")
    return len(tokens) == ncols and all(TOKEN_RE.match(t) for t in tokens)


# --- schema catalogue ------------------------------------------------------------------------

def catalogue_sql(schema, marker):
    """Structural catalogue of a schema: tables, columns, indexes, other objects. No volatile
    values (sizes, times, AUTO_INCREMENT), no schema name in the lines: the restored copy under
    another name yields the same lines."""
    s = f"'{schema}'"
    if not NAME_RE.match(schema):
        raise SnapshotError("bad schema name")
    return "\n".join([
        f"SELECT '{marker}';",
        "SELECT 'T',table_name,table_type,IFNULL(engine,''),IFNULL(table_collation,''),IFNULL(create_options,'') "
        f"FROM information_schema.tables WHERE table_schema={s} ORDER BY table_name;",
        "SELECT 'C',table_name,LPAD(ordinal_position,4,'0'),column_name,data_type,column_type,is_nullable,"
        "IF(column_default IS NULL,'N',HEX(column_default)),IFNULL(character_set_name,''),IFNULL(collation_name,''),"
        f"extra,HEX(IFNULL(generation_expression,'')) FROM information_schema.columns WHERE table_schema={s} "
        "ORDER BY table_name,ordinal_position;",
        "SELECT 'I',table_name,index_name,LPAD(seq_in_index,4,'0'),IFNULL(column_name,''),non_unique,"
        "IFNULL(sub_part,''),index_type,HEX(IFNULL(expression,'')) "
        f"FROM information_schema.statistics WHERE table_schema={s} ORDER BY table_name,index_name,seq_in_index;",
        f"SELECT 'O',(SELECT COUNT(*) FROM information_schema.views WHERE table_schema={s}),"
        f"(SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema={s}),"
        f"(SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema={s}),"
        f"(SELECT COUNT(*) FROM information_schema.events WHERE event_schema={s}),"
        f"(SELECT CONCAT(default_character_set_name,' ',default_collation_name) FROM information_schema.schemata "
        f"WHERE schema_name={s});",
    ])


# Words allowed in a DDL outside literals and identifiers: the keywords and type names SHOW CREATE TABLE
# printed for the source (all 785 tables, 2026-10-06) plus the codec's other types. Anything else —
# another engine (MERGE … UNION=(other_db.t) would let the restore INSERT into another database),
# partitions, foreign keys, generated columns, data/index directories — is refused, not interpreted.
DDL_WORDS = {"CREATE", "TABLE", "NOT", "NULL", "DEFAULT", "AUTO_INCREMENT", "PRIMARY", "UNIQUE", "KEY", "USING",
             "BTREE", "ENGINE", "InnoDB", "MyISAM", "CHARACTER", "SET", "CHARSET", "COLLATE", "COMMENT",
             "ROW_FORMAT", "COMPACT", "DYNAMIC", "ON", "UPDATE", "CURRENT_TIMESTAMP", "unsigned",
             *STRING, *BINARY, *EXACT, *TEMPORAL, *CHARSETS}
COLLATION_RE = re.compile(r"(?:latin1|utf8mb3|utf8mb4|ascii)_[a-z0-9_]+")


def single_create_table(ddl, table, engine):
    """The DDL of a table is executed as MySQL root on the stand: accept exactly one
    `CREATE TABLE `<table>` (` statement of the expected engine. A character scan (not regexes: a
    quote inside a comment must not open a literal) skips string literals ('…', "…" with '' and
    backslash escapes) and backtick identifiers; outside them a comment (/* -- #), `;` (a second
    statement) or backslash (mysql client commands such as \\! run a shell) is refused, and only the
    words of DDL_WORDS, collation names and numbers may appear."""
    if engine not in ENGINES or not ddl.startswith(f"CREATE TABLE `{table}` ("):
        return False
    outside, i, n = [], 0, len(ddl)
    while i < n:
        ch = ddl[i]
        if ch in "'\"`":
            i += 1
            while True:
                if i >= n:
                    return False                      # unterminated literal or identifier
                if ch != "`" and ddl[i] == "\\":
                    i += 2
                elif ddl[i] == ch and ddl[i + 1:i + 2] == ch:
                    i += 2                            # doubled quote inside
                elif ddl[i] == ch:
                    i += 1
                    break
                else:
                    i += 1
            outside.append(" ")
        elif ch in ";\\#" or ddl.startswith("/*", i) or ddl.startswith("--", i):
            return False
        else:
            outside.append(ch)
            i += 1
    body = "".join(outside)
    if not re.fullmatch(r"[A-Za-z0-9_\s(),=]*", body):
        return False
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body)
    return (all(w in DDL_WORDS or COLLATION_RE.fullmatch(w) for w in words) and words.count("ENGINE") == 1
            and re.findall(r"\bENGINE\s*=\s*(\w+)", body) == [engine])


def unescape(field):
    """Reverse mysql --batch escaping (\\0 \\t \\n \\\\), strictly."""
    if b"\\" not in field:
        return field
    out, i = bytearray(), 0
    while i < len(field):
        b = field[i]
        if b == 0x5C:
            nxt = field[i + 1:i + 2]
            mapped = {b"0": b"\0", b"t": b"\t", b"n": b"\n", b"\\": b"\\"}.get(nxt)
            if mapped is None:
                raise SnapshotError("unexpected escape in mysql batch output")
            out += mapped
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def fields(line):
    return [unescape(f).decode("utf-8") for f in line.split(b"\t")]


def fingerprint(lines):
    return hashlib.sha256(b"\n".join(sorted(lines))).hexdigest()


def parse_catalogue(lines):
    tables, columns, objects = {}, {}, None
    for line in lines:
        f = fields(line)
        if f[0] == "T":
            tables[f[1]] = {"type": f[2], "engine": f[3], "collation": f[4], "create_options": f[5]}
        elif f[0] == "C":
            col = {"name": f[3], "ordinal": int(f[2]), "data_type": f[4], "column_type": f[5],
                   "charset": f[8], "extra": f[10], "generated": f[11] != ""}
            col["class"] = classify(col)
            columns.setdefault(f[1], []).append(col)
        elif f[0] == "O":
            cs, _, coll = f[5].partition(" ")
            objects = {"views": int(f[1]), "triggers": int(f[2]), "routines": int(f[3]), "events": int(f[4]),
                       "charset": cs, "collation": coll}
    for cols in columns.values():
        cols.sort(key=lambda c: c["ordinal"])
    return {"tables": tables, "columns": columns, "objects": objects, "fingerprint": fingerprint(lines)}


def unsupported(cat):
    """Everything this codec does not handle: refuse before export instead of guessing."""
    problems = []
    obj = cat["objects"] or {}
    if any(obj.get(k) for k in ("views", "triggers", "routines", "events")):
        problems.append("views/triggers/routines/events present")
    if not (NAME_RE.match(obj.get("charset", "")) and NAME_RE.match(obj.get("collation", ""))):
        problems.append("schema charset/collation")
    for t, info in sorted(cat["tables"].items()):
        if not NAME_RE.match(t) or info["type"] != "BASE TABLE" or info["engine"] not in ENGINES:
            problems.append(f"table {t}")
            continue
        for c in cat["columns"].get(t, []):
            extra = c["extra"].upper()
            if (not NAME_RE.match(c["name"]) or c["class"] is None or c["generated"] or "INVISIBLE" in extra
                    or "VIRTUAL GENERATED" in extra or "STORED GENERATED" in extra
                    or (c["class"] == "string" and c["charset"] not in CHARSETS)):
                problems.append(f"column {t}.{c['name']} ({c['column_type']})")
    return problems


# --- restore ---------------------------------------------------------------------------------

def literal(token, col):
    if token == b"N":
        return "NULL"
    if col["class"] == "string":
        return f"_{col['charset']} X'{token.decode('ascii')}'"
    if col["class"] == "binary":
        return f"X'{token.decode('ascii')}'"
    text = bytes.fromhex(token.decode("ascii"))
    if col["class"] == "exact" and EXACT_RE.match(text):
        return text.decode("ascii")
    if col["class"] == "temporal" and TEMPORAL_RE.match(text):
        return "'" + text.decode("ascii") + "'"
    raise SnapshotError(f"bad {col['class']} token in column {col['name']}")
