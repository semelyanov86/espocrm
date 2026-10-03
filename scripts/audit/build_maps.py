#!/usr/bin/env python3
"""Build the anonymised docs/migration/field-map.csv and relations.csv from private audit outputs.

Usage: build_maps.py OUTDIR DOCSDIR

Inputs (private, outside Git): OUTDIR/columns.tsv (consolidate.py), 14_picklist_values.tsv,
13_reference_targets.tsv, 20_relations.tsv, 25_activity_workflows.tsv, 27_payments.tsv, 32_cardinality.tsv.
Outputs contain only schema metadata, counts, maximum string lengths and the mapping — never row values.
Stage 03: every target is checked against the EspoCRM model (scripts/model/model_check.py): column `espo_check`,
and `mapping_status=реализовано (этап 03)` for rows whose target exists with a compatible type and length.
Stage 04.1: rows of finance modules not yet in the model get `контракт (этап 04.1)` (finance-contract.md §11).
Stage 04.2: rows of Quote, SalesOrder, their items and LegalEntity (requisites per column) get
`реализовано (этап 04.2)`; generic line rows stay `контракт` until Invoice and Act items exist.
Stage 04.3: rows of Invoice and its items get `реализовано (этап 04.3)`; links to Act and payments stay `контракт`
(model_check.DEFERRED) and generic line rows stay partial until ActItem exists.
Stage 04.5: rows of Act and its items, Invoice.act and the generic line rows get `реализовано (этап 04.5)`.
Stage 04.6: the contract status is gone — a finance row that migrates nothing (excluded, empty, not migrated as data)
is `решено` (the fate is the reason); a migrated one stays `предложено` until the model check finds its target, and
scripts/model/build_finance_coverage.py reports it as open. The payment record keys are checked as Payment.vtigerId.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
import mapping as M  # noqa: E402
import model_check  # noqa: E402

DECIDED = "решено"
DOC_LINK = {"Invoice": "invoice", "Act": "act", "Quotes": "quote", "SalesOrder": "salesOrder", "Consignment": "data"}
NUMERIC = re.compile(r"^(int|tinyint|smallint|mediumint|bigint|decimal|float|double)")


def finance_status(status, fate):
    """Stage 04.6: a finance row that migrates nothing (excluded, empty, not migrated as data) is decided — its fate is
    the reason; a migrated row stays as it is until the model check marks it implemented."""
    if status == "предложено" and fate.startswith(("исключено", "пусто", "не переносится")):
        return DECIDED
    return status


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


def read_kind_rows(path, kind):
    """Rows of a multi-statement mysql output whose first column equals `kind`."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if parts and parts[0] == kind:
                rows.append(parts)
    return rows


def true_counts(outdir):
    res = defaultdict(int)
    with open(outdir / "14_picklist_values.tsv", encoding="utf-8") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) == 5 and p[2] == "56" and p[3] in ("1", "on", "yes"):
                res[(p[0], p[1])] += int(p[4])
    return res


def meaningful(row, trues):
    """Non-empty live values; numeric → non-zero; checkbox → true values."""
    if row["uitype"] == "56":
        return trues.get((row["module"], row["fieldname"]), 0)
    if NUMERIC.match(row["db_type"]):
        if int(row["live_rows"] or 0) == 0:
            return 0  # module has no live rows in this table: never fall back to whole-table counts
        return int(row["nonzero_live"] or 0) if row["nonzero_live"] != "" else int(row["nonempty_live"] or 0)
    return int(row["nonempty_live"] or 0)


def fate_for(target, transform, count):
    if target is None:
        return "исключено: " + transform
    if "SECURE" in transform:
        return "перенос в защищённое хранилище" if count else "пусто — данных нет"
    if count == 0:
        return "пусто — данных нет"
    if target.startswith("vtigerData") or ".vtigerData" in target or target.startswith("VtigerArchive"):
        return "архив (только чтение)"
    return "перенос"


def max_lengths(outdir):
    """(module, table, column) → maximum CHAR_LENGTH among live records (42_max_lengths.raw, stage 03)."""
    import json
    res = {}
    path = outdir / "42_max_lengths.raw"
    if not path.exists():
        return res
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 4 or p[0] == "module":
                continue
            for col, value in json.loads(p[3]).items():
                if value is not None:
                    res[(p[0], p[1], col)] = value
    return res


