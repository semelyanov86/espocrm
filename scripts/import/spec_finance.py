"""Finance part of the Vtiger import (stage 06.3, docs/migration/import.md «Финансы»; finance-contract §11, §14–§17):
quotes, sales orders, acts and invoices with their line items, payments with their allocation (D-11), the legal entity
and the numbering counters. Pure: no I/O, no values in messages.

Source values are the reference (D-05, D-17): numbers, dates, statuses, totals, item values are carried as they are,
nothing is recalculated; the item `amount` is the exact source net (Line::net of the core, never rounded). The legal
entity of a record and the settlement of the documents are derived by the finance hooks of the stand.
"""
import json
from decimal import Context, Decimal, Inexact, InvalidOperation, Overflow, localcontext

import spec as S
import transforms as T

REGISTRY = json.loads((S.T.REPO / "custom/Espo/Modules/Itvolga/Resources/metadata/app/itvolgaFinance.json")
                      .read_text(encoding="utf-8"))
# module → (document entity, item entity, parent link of the item, base table, number column, status column, status
# value-map key, archive key of the status)
DOCUMENTS = {
    "Quotes": ("Quote", "QuoteItem", "quote", "vtiger_quotes", "quote_no", "quotestage", "Quotes.quotestage"),
    "SalesOrder": ("SalesOrder", "SalesOrderItem", "salesOrder", "vtiger_salesorder", "salesorder_no", "sostatus",
                   "SalesOrder.sostatus"),
    "Act": ("Act", "ActItem", "act", "vtiger_sp_act", "act_no", "sp_actstatus", "Act.sp_actstatus"),
    "Invoice": ("Invoice", "InvoiceItem", "invoice", "vtiger_invoice", "invoice_no", "invoicestatus",
                "Invoice.invoicestatus"),
}
ADDRESS = {"Quotes": ("vtiger_quotesbillads", "vtiger_quotesshipads", "vtiger_quotescf"),
           "SalesOrder": ("vtiger_sobillads", "vtiger_soshipads", "vtiger_salesordercf"),
           "Act": ("vtiger_sp_actbillads", "vtiger_sp_actshipads", None),
           "Invoice": ("vtiger_invoicebillads", "vtiger_invoiceshipads", "vtiger_invoicecf")}
LINE = "vtiger_inventoryproductrel."
# vtiger_modentity_num.semodule → entity type of the numbering series (app.itvolgaFinance)
COUNTER_MODULES = {"Quotes": "Quote", "SalesOrder": "SalesOrder", "Invoice": "Invoice", "Act": "Act",
                   "SPPayments": "Payment"}


