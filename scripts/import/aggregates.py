"""Exact aggregates of the finance import (stage 06.3, docs/migration/import.md «Сверка финансов»): the same measures
three ways — SQL on the restored source, the planner's own values, SQL on the stand — compared as decimals, no
tolerance. Stage 06.4 adds the taxes (TAX_MEASURES): the tax mode of the documents, the shipping tax rate, the tax a
document's totals carry (grand total − pre-tax total − adjustment), the archived tax rates 2 and 3 of the lines and the
header tax of the custom fields, and the lines with any tax rate. Source SQL = planned (all records) proves the reader; planned (imported records) = stand SQL proves the
writer. Records the owner's answers keep out of the import (deleted or recalculated in EspoCRM) are excluded on both
sides of the second comparison and listed. Amounts stay in the private report; Git gets equal/differs only.
"""
from decimal import Decimal, localcontext

import spec_finance as F

# document module → (base table, key, stand table)
DOCUMENT_TABLES = {"Quotes": ("vtiger_quotes", "quoteid", "quote"), "SalesOrder": ("vtiger_salesorder", "salesorderid",
                   "sales_order"), "Act": ("vtiger_sp_act", "actid", "act"),
                   "Invoice": ("vtiger_invoice", "invoiceid", "invoice")}
# measure → (source column, stand column, attribute of the operation)
HEADER = {"subtotal": ("subtotal", "subtotal", "subtotal"), "preTaxTotal": ("pre_tax_total", "pre_tax_total", "preTaxTotal"),
          "grandTotal": ("total", "grand_total", "grandTotal"),
          "discountAmount": ("discount_amount", "discount_amount", "discountAmount"),
          "shippingAmount": ("s_h_amount", "shipping_amount", "shippingAmount"),
          "adjustment": ("adjustment", "adjustment", "adjustment")}
LINE = {"quantity": ("quantity", "quantity", "quantity"), "unitPrice": ("listprice", "unit_price", "unitPrice"),
        "discountAmount": ("discount_amount", "discount_amount", "discountAmount"),
        "taxRate": ("tax1", "tax_rate", "taxRate"), "margin": ("margin", "margin", "margin"),
        "purchaseCost": ("purchase_cost", "purchase_cost", "purchaseCost")}
ITEM_TABLES = {"Quotes": ("quote_item", "quote_id"), "SalesOrder": ("sales_order_item", "sales_order_id"),
               "Act": ("act_item", "act_id"), "Invoice": ("invoice_item", "invoice_id")}
TAX_MODES = ("individual", "group", "group_tax_inc")  # vtigerValueMap: the identity map of taxtype → taxMode
HEADER_TAX = {"Quotes": "vtiger_quotescf", "SalesOrder": "vtiger_salesordercf", "Invoice": "vtiger_invoicecf"}


def _json_dec(path, column="vtiger_data"):
    return f"IFNULL(CAST(JSON_UNQUOTE(JSON_EXTRACT({column}, '$.{path}')) AS DECIMAL(65,30)), 0)"


def tax_source_sql(module, table, key, live, lines):
    """Stage 06.4 tax measures on the restored source (the predicates of source_sql)."""
    implied = "IFNULL(t.total, 0) - IFNULL(t.pre_tax_total, 0) - IFNULL(t.adjustment, 0)"
    out = [(f"{module}.taxMode.{m}.count", f"SELECT COUNT(*) FROM {table} t {live} WHERE t.taxtype = '{m}'")
           for m in TAX_MODES]
    out += [(f"{module}.taxMode.none.count", f"SELECT COUNT(*) FROM {table} t {live} WHERE IFNULL(t.taxtype, '') = ''"),
            (f"{module}.shippingTaxPercent", f"SELECT IFNULL(SUM(t.s_h_percent), 0) FROM {table} t {live}"),
            (f"{module}.impliedTax", f"SELECT IFNULL(SUM({implied}), 0) FROM {table} t {live}"),
            (f"{module}.impliedTax.nonzero", f"SELECT IFNULL(SUM({implied} <> 0), 0) FROM {table} t {live}"),
            (f"{module}.lines.tax2", f"SELECT IFNULL(SUM(l.tax2), 0) {lines}"),
            (f"{module}.lines.tax3", f"SELECT IFNULL(SUM(l.tax3), 0) {lines}"),
            (f"{module}.lines.taxed.count", f"SELECT IFNULL(SUM(IFNULL(l.tax1, 0) + IFNULL(l.tax2, 0) "
                                            f"+ IFNULL(l.tax3, 0) <> 0), 0) {lines}")]
    if module in HEADER_TAX:
        cf = HEADER_TAX[module]
        out.append((f"{module}.headerTax", f"SELECT IFNULL(SUM(c.tax), 0) FROM {table} t {live} "
                                           f"LEFT JOIN {cf} c ON c.{key} = t.{key}"))
    return out