def audit_date(outdir):
    """Date of the audit slice the counts come from: its started_at.txt (run-audit.sh), else the slice name
    (YYYYMMDDT…). No date — no maps: a wrong «проверено SQL» date is worse than a stop."""
    started = outdir / "started_at.txt"
    if started.is_file():
        m = re.match(r"(\d{4}-\d{2}-\d{2})T", started.read_text(encoding="utf-8").strip())
        if m:
            return m.group(1)
    m = re.match(r"(\d{4})(\d{2})(\d{2})T", outdir.resolve().name)
    if m:
        return "-".join(m.groups())
    raise SystemExit(f"audit date unknown: no started_at.txt and no YYYYMMDDT… name in {outdir}")


def field_rows(outdir):
    checked = f"проверено SQL {audit_date(outdir)}"
    trues = true_counts(outdir)
    maxlen = max_lengths(outdir)
    rows = read_tsv(outdir / "columns.tsv")
    module_tables = {r["table"] for r in rows if r["in_vtiger_field"] == "1"}
    out = []
    for r in rows:
        mod = r["module"]
        count = meaningful(r, trues) if r["in_vtiger_field"] == "1" else None
        custom = "да" if r["generatedtype"] == "2" or r["column"].startswith("cf_") else "нет"
        verification = "count"
        status = "предложено"
        if r["in_vtiger_field"] == "1":
            entity, _mfate = M.MODULES.get(mod, ("?", "?"))
            fname = r["fieldname"]
            rule = None
            if mod in M.ARCHIVE_MODULES:
                rule = (f"VtigerArchive.data.{fname}", "JSON как есть; ссылки как vtigerId", "count+hash")
            elif mod == "VTEItems":
                rule = (None, "модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает; "
                              "1 расхождение суммы — в отчёт; решение владельца, Q-12)", "count")
            elif mod == "Notifications":
                rule = (None, "служебное уведомление (1 запись 2018 г.)", "count")
                status = "решено"
            elif mod == "Users" and fname in M.USERS_UI_PREFS:
                rule = (None, "UI-настройка Vtiger (Preferences EspoCRM задаются заново)", "count")
            else:
                rule = M.F.get(mod, {}).get(fname)
                if rule is None and r["table"] == "vtiger_inventoryproductrel":
                    rule = M.LINE_ITEM.get(fname)
                    if rule:
                        doc = {"Quotes": "Quote", "SalesOrder": "SalesOrder", "Invoice": "Invoice", "Act": "Act",
                               "PurchaseOrder": "PurchaseOrder", "Consignment": "Consignment"}.get(mod, mod)
                        rule = (rule[0].replace("<Doc>", doc) if rule[0] else None, rule[1], rule[2])
                if rule is None:
                    rule = M.COMMON.get(fname)
            if rule is None:
                if count:
                    rule = (f"vtigerData.{fname}", "как есть (семантика поля не определена)", "count+hash")
                    status = "не проверено"
                else:
                    rule = ("—", "нет данных", "count")
            target, transform, verification = rule
            if "не проверен" in transform and status == "предложено":
                status = "не проверено"
            if "владельц" in transform:
                status = "решено"  # confirmed by the owner in open-questions.md
            fate = fate_for(None if target is None else target, transform, count)
            if target == "—":
                fate = "пусто — данных нет"
            elif fname in M.NULL_SIGNIFICANT and r["live_rows"] not in ("", "0"):
                fate = "перенос (значимы NULL и 0)"
            if mod in M.FINANCE_CONTRACT_MODULES:
                status = finance_status(status, fate)
            ml = maxlen.get((mod, r["table"], r["column"]))
            out.append([mod, r["table"], r["column"], fname, r["label"], r["uitype"], r["db_type"], custom,
                        r["nonempty_all"], r["live_rows"], count, entity if target not in (None, "—") else "—",
                        target or "—", transform, verification, fate, status, checked,
                        "" if ml is None else ml])
        else:
            tbl, col = r["table"], r["column"]
            numeric = bool(NUMERIC.match(r["db_type"]))
            ne = int(r["nonempty_all"] or 0)
            nz = r["nonzero_all"]
            eff_all = int(nz) if nz not in ("", None) and numeric else ne
            if r["live_rows"] != "":
                # module table linked to vtiger_crmentity: count only rows of live records
                lnz = r["nonzero_live"]
                eff = int(lnz) if lnz not in ("", None) and numeric else int(r["nonempty_live"] or 0)
                live_records = r["live_rows"]
            else:
                eff, live_records = eff_all, ""
            if tbl in module_tables:
                rule = M.UNDECLARED.get((tbl, col))
                if rule is None:
                    if col.endswith("id") and eff_all == int(r["table_rows"]):
                        rule = ("(ключ записи)", "первичный ключ модульной таблицы = crmid", "count")
                    elif eff == 0:
                        rule = ("—", "нет данных", "count")
                    else:
                        rule = (f"vtigerData.{col}", "колонка без описания в vtiger_field", "count")
                        status = "не проверено"
                target, transform, verification = rule
                category = "модульная таблица (колонка без vtiger_field)"
                if target is None:
                    fate = "исключено: " + transform
                elif target == "—":
                    fate = "пусто — данных нет"
                elif target.startswith("vtigerData") or "vtigerData" in target:
                    fate = "архив (только чтение)" if eff else "пусто — данных нет"
                else:
                    fate = "перенос" if eff else "пусто — данных нет"
                entity = "—"
            elif tbl == "vtiger_organizationdetails":
                # One row: requisites of the single LegalEntity (stage 04.2); values stay out of Git.
                entity = "LegalEntity (собственная)"
                if col in M.ORGANIZATION_EXCLUDED:
                    target, transform = "—", M.ORGANIZATION_EXCLUDED[col]
                    fate = "пусто — данных нет" if eff == 0 else "исключено: " + transform
                else:
                    target = M.ORGANIZATION.get(col, f"vtigerData.{col}")
                    transform = M.ORGANIZATION_NOTES.get(col, "реквизит юрлица (значение вне Git)")
                    fate = "перенос (значения вне Git)" if eff else "пусто — данных нет"
                    if col not in M.ORGANIZATION:
                        status = "не проверено"
            else:
                category, fate, target = "?", "не классифицировано", "—"
                for rx, cat, tfate, ttarget in M.TABLE_RULES:
                    if re.search(rx, tbl):
                        category, fate, target = cat, tfate, ttarget
                        break
                transform = category
                entity = "—"
                if "владельц" in fate:
                    status = "решено"
                if fate == "не классифицировано":
                    status = "не проверено"
            if tbl in M.FINANCE_CONTRACT_TABLES:
                status = finance_status(status, fate)
            out.append(["", tbl, col, "", "", "", r["db_type"], "нет", r["nonempty_all"], live_records,
                        eff if live_records != "" else "", entity, target, transform, verification, fate, status,
                        checked, ""])
    return out


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