def document_rules(module):
    """Column rules of a finance document header (besides vtiger_crmentity)."""
    entity, _item, _link, base, number, status_col, status_key = DOCUMENTS[module]
    bill, ship, cf = ADDRESS[module]
    b = base + "."
    rules = [
        S.Str(b + "subject", "name"), S.Str(b + number, "number"),
        S.Enum(b + status_col, "status", vmap=(entity, "status", status_key), key=status_col),
        S.Enum(b + "taxtype", "taxMode", vmap=(entity, "taxMode", f"{module}.hdnTaxType"), key="taxtype"),
        S.Ref(b + "accountid", "account", accept=("Account",)),
        S.Ref(b + "contactid", "contact", accept=("Contact",)),
        S.Dec(b + "subtotal", "subtotal", scale=8), S.Dec(b + "pre_tax_total", "preTaxTotal", scale=8),
        S.Dec(b + "total", "grandTotal", scale=8), S.Dec(b + "discount_amount", "discountAmount", scale=8),
        S.Num(b + "discount_percent", "discountPercent", scale=3), S.Dec(b + "s_h_amount", "shippingAmount", scale=8),
        S.Num(b + "s_h_percent", "shippingTaxPercent", scale=3), S.Dec(b + "adjustment", "adjustment", scale=8),
        S.Archive(b + "compound_taxes_info", "compound_taxes_info"), S.RegionId(b + "region_id", "region_id"),
        S.Archive(b + "spcompany", "spcompany"),
        S.Address("billingAddress", Street=bill + ".bill_street", City=bill + ".bill_city",
                  State=bill + ".bill_state", PostalCode=bill + ".bill_code", Country=bill + ".bill_country"),
        S.Address("shippingAddress", Street=ship + ".ship_street", City=ship + ".ship_city",
                  State=ship + ".ship_state", PostalCode=ship + ".ship_code", Country=ship + ".ship_country"),
        S.Archive(bill + ".bill_pobox", "bill_pobox"), S.Archive(ship + ".ship_pobox", "ship_pobox"),
    ]
    if cf:
        rules.append(S.Archive(cf + ".tax", "tax", kind="dec"))
    if module != "Act":
        rules.append(S.Text(b + "terms_conditions", "termsAndConditions"))
    if module == "Quotes":
        rules += [S.Ref(b + "potentialid", "opportunity", accept=("Opportunity",)),
                  S.Date(b + "validtill", "dateValidUntil"), UserLink(b + "inventorymanager", "inventoryManager"),
                  S.Archive(b + "carrier", "carrier"), S.Archive(b + "shipping", "shipping")]
    elif module == "SalesOrder":
        r = "vtiger_invoice_recurring_info."
        rules += [S.Ref(b + "potentialid", "opportunity", accept=("Opportunity",)),
                  S.Ref(b + "quoteid", "quote", accept=("Quote",)), S.Date(b + "duedate", "dateDue"),
                  S.Archive(b + "carrier", "carrier"), S.Archive(b + "pending", "pending"),
                  S.Archive(b + "salescommission", "salescommission", kind="dec"),
                  S.Archive(b + "exciseduty", "exciseduty", kind="dec"), S.Archive(b + "fromsite", "fromsite", kind="int"),
                  S.Archive(b + "enable_recurring", "enable_recurring", kind="bool"),
                  S.Archive(r + "recurring_frequency", "recurring_frequency"),
                  S.Archive(r + "start_period", "start_period"), S.Archive(r + "end_period", "end_period"),
                  S.Archive(r + "payment_duration", "payment_duration"),
                  S.Archive(r + "invoice_status", "recurring_invoice_status")]
    elif module == "Invoice":
        rules += [S.Ref(b + "potential_id", "opportunity", accept=("Opportunity",)),
                  S.Ref(b + "salesorderid", "salesOrder", accept=("SalesOrder",)),
                  S.Ref(b + "sp_act_id", "act", accept=("Act",)),
                  S.Date(b + "invoicedate", "dateInvoiced"), S.Date(b + "duedate", "dateDue"),
                  S.Dec(b + "balance", "balanceSource", scale=8), S.Archive(b + "customerno", "customerno"),
                  S.Archive(b + "purchaseorder", "purchaseorder"),
                  S.Archive(b + "exciseduty", "exciseduty", kind="dec"),
                  S.Archive(b + "salescommission", "salescommission", kind="dec"),
                  S.Archive(b + "received", "received", kind="dec")]
    elif module == "Act":
        rules += [S.Date(b + "actdate", "dateAct")]
    return rules + [S.Currency(b + "currency_id", "currency")]  # last: it reads the money attributes set above


class UserLink(S.Rule):
    def apply(self, op, row, ctx):
        S.user_ref(op, ctx, self.cols[0], self.attr, self.value(row))


def build_document(module, row, ctx):
    entity, _item, _link, base, *_ = DOCUMENTS[module]
    op = S.Op(entity, int(row["vtiger_crmentity.crmid"]), module)
    S.crmentity(op, row, ctx)
    for rule in document_rules(module):
        rule.apply(op, row, ctx)
    return op