def tax_planned(op, add):
    """The same measures from an operation (a document or an item)."""
    module = op.module
    if op.entityType in ("Quote", "SalesOrder", "Act", "Invoice"):
        mode = op.attributes.get("taxMode")
        add(f"{module}.taxMode.{mode if mode in TAX_MODES else 'none'}.count", 1)
        add(f"{module}.shippingTaxPercent", op.attributes.get("shippingTaxPercent"))
        with localcontext(F.EXACT):
            implied = _dec(op.attributes.get("grandTotal")) - _dec(op.attributes.get("preTaxTotal")) - \
                _dec(op.attributes.get("adjustment"))
        add(f"{module}.impliedTax", implied)
        add(f"{module}.impliedTax.nonzero", 1 if implied != 0 else 0)
        if module in HEADER_TAX:
            add(f"{module}.headerTax", op.vtigerData.get("tax"))
    else:
        tax2, tax3 = _dec(op.vtigerData.get("tax2")), _dec(op.vtigerData.get("tax3"))
        add(f"{module}.lines.tax2", tax2)
        add(f"{module}.lines.tax3", tax3)
        with localcontext(F.EXACT):
            taxed = _dec(op.attributes.get("taxRate")) + tax2 + tax3 != 0
        add(f"{module}.lines.taxed.count", 1 if taxed else 0)


def tax_target_sql(module, where, lines):
    """The same measures on the stand (`where`/`lines`: the FROM … WHERE of target_sql)."""
    implied = "IFNULL(grand_total, 0) - IFNULL(pre_tax_total, 0) - IFNULL(adjustment, 0)"
    out = [(f"{module}.taxMode.{m}.count", f"SELECT COUNT(*) {where} AND tax_mode = '{m}'") for m in TAX_MODES]
    out += [(f"{module}.taxMode.none.count", f"SELECT COUNT(*) {where} AND IFNULL(tax_mode, '') = ''"),
            (f"{module}.shippingTaxPercent", f"SELECT IFNULL(SUM(shipping_tax_percent), 0) {where}"),
            (f"{module}.impliedTax", f"SELECT IFNULL(SUM({implied}), 0) {where}"),
            (f"{module}.impliedTax.nonzero", f"SELECT IFNULL(SUM({implied} <> 0), 0) {where}"),
            (f"{module}.lines.tax2", f"SELECT IFNULL(SUM({_json_dec('tax2')}), 0) {lines}"),
            (f"{module}.lines.tax3", f"SELECT IFNULL(SUM({_json_dec('tax3')}), 0) {lines}"),
            (f"{module}.lines.taxed.count", f"SELECT IFNULL(SUM(IFNULL(tax_rate, 0) + {_json_dec('tax2')} "
                                            f"+ {_json_dec('tax3')} <> 0), 0) {lines}")]
    if module in HEADER_TAX:
        out.append((f"{module}.headerTax", f"SELECT IFNULL(SUM({_json_dec('tax')}), 0) {where}"))
    return out


def _dec(value):
    return Decimal(0) if value in (None, "", "NULL") else Decimal(str(value).strip())