REL_TARGETS = {
    ("Potentials", "related_to"): "Opportunity.account (belongsTo)",
    ("Potentials", "contact_id"): "Opportunity.contacts (primary)",
    ("Potentials", "campaignid"): "Opportunity.campaign",
    ("Contacts", "accountid"): "Contact.account / accounts",
    ("Contacts", "reportsto"): "— (во всех записях '0')",
    ("Accounts", "parentid"): "Account.cParentAccount",
    ("HelpDesk", "parent_id"): "Case.account",
    ("HelpDesk", "contact_id"): "Case.contact",
    ("HelpDesk", "product_id"): "—",
    ("Quotes", "potentialid"): "Quote.opportunity",
    ("Quotes", "contactid"): "Quote.contact",
    ("Quotes", "accountid"): "Quote.account",
    ("Quotes", "inventorymanager"): "Quote.inventoryManager (User)",
    ("Quotes", "productid"): "QuoteItem.product",
    ("SalesOrder", "potentialid"): "SalesOrder.opportunity",
    ("SalesOrder", "quoteid"): "SalesOrder.quote",
    ("SalesOrder", "contactid"): "SalesOrder.contact",
    ("SalesOrder", "accountid"): "SalesOrder.account",
    ("SalesOrder", "productid"): "SalesOrderItem.product",
    ("Invoice", "salesorderid"): "Invoice.salesOrder",
    ("Invoice", "contactid"): "Invoice.contact",
    ("Invoice", "accountid"): "Invoice.account",
    ("Invoice", "sp_act_id"): "Invoice.act (belongsTo; обратная Act.invoices hasMany без ограничения 1:1)",
    ("Invoice", "potential_id"): "Invoice.opportunity",
    ("Invoice", "productid"): "InvoiceItem.product",
    ("Act", "salesorderid"): "— (у актов пусто: поле не создаётся, finance-contract.md §11 Act)",
    ("Act", "accountid"): "Act.account",
    ("Act", "contactid"): "Act.contact",
    ("Act", "productid"): "ActItem.product",
    ("PBXManager", "customer"): "Call.parent",
    ("ModComments", "smownerid"): "Note.vtigerData (у Note нет ответственного; автор — createdBy)",
    ("PBXManager", "user"): "Call.assignedUser",
    ("ServiceContracts", "sc_related_to"): "VtigerArchive.account",
    ("SPPayments", "payer"): "Payment.payer (Account|Contact|Vendor)",
    ("SPPayments", "related_to"): "PaymentAllocation.invoice | PaymentAllocation.salesOrder",
    ("ProjectTask", "projectid"): "ProjectTask.project",
    ("Project", "linktoaccountscontacts"): "Project.account",
    ("Project", "potentialid"): "Project.opportunity",
    ("Consignment", "invoiceid"): "VtigerArchive.invoice (+ vtigerId счёта в VtigerArchive.data)",
    ("Consignment", "salesorderid"): "VtigerArchive.data",
    ("Consignment", "accountid"): "VtigerArchive.account",
    ("Consignment", "contactid"): "VtigerArchive.contact",
    ("Consignment", "productid"): "VtigerArchive.data (строки)",
    ("Assets", "product"): "VtigerArchive.product",
    ("Assets", "invoiceid"): "VtigerArchive.data",
    ("Assets", "account"): "VtigerArchive.account",
    ("Assets", "contact"): "VtigerArchive.contact",
    ("ModComments", "customer"): "Note.vtigerData",
    ("ModComments", "userid"): "Note.createdBy (vtiger_users.id, не crmid)",
    ("ModComments", "related_to"): "Note.parent",
    ("ModComments", "parent_comments"): "—",
    ("Jivosite", "relatedcontact"): "VtigerArchive.contact",
    ("Jivosite", "relatedleads"): "VtigerArchive.lead",
    ("JVmes", "relatedjivo"): "VtigerArchive.parentArchive (сообщение → чат)",
    ("Notifications", "related_to"): "—",
    ("VTEItems", "related_to"): "— (исключено вместе с VTEItems)",
    ("VTEItems", "productid"): "— (исключено вместе с VTEItems)",
    ("SPCallPopup", "callid"): "слияние в Call (1:1)",
    ("Calendar", "crmid"): "Task.parent",
    ("Calendar", "contactid"): "Task.contact",
    ("Events", "crmid"): "Call|Meeting|Task.parent",
    ("Events", "contactid"): "Call|Meeting.contacts / Task.contact",
    ("Events", "invoiceid"): "—", ("Events", "salesorder_id"): "—", ("Events", "timesheet_id"): "—",
    ("Faq", "product_id"): "—", ("Products", "vendor_id"): "Product.vendor",
}