def line_rules():
    return [S.Text(LINE + "comment", "description"), S.Num(LINE + "quantity", "quantity", scale=3),
            S.Dec(LINE + "listprice", "unitPrice", scale=8), S.Dec(LINE + "discount_amount", "discountAmount", scale=8),
            S.Num(LINE + "discount_percent", "discountPercent", scale=3), S.Num(LINE + "tax1", "taxRate", scale=3),
            S.Dec(LINE + "purchase_cost", "purchaseCost", scale=8), S.Dec(LINE + "margin", "margin", scale=8),
            S.Archive(LINE + "tax2", "tax2", kind="dec"), S.Archive(LINE + "tax3", "tax3", kind="dec")]


def build_item(module, row, ctx):
    """A line of vtiger_inventoryproductrel → <Doc>Item (lineitem_id is its key): source values, the exact net as
    `amount` (no column in the source; Line::net of the core), the product name of the line as `name`."""
    entity, item, link, *_ = DOCUMENTS[module]
    op = S.Op(item, int(row[LINE + "lineitem_id"]), module)
    op.column(LINE + "lineitem_id", "carried", "vtigerId")
    op.links[link] = [entity, int(row[LINE + "id"])]
    op.column(LINE + "id", "linked", f"{link}Id")
    S._set(op, LINE + "sequence_no", "order", T.integer(row.get(LINE + "sequence_no")))
    raw = row.get(LINE + "productid")
    S.link_ref(op, ctx, LINE + "productid", "product", raw, accept=("Product",))
    # the product name at the time of the save, as DocumentProcessor names an item (also when products wait, --only)
    op.attributes["name"] = ctx.product_names.get(int(raw)) if raw and raw.strip().isdigit() else None
    for rule in line_rules():
        rule.apply(op, row, ctx)
    op.attributes.update(amount=exact_net(row), amountCurrency="RUB")
    return op


# Exact decimal arithmetic: the operands are DECIMAL columns (at most 65 digits), the products fit; a rounding would
# raise instead of passing silently (the default context keeps 28 digits).
EXACT = Context(prec=200, traps=[Inexact, InvalidOperation, Overflow])


def exact_net(row):
    """net = quantity × price − discount amount − quantity × price × discount percent / 100 (finance-contract §4):
    exact; more than 8 decimals would not fit the column and is an error, never rounded."""
    def dec(col):
        raw = row.get(LINE + col)
        return Decimal(0) if T.is_empty(raw) else Decimal(raw.strip())

    with localcontext(EXACT):
        gross = dec("quantity") * dec("listprice")
        net = gross - dec("discount_amount") - gross * dec("discount_percent").scaleb(-2)
        if net.scaleb(8) != net.scaleb(8).to_integral_value():  # never signals: the scale is checked, not rounded
            raise T.TransformError("amount_scale")
        return format(net.quantize(Decimal("1e-8")), "f")


# --- payments and the allocation (D-11) --------------------------------------------------------------

def payment_rules():
    p, cf = "sp_payments.", "sp_paymentscf."
    return [
        S.Str(p + "pay_no", "number"), S.Date(p + "pay_date", "datePaid"), S.Str(p + "pay_details", "purpose"),
        S.Enum(p + "pay_type", "direction", vmap=("Payment", "direction", "SPPayments.pay_type"), key="pay_type"),
        S.Enum(p + "type_payment", "method", vmap=("Payment", "method", "SPPayments.type_payment"), key="type_payment"),
        S.Enum(p + "spstatus", "status", vmap=("Payment", "status", "SPPayments.spstatus"), key="spstatus"),
        S.Dec(p + "amount", "amount", scale=8), S.DocNo(p + "doc_no", "documentNumber"),
        S.Archive(p + "spcompany", "spcompany"), S.Archive(p + "debit", "debit"),
        S.Archive(p + "coracc_subacc", "coracc_subacc"), S.Archive(p + "analytics_code", "analytics_code"),
        S.Archive(p + "target_code", "target_code"),
        S.Str(cf + "cf_1198", "counterpartyAccount"), S.Str(cf + "cf_1200", "counterpartyBic"),
        S.Str(cf + "cf_1202", "counterpartyBankName"), S.Str(cf + "cf_1204", "bankTransactionId"),
        S.Bool(cf + "cf_1380", "isForeignCurrencyAccount"),
        S.Ref(p + "payer", "payer", accept=("Account", "Contact", "Vendor")),
    ]


