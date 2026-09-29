#!/usr/bin/env python3
"""Build the anonymised docs/migration/field-map.csv and relations.csv from private audit outputs.

Usage: build_maps.py OUTDIR DOCSDIR

Inputs (private, outside Git): OUTDIR/columns.tsv (consolidate.py), 14_picklist_values.tsv,
13_reference_targets.tsv, 20_relations.tsv, 25_activity_workflows.tsv, 27_payments.tsv, 32_cardinality.tsv.
Outputs contain only schema metadata, counts and proposed mapping — never row values.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mapping as M  # noqa: E402

AUDIT_DATE = "2026-09-29"
NUMERIC = re.compile(r"^(int|tinyint|smallint|mediumint|bigint|decimal|float|double)")


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
        v = row["nonzero_live"] if row["nonzero_live"] != "" else row["nonzero_all"]
        return int(v or 0)
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


def field_rows(outdir):
    trues = true_counts(outdir)
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
                rule = (None, "модуль VTEItems — дубль vtiger_inventoryproductrel (222 родителя, число строк совпадает)", "count")
                status = "решено"
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
            fate = fate_for(None if target is None else target, transform, count)
            if target == "—":
                fate = "пусто — данных нет"
            out.append([mod, r["table"], r["column"], fname, r["label"], r["uitype"], r["db_type"], custom,
                        r["nonempty_all"], r["live_rows"], count, entity if target not in (None, "—") else "—",
                        target or "—", transform, verification, fate, status, f"проверено SQL {AUDIT_DATE}"])
        else:
            tbl, col = r["table"], r["column"]
            ne = int(r["nonempty_all"] or 0)
            nz = r["nonzero_all"]
            eff = int(nz) if nz not in ("", None) and NUMERIC.match(r["db_type"]) else ne
            if tbl in module_tables:
                rule = M.UNDECLARED.get((tbl, col))
                if rule is None:
                    if col.endswith("id") and eff == int(r["table_rows"]):
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
            else:
                category, fate, target = "?", "не классифицировано", "—"
                for rx, cat, tfate, ttarget in M.TABLE_RULES:
                    if re.search(rx, tbl):
                        category, fate, target = cat, tfate, ttarget
                        break
                transform = category
                entity = "—"
                if fate == "не классифицировано":
                    status = "не проверено"
            out.append(["", tbl, col, "", "", "", r["db_type"], "нет", r["nonempty_all"], r["table_rows"], eff,
                        entity, target, transform, verification, fate, status, f"проверено SQL {AUDIT_DATE}"])
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
    ("Contacts", "reportsto"): "Contact.cReportsTo",
    ("Accounts", "parentid"): "Account.cParentAccount",
    ("HelpDesk", "parent_id"): "Case.account",
    ("HelpDesk", "contact_id"): "Case.contact",
    ("HelpDesk", "product_id"): "—",
    ("Quotes", "potentialid"): "Quote.opportunity",
    ("Quotes", "contactid"): "Quote.contact",
    ("Quotes", "accountid"): "Quote.account",
    ("Quotes", "inventorymanager"): "Quote.cInventoryManager (User)",
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
    ("Act", "salesorderid"): "Act.salesOrder",
    ("Act", "accountid"): "Act.account",
    ("Act", "contactid"): "Act.contact",
    ("Act", "productid"): "ActItem.product",
    ("PBXManager", "customer"): "Call.parent",
    ("PBXManager", "user"): "Call.assignedUser",
    ("ServiceContracts", "sc_related_to"): "VtigerArchive.parent",
    ("SPPayments", "payer"): "Payment.payer (Account|Contact)",
    ("SPPayments", "related_to"): "PaymentAllocation.invoice | PaymentAllocation.salesOrder",
    ("ProjectTask", "projectid"): "ProjectTask.project",
    ("Project", "linktoaccountscontacts"): "Project.account",
    ("Project", "potentialid"): "Project.opportunity",
    ("Consignment", "invoiceid"): "VtigerArchive.links",
    ("Consignment", "salesorderid"): "VtigerArchive.links",
    ("Consignment", "accountid"): "VtigerArchive.links",
    ("Consignment", "contactid"): "VtigerArchive.links",
    ("Consignment", "productid"): "VtigerArchive.lines",
    ("Assets", "product"): "VtigerArchive.links",
    ("Assets", "invoiceid"): "VtigerArchive.links",
    ("Assets", "account"): "VtigerArchive.links",
    ("Assets", "contact"): "VtigerArchive.links",
    ("ModComments", "customer"): "Note.vtigerData.customer",
    ("ModComments", "userid"): "Note.createdBy (vtiger_users.id, не crmid)",
    ("ModComments", "related_to"): "Note.parent",
    ("ModComments", "parent_comments"): "—",
    ("Jivosite", "relatedcontact"): "VtigerArchive.links",
    ("Jivosite", "relatedleads"): "VtigerArchive.links → Lead",
    ("JVmes", "relatedjivo"): "VtigerArchive.parentArchive (сообщение → чат)",
    ("Notifications", "related_to"): "—",
    ("VTEItems", "related_to"): "— (исключено вместе с VTEItems)",
    ("VTEItems", "productid"): "— (исключено вместе с VTEItems)",
    ("SPCallPopup", "callid"): "слияние в Call (1:1)",
    ("Calendar", "crmid"): "Task.parent",
    ("Calendar", "contactid"): "Task.parent/contact",
    ("Events", "crmid"): "Call|Meeting.parent",
    ("Events", "contactid"): "Call|Meeting.contacts",
    ("Events", "invoiceid"): "—", ("Events", "salesorder_id"): "—", ("Events", "timesheet_id"): "—",
    ("Faq", "product_id"): "—", ("Products", "vendor_id"): "Product.vendor",
}

CRMREL_TARGETS = {
    ("Accounts", "Invoice"): "Invoice.account (дублирует поле accountid)",
    ("Accounts", "SPPayments"): "Payment.payer (дублирует поле payer)",
    ("Accounts", "Calendar"): "Task/Meeting.parent",
    ("Accounts", "Contacts"): "Account.contacts (M:N accountContact)",
    ("Accounts", "Potentials"): "Opportunity.account (дублирует related_to)",
    ("Accounts", "HelpDesk"): "Case.account",
    ("Accounts", "Project"): "Project.account",
    ("Contacts", "Calendar"): "activity.parent/contacts",
    ("Contacts", "Emails"): "Email.parent",
    ("Contacts", "HelpDesk"): "Case.contacts",
    ("Contacts", "Invoice"): "Invoice.contact",
    ("Contacts", "Jivosite"): "VtigerArchive.links",
    ("Contacts", "PBXManager"): "Call.parent/contacts",
    ("Contacts", "SPCallPopup"): "слияние в Call",
    ("Contacts", "SPPayments"): "Payment.payer",
    ("HelpDesk", "Emails"): "Email.parent (все письма удалены)",
    ("Invoice", "Calendar"): "activity.parent",
    ("Invoice", "Consignment"): "VtigerArchive.links",
    ("Invoice", "SPPayments"): "PaymentAllocation (объединение с related_to)",
    ("Leads", "Calendar"): "activity.parent",
    ("Leads", "Emails"): "Email.parent",
    ("Leads", "Jivosite"): "VtigerArchive.links",
    ("Leads", "PBXManager"): "Call.parent/leads",
    ("Leads", "SPCallPopup"): "слияние в Call",
    ("PBXManager", "SPCallPopup"): "слияние в Call (1:1)",
    ("Potentials", "Calendar"): "activity.parent",
    ("Potentials", "Emails"): "Email.parent",
    ("Potentials", "Invoice"): "Invoice.opportunity",
    ("Potentials", "Quotes"): "Quote.opportunity",
    ("Potentials", "Services"): "Opportunity.cProducts (M:N)",
    ("Project", "HelpDesk"): "Project.cases (M:N)",
    ("Project", "ProjectTask"): "ProjectTask.project (дублирует projectid)",
    ("SPCallPopup", "Contacts"): "слияние в Call", ("SPCallPopup", "Leads"): "слияние в Call",
    ("SPCallPopup", "PBXManager"): "слияние в Call (1:1)",
    ("Vendors", "SPPayments"): "Payment.payer (Account type=Vendor)",
}


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
        target = "Email.parent" if atype == "Emails" else ("Task.parent" if atype == "Task" else "Call|Meeting.parent")
        rows.append([f"seactivityrel:{parent}->{atype}", "m2m", "vtiger_seactivityrel", parent, f"activity:{atype}",
                     "N:1 (max 1 родитель на активность)", live, dead, "", target, "count",
                     "перенос" if live else "исключено: только удалённые", "предложено"])
    for p in read_kind_rows(outdir / "20_relations.tsv", "cntactivityrel"):
        _, atype, adel, cdel, n = p
        rows.append([f"cntactivityrel:Contacts->{atype}", "m2m", "vtiger_cntactivityrel", "Contacts", f"activity:{atype}", "M:N", n, 0, "",
                     "Call|Meeting.contacts / Task.contact", "count", "перенос", "предложено"])
    sa = defaultdict(lambda: [0, 0])
    for p in read_kind_rows(outdir / "20_relations.tsv", "salesmanactivityrel"):
        _, atype, adel, n = p
        sa[atype][0 if adel == "0" else 1] += int(n)
    for atype, (live, dead) in sorted(sa.items()):
        rows.append([f"salesmanactivityrel:Users->{atype}", "m2m", "vtiger_salesmanactivityrel", "Users", f"activity:{atype}", "M:N", live,
                     dead, "", "Call|Meeting.users (приглашённые)", "count", "перенос" if live else "исключено: только удалённые", "предложено"])
    scard = {p[1]: (p[3], p[4]) for p in read_kind_rows(outdir / "32_cardinality.tsv", "senotes_card")}
    sn = defaultdict(lambda: [0, 0])
    for p in read_kind_rows(outdir / "20_relations.tsv", "senotesrel"):
        _, parent, pdel, ndel, n = p
        sn[parent][0 if pdel == "0" and ndel == "0" else 1] += int(n)
    for parent, (live, dead) in sorted(sn.items()):
        mx = scard.get(parent)
        c = f"M:N (max {mx[0]} док. на запись, {mx[1]} записей на док.)" if mx and live else "M:N"
        rows.append([f"senotesrel:{parent}->Documents", "m2m", "vtiger_senotesrel", parent, "Documents", c, live, dead, "",
                     "Document.parents / <Entity>.documents (M:N)", "count", "перенос" if live else "исключено: только удалённые", "предложено"])
    for p in read_kind_rows(outdir / "20_relations.tsv", "seattachmentsrel"):
        _, parent, pdel, atype, adel, n = p
        target = {"Documents Attachment": "Document.file", "Emails Attachment": "Email.attachments",
                  "ModComments Attachment": "Note.attachments", "Contacts Image": "Contact.avatar"}.get(atype, "(не определено)")
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
                         f"документов {p[2]}", f"{item}.{ 'parent' if item != 'lines' else 'data'}", "count+sum по документу", "перенос" if mod != "Consignment" else "архив (только чтение)", "предложено"])
    pay = {p[0]: p for p in read_kind_rows(outdir / "27_payments.tsv", "rel_consistency")}
    ppi = read_kind_rows(outdir / "32_cardinality.tsv", "payments_per_invoice")
    if pay:
        p = pay["rel_consistency"]
        ua = read_kind_rows(outdir / "33_allocation_check.tsv", "union_alloc")[0]
        rv = read_kind_rows(outdir / "33_allocation_check.tsv", "rel_vs_related_to")[0]
        rows.append(["allocation:SPPayments->Invoice", "derived", "sp_payments.related_to ∪ vtiger_crmentityrel(Invoice,SPPayments)",
                     "SPPayments", "Invoice|SalesOrder",
                     f"related_to: N:1 (до {ppi[0][1] if ppi else '?'} платежей на счёт); объединение: {ua[2]} платежей в 2 счетах (конфликт)",
                     ua[1], ua[2],
                     f"совпадают: {rv[1]}; связь указывает другой счёт: {rv[2]}; только связь (related_to пуст): {rv[3]}; только related_to: {p[2]}",
                     "PaymentAllocation(payment, invoice|salesOrder, amount)",
                     "count; сумма распределений = сумма платежа; конфликты — ручной разбор",
                     "перенос: related_to — основной; связь — только при пустом related_to; конфликты не угадывать", "не проверено"])
    ia = read_kind_rows(outdir / "27_payments.tsv", "invoice_act")
    if ia:
        rows.append(["invoice_act:Invoice->Act", "field", "vtiger_invoice.sp_act_id", "Invoice", "Act",
                     f"N:1, фактически ≤1:1 (актов со связью {ia[0][1]}, макс. счетов на акт {ia[0][3]})", ia[0][1], 0,
                     "11 актов без счёта", "Invoice.act / Act.invoices (hasMany, без ограничения 1:1)", "fk-resolve", "перенос", "предложено"])
    rows.append(["starred:Users->*", "m2m", "vtiger_crmentity_user_field", "*", "Users", "M:N", 3, 0, "истинных отметок: Faq 3",
                 "—", "count", "исключено: персональные «звёздочки»", "решено"])
    for p in read_kind_rows(outdir / "25_activity_workflows.tsv", "tags"):
        rows.append([f"tags:{p[1]}", "m2m", "vtiger_freetagged_objects", p[1], "tags", "M:N", p[2], 0, f"тегов {p[3]}",
                     f"{p[1]} → multiEnum tags", "count", "перенос", "предложено"])
    for p in read_kind_rows(outdir / "25_activity_workflows.tsv", "modtracker_relations"):
        rows.append([f"history-link:{p[1]}->{p[2]}", "history", "vtiger_modtracker_relations", p[1], p[2], "журнал", p[3], 0, "",
                     "VtigerChangeLog", "count", "архив (только чтение)", "предложено"])
    rows.append(["users2group", "acl", "vtiger_users2group", "Users", "Groups", "M:N", 4, 0, "", "User.teams", "count", "перенос", "предложено"])
    rows.append(["user2role", "acl", "vtiger_user2role", "Users", "Roles", "N:1", 7, 0, "", "User.roles", "count", "перенос (роли пересобираются)", "предложено"])
    return rows


def main():
    outdir, docs = Path(sys.argv[1]), Path(sys.argv[2])
    fr = field_rows(outdir)
    write_csv(docs / "field-map.csv",
              ["source_module", "source_table", "source_column", "source_field", "source_label", "uitype", "source_db_type",
               "custom", "nonempty_all_rows", "live_records", "nonempty_live", "target_entity", "target_field", "transform",
               "verification", "fate", "mapping_status", "count_status"], fr)
    rr = relation_rows(outdir)
    write_csv(docs / "relations.csv",
              ["relation_id", "kind", "source_object", "from_module", "to_module", "cardinality_observed", "live_count",
               "deleted_or_dangling", "distribution", "target_link", "verification", "fate", "status"], rr)
    print(f"field-map.csv: {len(fr)} rows; relations.csv: {len(rr)} rows")


if __name__ == "__main__":
    main()