CRMREL_TARGETS = {
    ("Accounts", "Invoice"): "Invoice.account (дублирует поле accountid)",
    ("Accounts", "SPPayments"): "Payment.payer (дублирует поле payer)",
    ("Accounts", "Calendar"): "Task|Call|Meeting.parent",
    ("Accounts", "Contacts"): "Account.contacts (M:N accountContact)",
    ("Accounts", "Potentials"): "Opportunity.account (дублирует related_to)",
    ("Accounts", "HelpDesk"): "Case.account",
    ("Accounts", "Project"): "Project.account",
    ("Contacts", "Calendar"): "Task|Call|Meeting.parent / Call|Meeting.contacts / Task.contact",
    ("Contacts", "Emails"): "Email.parent",
    ("Contacts", "HelpDesk"): "Case.contacts",
    ("Contacts", "Invoice"): "Invoice.contact",
    ("Contacts", "Jivosite"): "VtigerArchive.contact",
    ("Contacts", "PBXManager"): "Call.parent / Call.contacts",
    ("Contacts", "SPCallPopup"): "слияние в Call",
    ("Contacts", "SPPayments"): "Payment.payer",
    ("HelpDesk", "Emails"): "Email.parent (все письма удалены)",
    ("Invoice", "Calendar"): "Task|Call|Meeting.parent (родитель Invoice)",
    ("Invoice", "Consignment"): "VtigerArchive.invoice (дублирует поле invoiceid)",
    ("Invoice", "SPPayments"): "PaymentAllocation.invoice (объединение с related_to)",
    ("Leads", "Calendar"): "Task|Call|Meeting.parent",
    ("Leads", "Emails"): "Email.parent",
    ("Leads", "Jivosite"): "VtigerArchive.lead",
    ("Leads", "PBXManager"): "Call.parent / Call.leads",
    ("Leads", "SPCallPopup"): "слияние в Call",
    ("PBXManager", "SPCallPopup"): "слияние в Call (1:1)",
    ("Potentials", "Calendar"): "Task|Call|Meeting.parent",
    ("Potentials", "Emails"): "Email.parent",
    ("Potentials", "Invoice"): "Invoice.opportunity",
    ("Potentials", "Quotes"): "Quote.opportunity",
    ("Potentials", "Services"): "Opportunity.cProducts (M:N)",
    ("Project", "HelpDesk"): "Project.cases (M:N)",
    ("Project", "ProjectTask"): "ProjectTask.project (дублирует projectid)",
    ("SPCallPopup", "Contacts"): "слияние в Call", ("SPCallPopup", "Leads"): "слияние в Call",
    ("SPCallPopup", "PBXManager"): "слияние в Call (1:1)",
    ("Vendors", "SPPayments"): "Payment.payer (Vendor)",
}