def build_payment(module, row, ctx):
    op = S.Op("Payment", int(row["vtiger_crmentity.crmid"]), "SPPayments")
    S.crmentity(op, row, ctx)
    for rule in payment_rules():
        rule.apply(op, row, ctx)
    return op


def resolve_allocation(payment, row, links, ctx):
    """SourceAllocationResolver (D-11, Q-36) on a source payment, ported verbatim (parity with the PHP core is tested,
    the category counts are reconciled with the audit's SQL split): → (category, decision, target, conflicts)."""
    direction = payment.attributes.get("direction")
    amount = Decimal(payment.attributes.get("amount") or "0")
    related = row.get("sp_payments.related_to")
    related_id = 0 if T.is_empty(related) else int(related)
    links = sorted(set(links))
    if related_id:
        setype, deleted = ctx.crm.get(related_id, ("", True))
        if deleted or setype not in ("Invoice", "SalesOrder"):
            return "other", "unresolved", None, [], "related_to_not_document"
        if direction == "outgoing":
            return "other", "unresolved", (setype, related_id), [], "outgoing_with_related_to"
        if setype == "SalesOrder":
            if links:
                return "other", "unresolved", (setype, related_id), [], "salesorder_and_invoice_link"
            return allocate("related_to_salesorder", amount, setype, related_id)
        if not links:
            return allocate("related_to_invoice_only", amount, setype, related_id)
        if links == [related_id]:
            return allocate("both_same_invoice", amount, setype, related_id)
        if len(links) > 1:
            return "other", "unresolved", (setype, related_id), [], "several_invoice_links"
        return allocate("conflict_rel_other_invoice", amount, setype, related_id, links)
    if not links:
        return "unallocated", "none", None, [], None
    if len(links) > 1:
        return "other", "unresolved", ("Invoice", links[0]), [], "several_invoice_links"
    if direction == "outgoing":
        return "rel_only", "none", ("Invoice", links[0]), [], "outgoing_relation_only"
    return allocate("rel_only", amount, "Invoice", links[0])


def allocate(category, amount, setype, target, conflicts=()):
    if amount <= 0:
        return category, "unresolved", (setype, target), [], "zero_payment"
    return category, "allocate", (setype, target), list(conflicts), None


SOURCE_OF = {"both_same_invoice": "relatedTo", "related_to_invoice_only": "relatedTo",
             "related_to_salesorder": "relatedTo", "conflict_rel_other_invoice": "relatedTo",
             "rel_only": "relationLink"}