def source_sql():
    """[(measure name, SQL)] on the restored source: one row, one value."""
    out = []
    for module, (table, key, _stand) in DOCUMENT_TABLES.items():
        live = f"JOIN vtiger_crmentity e ON e.crmid = t.{key} AND e.deleted = 0 AND e.setype = '{module}'"
        out.append((f"{module}.count", f"SELECT COUNT(*) FROM {table} t {live}"))
        for name, (col, _s, _a) in HEADER.items():
            out.append((f"{module}.{name}", f"SELECT IFNULL(SUM(t.{col}), 0) FROM {table} t {live}"))
        if module == "Invoice":
            out.append(("Invoice.balanceSource", f"SELECT IFNULL(SUM(t.balance), 0) FROM {table} t {live}"))
        lines = (f"FROM vtiger_inventoryproductrel l JOIN vtiger_crmentity e ON e.crmid = l.id AND e.deleted = 0 "
                 f"AND e.setype = '{module}'")
        out.append((f"{module}.lines.count", f"SELECT COUNT(*) {lines}"))
        for name, (col, _s, _a) in LINE.items():
            out.append((f"{module}.lines.{name}", f"SELECT IFNULL(SUM(l.{col}), 0) {lines}"))
        out.append((f"{module}.lines.amount", "SELECT IFNULL(SUM(l.quantity * l.listprice - IFNULL(l.discount_amount, 0) "
                                              "- l.quantity * l.listprice * IFNULL(l.discount_percent, 0) / 100), 0) "
                                              + lines))
        out += tax_source_sql(module, table, key, live, lines)
    pay = "FROM sp_payments p JOIN vtiger_crmentity e ON e.crmid = p.payid AND e.deleted = 0 AND e.setype = 'SPPayments'"
    for raw, direction in (("Приход", "incoming"), ("Expense", "outgoing")):
        out.append((f"Payment.{direction}.count", f"SELECT COUNT(*) {pay} WHERE p.pay_type = '{raw}'"))
        out.append((f"Payment.{direction}.amount", f"SELECT IFNULL(SUM(p.amount), 0) {pay} WHERE p.pay_type = '{raw}'"))
    for side, where in ALLOCATED.items():
        out.append((f"PaymentAllocation.{side}.count", f"SELECT COUNT(*) {ALLOCATION_FROM} WHERE {where}"))
        out.append((f"PaymentAllocation.{side}.amount", f"SELECT IFNULL(SUM(p.amount), 0) {ALLOCATION_FROM} WHERE {where}"))
    return out


# Allocations of the source in SQL — the rule D-11 (SourceAllocationResolver) written a second time, independently of
# the planner's port: a live incoming payment with a positive amount; its related_to document (live) and its live
# invoice links of vtiger_crmentityrel (both directions, distinct). Allocated: to the sales order of related_to without
# invoice links; to the invoice of related_to with no other link than itself or one other (a conflict); to the single
# linked invoice without related_to. Everything else is unallocated or an error of the plan.
_LINKS = ("SELECT x.{inv} inv, x.{pay} pay FROM vtiger_crmentityrel x "
          "JOIN vtiger_crmentity i ON i.crmid = x.{inv} AND i.deleted = 0 AND i.setype = 'Invoice' "
          "JOIN vtiger_crmentity s ON s.crmid = x.{pay} AND s.deleted = 0 AND s.setype = 'SPPayments' "
          "WHERE x.module = '{m}' AND x.relmodule = '{r}'")
ALLOCATION_FROM = (
    "FROM sp_payments p JOIN vtiger_crmentity e ON e.crmid = p.payid AND e.deleted = 0 AND e.setype = 'SPPayments' "
    "LEFT JOIN vtiger_crmentity r ON r.crmid = p.related_to AND r.deleted = 0 "
    "LEFT JOIN (SELECT pay, COUNT(DISTINCT inv) n, MIN(inv) one FROM ("
    + _LINKS.format(inv="crmid", pay="relcrmid", m="Invoice", r="SPPayments") + " UNION ALL "
    + _LINKS.format(inv="relcrmid", pay="crmid", m="SPPayments", r="Invoice") + ") l GROUP BY pay) k ON k.pay = p.payid")
_INCOMING = "p.pay_type = 'Приход' AND p.amount > 0"
ALLOCATED = {
    "invoice": f"{_INCOMING} AND ((IFNULL(p.related_to, 0) <> 0 AND r.setype = 'Invoice' AND IFNULL(k.n, 0) <= 1) "
               "OR (IFNULL(p.related_to, 0) = 0 AND k.n = 1))",
    "salesOrder": f"{_INCOMING} AND IFNULL(p.related_to, 0) <> 0 AND r.setype = 'SalesOrder' AND k.n IS NULL",
}