DOC_LINKS = {
    "Accounts": "Account.documents", "Contacts": "Contact.documents", "Leads": "Lead.documents",
    "Potentials": "Opportunity.documents", "HelpDesk": "Case.cDocuments", "Faq": "KnowledgeBaseArticle.cDocuments",
    "Project": "Project.documents", "ProjectTask": "ProjectTask.documents", "Consignment": "VtigerArchive.documents",
    "Invoice": "Invoice.documents", "Act": "Act.documents", "SPPayments": "Payment.documents",
}
TAG_FIELDS = {"Faq": "KnowledgeBaseArticle.cTags", "HelpDesk": "Case.cTags", "ProjectTask": "ProjectTask.tags"}


def relation_rows(outdir):
    rows = []
    # 1. Reference fields.
    agg = defaultdict(lambda: defaultdict(int))
    meta = {}
    with open(outdir / "13_reference_targets.tsv", encoding="utf-8") as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) != 7 or p[0] == "module":
                continue
            module, tbl, col, uitype, target, tdel, n = p
            key = (module, tbl, col)
            # vtiger_field may declare the same column twice (e.g. created_user_id as uitype 52 and 53):
            # both queries return identical rows, so only the first declared uitype is counted.
            if meta.setdefault(key, uitype) != uitype:
                continue
            label = target + ("(удалён)" if tdel == "1" else "")
            agg[key][label] += int(n)
    for (module, tbl, col), dist in sorted(agg.items()):
        uitype = meta[(module, tbl, col)]
        live = sum(v for k, v in dist.items() if not k.startswith("(") and "(удалён)" not in k and not k.startswith("user:") and k != "group")
        owners = sum(v for k, v in dist.items() if k.startswith("user:") or k == "group")
        dangling = sum(v for k, v in dist.items() if k == "(dangling)" or "(удалён)" in k)
        distribution = "; ".join(f"{k}:{v}" for k, v in sorted(dist.items(), key=lambda x: -x[1]))
        if uitype in ("52", "53", "77", "101"):
            kind, card = "owner", "N:1"
            target = {"smownerid": "assignedUser/teams", "smcreatorid": "createdBy", "modifiedby": "modifiedBy"}.get(col, "User link")
            if (module, col) in REL_TARGETS:
                target = REL_TARGETS[(module, col)]
            count = owners
        else:
            kind, card = "field", "N:1"
            target = REL_TARGETS.get((module, col), "(не определено)")
            count = live
        if (module, col) == ("ModComments", "userid"):
            # userid holds vtiger_users.id, not a crmid (verified: 77 of 78 match a user, 1 empty).
            uc = {p[0]: p for p in read_kind_rows(outdir / "20_relations.tsv", "modcomments_userid")}
            count, dangling = int(uc["modcomments_userid"][1]), 0
            distribution = f"user:{count}; (empty):{int(uc['modcomments_userid'][3]) - count}"
        mods = sorted({k.split("(")[0].split(":")[0] for k in dist if not k.startswith("(")} - {""})
        to_module = "|".join("User" if m == "user" else ("Group" if m == "group" else m) for m in mods) or "—"
        if (module, col) == ("ModComments", "userid"):
            to_module = "Users"
        fate = "перенос" if count else "пусто — данных нет"
        if module in M.ARCHIVE_MODULES:
            fate = "архив (только чтение)" if count else fate
        if module in ("VTEItems", "Notifications"):
            fate = "исключено вместе с модулем"
        status = "не проверено" if target == "(не определено)" else "предложено"
        verify = "fk-resolve: число разрешённых ссылок = число в источнике; висячие — в отчёт"
        rows.append([f"{module}.{col}", kind, f"{tbl}.{col}", module, to_module,
                     card, count, dangling, distribution, target, verify, fate, status])
    # 1b. Reference/owner fields of non-empty tables that returned no rows at all (e.g. Calendar tasks
    # have no vtiger_cntactivityrel rows) — listed with zero so the inventory of links is complete.
    counts = {r["tbl"]: int(r["n"]) for r in read_tsv(outdir / "10_table_counts.tsv")}
    seen_ref = {(r[3], r[2].split(".")[0], r[2].split(".", 1)[1]) for r in rows}
    live_modules = {t["name"] for t in read_tsv(outdir / "01_tabs.tsv") if int(t["live"]) > 0} | {"Events"}
    for f in read_tsv(outdir / "02_fields.tsv"):
        mod, tbl, col = f["module"], f["tablename"], f["columnname"]
        if mod == "Users" or mod not in live_modules or counts.get(tbl, 0) == 0 or (mod, tbl, col) in seen_ref:
            continue
        if f["uitype"] not in ("10", "51", "57", "58", "59", "66", "68", "73", "75", "76", "78", "80", "81",
                               "52", "53", "77", "101"):
            continue
        seen_ref.add((mod, tbl, col))
        rows.append([f"{mod}.{col}", "field", f"{tbl}.{col}", mod, "—", "N:1", 0, 0, "(нет строк у живых записей модуля)",
                     REL_TARGETS.get((mod, col), "—"), "fk-resolve", "пусто — данных нет", "предложено"])
    # 2. vtiger_crmentityrel pairs.
    card = {(p[1], p[2]): (p[4], p[5]) for p in read_kind_rows(outdir / "32_cardinality.tsv", "crmentityrel_card")}
    pairs = defaultdict(lambda: [0, 0])
    for p in read_kind_rows(outdir / "20_relations.tsv", "crmentityrel"):
        _, module, src, sdel, rel, dst, ddel, n = p
        idx = 0 if sdel == "0" and ddel == "0" else 1
        pairs[(module, rel)][idx] += int(n)
    for (module, rel), (live, dead) in sorted(pairs.items()):
        mx = card.get((module, rel))
        c = f"M:N (max {mx[0]} на источник, {mx[1]} на цель)" if mx else "M:N"
        target = CRMREL_TARGETS.get((module, rel), "(не определено)")
        fate = "перенос" if live else "исключено: только удалённые записи"
        if "слияние" in target:
            fate = "слияние"
        rows.append([f"crmentityrel:{module}->{rel}", "m2m", "vtiger_crmentityrel", module, rel, c, live, dead, "",
                     target, "count: пары live/live; дубли с полями-ссылками схлопываются", fate,
                     "не проверено" if target == "(не определено)" else "предложено"])
    # 3. Activity / document / attachment relation tables.
    se = defaultdict(lambda: [0, 0])
    for p in read_kind_rows(outdir / "20_relations.tsv", "seactivityrel"):
        _, parent, pdel, atype, adel, n = p
        se[(parent, atype)][0 if pdel == "0" and adel == "0" else 1] += int(n)
    for (parent, atype), (live, dead) in sorted(se.items()):
        target = {"Emails": "Email.parent", "Task": "Task.parent", "Письмо": "Task.parent (вид «Письмо»)",
                  "Call": "Call.parent", "Meeting": "Meeting.parent"}.get(atype, "(не определено)")
        rows.append([f"seactivityrel:{parent}->{atype}", "m2m", "vtiger_seactivityrel", parent, f"activity:{atype}",
                     "N:1 (max 1 родитель на активность)", live, dead, "", target, "count",
                     "перенос" if live else "исключено: только удалённые", "предложено"])
    for p in read_kind_rows(outdir / "20_relations.tsv", "cntactivityrel"):
        _, atype, adel, cdel, n = p
        target = {"Call": "Call.contacts", "Meeting": "Meeting.contacts", "Письмо": "Task.contact (вид «Письмо»)",
                  "Task": "Task.contact"}.get(atype, "(не определено)")
        rows.append([f"cntactivityrel:Contacts->{atype}", "m2m", "vtiger_cntactivityrel", "Contacts", f"activity:{atype}", "M:N", n, 0, "",
                     target, "count", "перенос", "предложено"])
    sa = defaultdict(lambda: [0, 0])
    for p in read_kind_rows(outdir / "20_relations.tsv", "salesmanactivityrel"):
        _, atype, adel, n = p
        sa[atype][0 if adel == "0" else 1] += int(n)
    for atype, (live, dead) in sorted(sa.items()):
        target = {"Call": "Call.users (приглашённые)", "Meeting": "Meeting.users (приглашённые)",
                  "Task": "Task.collaborators (участники)", "Письмо": "Task.collaborators (участники)"}.get(atype, "(не определено)")
        rows.append([f"salesmanactivityrel:Users->{atype}", "m2m", "vtiger_salesmanactivityrel", "Users", f"activity:{atype}", "M:N", live,
                     dead, "", target, "count", "перенос" if live else "исключено: только удалённые", "предложено"])
    scard = {p[1]: (p[3], p[4]) for p in read_kind_rows(outdir / "32_cardinality.tsv", "senotes_card")}
    sn = defaultdict(lambda: [0, 0])
    for p in read_kind_rows(outdir / "20_relations.tsv", "senotesrel"):
        _, parent, pdel, ndel, n = p
        sn[parent][0 if pdel == "0" and ndel == "0" else 1] += int(n)
    for parent, (live, dead) in sorted(sn.items()):
        mx = scard.get(parent)
        c = f"M:N (max {mx[0]} док. на запись, {mx[1]} записей на док.)" if mx and live else "M:N"
        rows.append([f"senotesrel:{parent}->Documents", "m2m", "vtiger_senotesrel", parent, "Documents", c, live, dead, "",
                     DOC_LINKS.get(parent, "(не определено)") + " (M:N с Document)", "count",
                     "перенос" if live else "исключено: только удалённые", "предложено"])
    for p in read_kind_rows(outdir / "20_relations.tsv", "seattachmentsrel"):
        _, parent, pdel, atype, adel, n = p
        target = {"Documents Attachment": "Document.file", "Emails Attachment": "Email.attachments",
                  "ModComments Attachment": "Note.attachments", "Contacts Image": "Contact.cPhoto"}.get(atype, "(не определено)")
        rows.append([f"seattachmentsrel:{parent}->{atype}", "attachment", "vtiger_seattachmentsrel", parent, atype, "1:N", n, 0, "",
                     target, "file-hash: наличие + sha256 каждого файла", "перенос", "предложено"])
    for p in read_kind_rows(outdir / "20_relations.tsv", "contpotentialrel"):
        rows.append(["contpotentialrel:Contacts->Potentials", "m2m", "vtiger_contpotentialrel", "Contacts", "Potentials", "M:N", p[3], 0, "",
                     "Opportunity.contacts", "count", "перенос", "предложено"])
    # 4. Special relations.
    dl = {p[1]: p for p in read_kind_rows(outdir / "32_cardinality.tsv", "doc_lines")}
    for mod, (doc, item) in {"Invoice": ("Invoice", "InvoiceItem"), "Act": ("Act", "ActItem"), "Quotes": ("Quote", "QuoteItem"),
                             "SalesOrder": ("SalesOrder", "SalesOrderItem"), "Consignment": ("VtigerArchive", "lines")}.items():
        p = dl.get(mod)
        if p:
            rows.append([f"lines:{mod}", "lines", "vtiger_inventoryproductrel.id", mod, "lines", f"1:N (max {p[4]} строк)", p[3], 0,
                         f"документов {p[2]}", f"{item}.{DOC_LINK[mod]}" if item != "lines" else "VtigerArchive.data (строки)",
                         "count+sum по документу", "перенос" if mod != "Consignment" else "архив (только чтение)", "предложено"])
    ppi = read_kind_rows(outdir / "32_cardinality.tsv", "payments_per_invoice")
    part = {p[1]: int(p[2]) for p in read_kind_rows(outdir / "33_allocation_check.tsv", "alloc_partition")}
    if part:
        allocated = sum(v for k, v in part.items() if k != "unallocated")
        rows.append(["allocation:SPPayments->Invoice", "derived", "sp_payments.related_to ∪ vtiger_crmentityrel(Invoice,SPPayments)",
                     "SPPayments", "Invoice|SalesOrder",
                     f"related_to: N:1 (до {ppi[0][1] if ppi else '?'} платежей на счёт); связь: ≤1 счёт на платёж; "
                     f"конфликтов {part.get('conflict_rel_other_invoice', 0)}",
                     allocated, part.get("conflict_rel_other_invoice", 0),
                     "; ".join(f"{k}: {v}" for k, v in sorted(part.items())),
                     "PaymentAllocation.payment / PaymentAllocation.invoice / PaymentAllocation.salesOrder (сумма = сумма платежа)",
                     "count по категориям разбиения; сумма распределений = сумма платежа; конфликты — ручной разбор",
                     "перенос: related_to — основной; связь — только при пустом related_to; конфликты не угадывать; "
                     "расходы со связью — Q-36", "предложено"])
    ia = read_kind_rows(outdir / "27_payments.tsv", "invoice_act")
    awi = read_kind_rows(outdir / "27_payments.tsv", "act_without_invoice")
    if ia:
        rows.append(["invoice_act:Invoice->Act", "field", "vtiger_invoice.sp_act_id", "Invoice", "Act",
                     f"N:1, фактически ≤1:1 (актов со связью {ia[0][1]}, макс. счетов на акт {ia[0][3]})", ia[0][1], 0,
                     f"живых актов без живого счёта: {awi[0][1] if awi else '?'}", "Invoice.act / Act.invoices (hasMany, без ограничения 1:1)", "fk-resolve", "перенос", "предложено"])
    rows.append(["starred:Users->*", "m2m", "vtiger_crmentity_user_field", "*", "Users", "M:N", 3, 0, "истинных отметок: Faq 3",
                 "—", "count", "исключено: персональные «звёздочки»", "решено"])
    for p in read_kind_rows(outdir / "25_activity_workflows.tsv", "tags"):
        rows.append([f"tags:{p[1]}", "m2m", "vtiger_freetagged_objects", p[1], "tags", "M:N", p[2], 0, f"тегов {p[3]}",
                     TAG_FIELDS.get(p[1], "(не определено)") + " (multiEnum)", "count", "перенос", "предложено"])
    for p in read_kind_rows(outdir / "25_activity_workflows.tsv", "modtracker_relations"):
        rows.append([f"history-link:{p[1]}->{p[2]}", "history", "vtiger_modtracker_relations", p[1], p[2], "журнал", p[3], 0, "",
                     "—", "count", "исключено: история не переносится (Q-27)", "решено"])
    rows.append(["users2group", "acl", "vtiger_users2group", "Users", "Groups", "M:N", 4, 0, "", "User.teams", "count", "перенос", "предложено"])
    rows.append(["user2role", "acl", "vtiger_user2role", "Users", "Roles", "N:1", 7, 0, "", "User.roles", "count", "перенос (роли пересобираются)", "предложено"])
    for r in rows:  # links of finance documents: final status (stage 04.6)
        if r[3] in M.FINANCE_CONTRACT_MODULES or r[4] in M.FINANCE_CONTRACT_MODULES:
            r[12] = finance_status(r[12], r[11])
    return rows