def build_allocation(payment, row, links, ctx):
    """The allocation of a source payment (at most one: the source never splits payments), keyed by the payid, plus the
    outcomes of related_to and of the Invoice↔payment rows of vtiger_crmentityrel."""
    category, decision, target, conflicts, reason = resolve_allocation(payment, row, links, ctx)
    ctx.flags[f"allocation:{category}:{decision}"] += 1
    col = "sp_payments.related_to"
    rel = "crmentityrel:Invoice->SPPayments"
    related = row.get(col)
    has_related = not (T.is_empty(related) or related.strip() == "0")
    if not T.is_empty(related) and not has_related:
        payment.column(col, "zero_empty")  # 0 = no related record
    if decision == "unresolved":
        if has_related:
            payment.column(col, f"error:allocation_{reason}")
        for _ in links:
            payment.relation(rel, f"error:allocation_{reason}")
        return None
    if decision == "none":
        if has_related:
            payment.column(col, "error:allocation_unexpected")
        if links:  # Q-36: an outgoing payment linked to a customer invoice only through the related list
            key = payment.archive("invoiceLinks", sorted(set(links)))
            for _ in links:
                payment.relation(rel, "no_target", key)
        return None
    setype, target_id = target
    status, resolved = ctx.target(target_id)
    entity_link = {"Invoice": "invoice", "SalesOrder": "salesOrder"}[setype]
    op = S.Op("PaymentAllocation", payment.vtigerId, "SPPayments")
    op.links["payment"] = ["Payment", payment.vtigerId]
    op.vtigerData["category"] = category
    if status != "ok":  # the document is not part of this run (--only): the allocation waits for it
        outcome = "deferred" if status == "deferred" else f"error:target_{status}"
        op.pending, op.skip = ("deferred", None) if status == "deferred" else (None, outcome)
        if has_related:
            op.column(col, outcome)
        for _ in links:
            op.relation(rel, outcome)
        return op
    op.links["invoice"] = list(resolved) if setype == "Invoice" else None
    op.links["salesOrder"] = list(resolved) if setype == "SalesOrder" else None
    op.attributes.update(amount=payment.attributes["amount"], amountCurrency="RUB", source=SOURCE_OF[category],
                         sourceConflict=category == "conflict_rel_other_invoice")
    if has_related:
        op.column(col, "linked", f"{entity_link}Id")
    for link in links:
        if category == "conflict_rel_other_invoice":
            op.relation(rel, "conflict", op.archive("conflictInvoiceIds", sorted(set(conflicts))))
        elif category == "both_same_invoice":
            op.relation(rel, "duplicate", f"{entity_link}Id")
        else:
            op.relation(rel, "linked", f"{entity_link}Id")
    return op


# --- legal entity and counters -------------------------------------------------------------------------

def legal_entity_rules():
    o = "vtiger_organizationdetails."
    rules = [S.Str(o + c, a) for c, a in (
        ("organizationname", "name"), ("city", "addressCity"), ("state", "addressState"),
        ("country", "addressCountry"), ("code", "addressPostalCode"), ("phone", "phoneNumber"), ("fax", "fax"),
        ("website", "website"), ("inn", "inn"), ("kpp", "kpp"), ("okpo", "okpo"), ("bankaccount", "bankAccount"),
        ("bankname", "bankName"), ("bankid", "bic"), ("corraccount", "corrAccount"), ("director", "director"),
        ("bookkeeper", "bookkeeper"), ("entrepreneur", "entrepreneur"),
        ("entrepreneurreg", "entrepreneurRegistration"))]
    return rules + [S.Text(o + "address", "addressStreet")]


def build_legal_entity(row, ctx):
    """The single legal entity (D-04, D-48): requisites of vtiger_organizationdetails onto the record of
    itvolga-setup-finance (key `Default`); the logo is a file (an Attachment operation)."""
    o = "vtiger_organizationdetails."
    company = row.get(o + "company")
    op = S.Op("LegalEntity", "Default", "OrganizationDetails")
    if T.is_empty(company) or company.strip() != "Default":
        op.skip = "error:legal_entity_key"
        op.column(o + "company", "error:legal_entity_key")
        return op
    op.column(o + "company", "carried", "vtigerCompanyKey")
    for rule in legal_entity_rules():
        rule.apply(op, row, ctx)
    return op


def counters(data):
    """→ ({entity type: next number}, problems): vtiger_modentity_num.cur_id of the active series of the finance modules
    (owner's answer 2026-10-11: raised, never lowered); the prefix must be the one of the registry."""
    out, problems = {}, []
    prefixes = {**{k: v["numberPrefix"] for k, v in REGISTRY["documents"].items()},
                **{k: v["numberPrefix"] for k, v in REGISTRY["payments"].items()}}
    for row in data.get("modentity_num", []):
        entity = COUNTER_MODULES.get(row["semodule"])
        if entity is None or row["active"] != "1":
            continue
        if (row["prefix"] or "") != prefixes[entity]:
            problems.append(f"counter_prefix:{entity}")
            continue
        out[entity] = max(out.get(entity, 0), int(row["cur_id"]))
    return out, problems