def planned(ops, include):
    """The same measures from the operations (values as sent to the writer)."""
    out = {}

    def add(name, value):
        with localcontext(F.EXACT):
            out[name] = out.get(name, Decimal(0)) + _dec(value)

    for op in ops:
        if not include(op):
            continue
        module = op.module
        if op.entityType in ("Quote", "SalesOrder", "Act", "Invoice"):
            add(f"{module}.count", 1)
            for name, (_c, _s, attr) in HEADER.items():
                add(f"{module}.{name}", op.attributes.get(attr))
            if module == "Invoice":
                add("Invoice.balanceSource", op.attributes.get("balanceSource"))
            tax_planned(op, add)
        elif op.entityType in ("QuoteItem", "SalesOrderItem", "ActItem", "InvoiceItem"):
            add(f"{module}.lines.count", 1)
            for name, (_c, _s, attr) in LINE.items():
                add(f"{module}.lines.{name}", op.attributes.get(attr))
            add(f"{module}.lines.amount", op.attributes.get("amount"))
            tax_planned(op, add)
        elif op.entityType == "Payment":
            direction = op.attributes.get("direction")
            add(f"Payment.{direction}.count", 1)
            add(f"Payment.{direction}.amount", op.attributes.get("amount"))
        elif op.entityType == "PaymentAllocation":  # also one that waits for its document (no links yet)
            side = "salesOrder" if op.vtigerData.get("category") == "related_to_salesorder" else "invoice"
            add(f"PaymentAllocation.{side}.count", 1)
            add(f"PaymentAllocation.{side}.amount", op.attributes.get("amount"))
    return out


def target_sql(keys):
    """[(measure name, SQL)] on the stand, for the given source keys of each entity type ({entity: [vtigerId]})."""
    out = []

    def ids(entity):
        values = sorted(int(k) for k in keys.get(entity, ()))
        return ", ".join(str(v) for v in values) or "NULL"

    for module, (_t, _k, stand) in DOCUMENT_TABLES.items():
        entity, item, *_ = F.DOCUMENTS[module]
        where = f"FROM `{stand}` WHERE deleted = 0 AND vtiger_id IN ({ids(entity)})"
        out.append((f"{module}.count", f"SELECT COUNT(*) {where}"))
        for name, (_c, col, _a) in HEADER.items():
            out.append((f"{module}.{name}", f"SELECT IFNULL(SUM({col}), 0) {where}"))
        if module == "Invoice":
            out.append(("Invoice.balanceSource", f"SELECT IFNULL(SUM(balance_source), 0) {where}"))
        table, parent = ITEM_TABLES[module]
        lines = f"FROM `{table}` WHERE deleted = 0 AND vtiger_id IN ({ids(item)})"
        out.append((f"{module}.lines.count", f"SELECT COUNT(*) {lines}"))
        for name, (_c, col, _a) in LINE.items():
            out.append((f"{module}.lines.{name}", f"SELECT IFNULL(SUM({col}), 0) {lines}"))
        out.append((f"{module}.lines.amount", f"SELECT IFNULL(SUM(amount), 0) {lines}"))
        out += tax_target_sql(module, where, lines)
    for direction in ("incoming", "outgoing"):
        where = f"FROM payment WHERE deleted = 0 AND direction = '{direction}' AND vtiger_id IN ({ids('Payment')})"
        out.append((f"Payment.{direction}.count", f"SELECT COUNT(*) {where}"))
        out.append((f"Payment.{direction}.amount", f"SELECT IFNULL(SUM(amount), 0) {where}"))
    for side, col in (("invoice", "invoice_id"), ("salesOrder", "sales_order_id")):
        where = (f"FROM payment_allocation WHERE deleted = 0 AND {col} IS NOT NULL "
                 f"AND vtiger_id IN ({ids('PaymentAllocation')})")
        out.append((f"PaymentAllocation.{side}.count", f"SELECT COUNT(*) {where}"))
        out.append((f"PaymentAllocation.{side}.amount", f"SELECT IFNULL(SUM(amount), 0) {where}"))
    return out


def run(lines_of, queries):
    """Executes [(name, SQL)] with `lines_of(sql) -> [bytes]` (one value per query) → {name: Decimal}."""
    sql = "".join(f"{q};\n" for _n, q in queries)
    values = lines_of(sql)
    if len(values) != len(queries):
        raise ValueError("aggregate queries failed")
    return {name: _dec(v.decode("ascii")) for (name, _q), v in zip(queries, values)}


def compare(left, right, names=None):
    """→ [{measure, left, right, equal}] for the names of `left` (or `names`)."""
    out = []
    for name in sorted(left if names is None else names):
        a, b = left.get(name, Decimal(0)), right.get(name, Decimal(0))
        out.append({"measure": name, "left": str(a), "right": str(b), "equal": a == b})
    return out