FIELD_HEADER = ["source_module", "source_table", "source_column", "source_field", "source_label", "uitype", "source_db_type",
                "custom", "nonempty_all_rows", "live_records", "nonempty_live", "target_entity", "target_field", "transform",
                "verification", "fate", "mapping_status", "count_status", "max_len_live", "espo_check"]
REL_HEADER = ["relation_id", "kind", "source_object", "from_module", "to_module", "cardinality_observed", "live_count",
              "deleted_or_dangling", "distribution", "target_link", "verification", "fate", "status", "espo_check"]
def apply_model_check(rows, header, checker, status_col):
    """Append `espo_check`; flip the status of rows whose target exists in the EspoCRM model to
    `реализовано (этап 03|04.2)` (the stage of the row's entities)."""
    try:
        model = model_check.Model()
    except SystemExit as exc:  # no unpacked core: keep the maps, mark the check as not done
        print(f"model check skipped: {exc}")
        return [r + ["не проверено: нет ядра EspoCRM"] for r in rows], 0, 0
    idx = header.index(status_col)
    ok = failed = 0
    out = []
    for r in rows:
        row = dict(zip(header, r))
        res, text = checker(model, row) if checker is model_check.check_relation_row \
            else checker(model, row, row.get("max_len_live") or None)
        if res is True:
            ok += 1
            r = list(r)
            r[idx] = f"реализовано (этап {model_check.implemented_stage(model, row)})"
        elif res is False:
            failed += 1
        out.append(list(r) + [text])
    return out, ok, failed


def main():
    outdir, docs = Path(sys.argv[1]), Path(sys.argv[2])
    fr, f_ok, f_bad = apply_model_check(field_rows(outdir), FIELD_HEADER[:-1], model_check.check_field_row, "mapping_status")
    write_csv(docs / "field-map.csv", FIELD_HEADER, fr)
    rr, r_ok, r_bad = apply_model_check(relation_rows(outdir), REL_HEADER[:-1], model_check.check_relation_row, "status")
    write_csv(docs / "relations.csv", REL_HEADER, rr)
    print(f"field-map.csv: {len(fr)} rows (model: {f_ok} ok, {f_bad} failed); "
          f"relations.csv: {len(rr)} rows (model: {r_ok} ok, {r_bad} failed)")


if __name__ == "__main__":
    main()
