"""The Vtiger call history (stage 07.2, D-173, docs/migration/import.md «История звонков»): PBXManager → Call by the
same importer as every Vtiger module (key `vtigerId` = pbxmanagerid, source wins, the 06.4 delta), SPCallPopup merged
into the call of its `callid`. Pure (no I/O, no values in messages).

- Internal calls (a customer number of three digits — an extension; owner's answer 2026-10-17) are not imported: the
  record is held `excluded:internal_call`, every value of it, of its popup and of their relations is counted
  `not_applicable:internal_call`.
- The recording URL of the dead connector (127.0.0.1:5000) is only the archive mark `cLegacyRecordingUrl` (D-10): the
  call has no playable recording. `sourceuuid` is the connector's id (`cConnectorCallId`), never an Asterisk key.
- Times: Berlin until 2020-10-22 inclusive, then the D-30 epochs (transforms.pbx_datetime). `Call.duration` is computed
  by EspoCRM from the dates: `totalduration` is `derived_equal` or archived (vtigerData.totalduration).
- Clients: `customer` → the parent (a contact or lead also in contacts/leads); empty or deleted → the exact matches of
  the number among the live contacts, accounts and leads of the source (D-167 rules: transforms.canonical_phone, the
  parent as Core/ParentChooser) — deterministic, owned by the import and compared by the check pass.
- SPCallPopup (1:1): a «carrier» operation with the call's key holds the popup's outcomes (module SPCallPopup); its
  values that differ from the call's go to vtigerData.popup_<column>, its comment is appended to the description.
"""
import json
import re
from collections import defaultdict

import spec as S
import transforms as T

P, POP, E = "vtiger_pbxmanager.", "vtiger_sp_callpopup.", "vtiger_crmentity."
INTERNAL = re.compile(r"^\s*[0-9]{3}\s*$")
EXCLUDED = "excluded:internal_call"
NOT_APPLICABLE = "not_applicable:internal_call"
LOOKUP_LIMIT = 100
# crmentityrel pairs of the call history (relations.csv): the popup's pair with its call, contacts and leads of calls
CALL_PAIRS = {("PBXManager", "SPCallPopup"), ("SPCallPopup", "PBXManager"), ("Contacts", "PBXManager"),
              ("Leads", "PBXManager"), ("Contacts", "SPCallPopup"), ("Leads", "SPCallPopup"),
              ("SPCallPopup", "Contacts"), ("SPCallPopup", "Leads")}
CLIENT_TYPES = {"Contacts": "Contact", "Accounts": "Account", "Leads": "Lead"}
POPUP_SAME = {"smownerid": "assignedUserId", "smcreatorid": "createdById", "modifiedby": "modifiedById",
              "createdtime": "createdAt", "modifiedtime": "modifiedAt", "description": "description"}
POPUP_ARCHIVE = ("firstname", "lastname", "client_type", "accountname", "call_no")
_LABELS = {}


def label(key):
    """The installation's Russian label of the live integration (i18n ru_RU/Call.json labels): one name scheme."""
    if not _LABELS:
        path = T.REPO / "custom/Espo/Modules/Itvolga/Resources/i18n/ru_RU/Call.json"
        _LABELS.update(json.loads(path.read_text(encoding="utf-8"))["labels"])
    return _LABELS[key]


def is_internal(row):
    return INTERNAL.match(row.get(P + "customernumber") or "") is not None


# --- clients by number ---------------------------------------------------------------------------------------------

def client_index(data, area):
    """Canonical number → [(module, crmid)] of the live contacts, accounts and leads of the source (all phone columns)."""
    index = defaultdict(list)
    for module in CLIENT_TYPES:
        for row in data.get(module, []):
            crmid = int(row["vtiger_crmentity.crmid"])
            for col, _type, _key in S.PHONE_COLUMNS[module]:
                number = T.canonical_phone(row.get(col), area)
                if number is not None and (module, crmid) not in index[number]:
                    index[number].append((module, crmid))
    return index


def choose_parent(accounts, contacts, leads):
    """Port of Core/ParentChooser: the single account (matched accounts and the accounts of matched contacts), else the
    single contact, else the single lead when no contact matched."""
    pool = sorted(set(accounts) | {a for a in contacts.values() if a})
    if len(pool) == 1:
        return "Account", pool[0]
    if len(contacts) == 1:
        return "Contact", next(iter(contacts))
    if not contacts and len(set(leads)) == 1:
        return "Lead", leads[0]
    return None


def lookup_clients(op, number, ctx):
    """The exact clients of the number → contacts/leads items and the parent; a list cut by the limit picks no parent.
    A client — or the account of a matched contact — outside this run (--only) defers the whole choice: the stored
    parent and items stay (a choice from part of the clients would differ from the full run's; external review
    2026-10-17)."""
    matches = ctx.telephony["index"].get(number, []) if number else []
    complete = len(matches) <= LOOKUP_LIMIT
    live = []
    for module, crmid in matches[:LOOKUP_LIMIT]:
        status = ctx.target(crmid)[0]
        account = ctx.contact_account.get(crmid) if module == "Contacts" and status == "ok" else None
        account_status = ctx.target(account)[0] if account else None
        if "deferred" in (status, account_status):
            op.keep.add("parent")
            ctx.flags["pbx_lookup:deferred"] += 1
            return
        if status == "ok":
            live.append((module, crmid, account if account_status == "ok" else None))
    contacts, accounts, leads = {}, [], []
    for module, crmid, account in live:
        if module == "Contacts":
            contacts[crmid] = account
            op.add_item("contacts", ["Contact", crmid, {"status": "None"}])
        elif module == "Leads":
            leads.append(crmid)
            op.add_item("leads", ["Lead", crmid, {"status": "None"}])
        else:
            accounts.append(crmid)
    parent = choose_parent(accounts, contacts, leads) if complete else None
    op.links["parent"] = [{"Account": "Account", "Contact": "Contact", "Lead": "Lead"}[parent[0]], parent[1]] \
        if parent else None
    ctx.flags["pbx_lookup:" + ("parent" if parent else "matches" if matches else "none")] += 1


# --- the call --------------------------------------------------------------------------------------------------------

def build_call(module, row, ctx):
    op = S.Op("Call", int(row[E + "crmid"]), "PBXManager")
    S.crmentity(op, row, ctx)
    S.Enum(P + "direction", "direction", vmap=("Call", "direction", "PBXManager.direction"), key="direction").apply(
        op, row, ctx)
    raw = row.get(P + "callstatus")
    status = ctx.maps.lookup("Call", "status", "PBXManager.callstatus", raw) if not T.is_empty(raw) else None
    op.attributes.update(status=status, cCallStatusRaw=T.string(raw))
    if status is not None:
        op.column(P + "callstatus", "mapped", "status", "cCallStatusRaw")
    start = T.pbx_datetime(row.get(P + "starttime"), ctx.flags)
    end = T.pbx_datetime(row.get(P + "endtime"), ctx.flags)
    for col, value in (("starttime", start), ("endtime", end)):
        if value is not None:
            op.column(P + col, "carried", "dateStart" if col == "starttime" else "dateEnd")
    if end is None:
        end = start  # D-43: Call.dateEnd is required; the source had none
        if start:
            op.archive("dateEndMissing", True)
    op.attributes.update(dateStart=start, dateEnd=end)
    total = row.get(P + "totalduration")
    if not T.is_empty(total):
        computed = int((T.local_datetime(end) - T.local_datetime(start)).total_seconds()) if start and end else None
        if computed is not None and T.integer(total) == computed:
            op.column(P + "totalduration", "derived_equal", "dateEnd")
        else:
            op.column(P + "totalduration", "archived", op.archive("totalduration", T.integer(total)))
    S.Int(P + "billduration", "cBillDuration").apply(op, row, ctx)
    for col, attr in (("recordingurl", "cLegacyRecordingUrl"), ("sourceuuid", "cConnectorCallId"),
                      ("incominglinename", "cIncomingLine")):
        S.Str(P + col, attr).apply(op, row, ctx)
    number_raw = row.get(P + "customernumber")
    canonical = T.canonical_phone(number_raw, ctx.telephony["area"])
    stored = canonical or T.string(number_raw)
    op.attributes["cPhoneNumber"] = stored
    if stored is not None:
        if stored == number_raw:
            op.column(P + "customernumber", "carried", "cPhoneNumber")
        else:
            op.column(P + "customernumber", "normalized", "cPhoneNumber", op.archive("customernumber", number_raw))
    direction = "Incoming call" if op.attributes.get("direction") == "Inbound" else "Outgoing call"
    op.attributes["name"] = f"{label(direction)} {stored or label('Hidden number')}"[:255]
    user, owner = row.get(P + "user"), row.get(E + "smownerid")
    if not T.is_empty(user):
        if user.strip() == (owner or "").strip():
            op.column(P + "user", "duplicate", "assignedUserId")
        else:
            op.column(P + "user", "archived", op.archive("user", user))
    customer = row.get(P + "customer")
    target = S.link_ref(op, ctx, P + "customer", "parent", customer, accept=("Account", "Contact", "Lead"))
    if target is not None:
        link = {"Contact": "contacts", "Lead": "leads"}.get(target[0])
        if link:
            op.add_item(link, list(target) + [{"status": "None"}])
    elif "parent" not in op.keep and not is_internal(row):
        lookup_clients(op, canonical, ctx)
    if "parent" in op.keep:  # a kept parent is not a link of the operation (the check pass would see it cleared)
        op.links.pop("parent", None)
    else:
        op.links.setdefault("parent", None)
    if is_internal(row):
        exclude(op)
    return op


def exclude(op):
    op.skip = EXCLUDED
    op.outcomes = [(kind, key, NOT_APPLICABLE, ()) for kind, key, _outcome, _attrs in op.outcomes]


def merge_popup(call, row, pbx_row, ctx):
    """The carrier of a popup: its outcomes under SPCallPopup, its values on the call's operation."""
    carrier = S.Op("Call", int(row[E + "crmid"]), "SPCallPopup", name_override=call.key)
    carrier.column(POP + "callid", "linked", "vtigerId")
    for col, attr in POPUP_SAME.items():
        value = row.get(E + col)
        if T.is_empty(value):
            continue
        if (value or "") == (pbx_row.get(E + col) or ""):
            carrier.column(E + col, "duplicate", attr)
        else:
            carrier.column(E + col, "archived", call.archive(f"popup_{col}", value))
    comment = T.text(row.get(POP + "comment"))
    if comment is not None:
        call.attributes["description"] = "\n\n".join(v for v in (call.attributes.get("description"), comment) if v)
        carrier.column(POP + "comment", "carried", "description")
    for col in POPUP_ARCHIVE:
        value = row.get(POP + col)
        if not T.is_empty(value):
            carrier.column(POP + col, "archived", call.archive(f"popup_{col}", value))
    if call.skip == EXCLUDED:
        exclude(carrier)
    elif call.skip:
        carrier.skip = "owner_skipped"  # the call is held (an error): its popup waits with it
    return carrier


def build(data, ctx):
    """→ (call operations, popup carriers). A popup without a live call of its `callid` is an error (held)."""
    pbx_rows = {int(r[E + "crmid"]): r for r in data.get("PBXManager", [])}
    ops = {crmid: S.record_or_error("PBXManager", r, ctx, build_call) for crmid, r in sorted(pbx_rows.items())}
    carriers = {}
    for row in S._crm_sorted(data.get("SPCallPopup", [])):
        popup = int(row[E + "crmid"])
        callid = T.integer(row.get(POP + "callid"))
        call = ops.get(callid)
        if call is None:
            carrier = S.Op("Call", popup, "SPCallPopup")
            carrier.skip = "error:popup_without_call"
            carrier.column(POP + "callid", "dangling:missing")
        else:
            carrier = merge_popup(call, row, pbx_rows[callid], ctx)
        carriers[popup] = carrier
    ctx.telephony["calls"], ctx.telephony["carriers"] = ops, carriers
    return list(ops.values()), list(carriers.values())


def call_pair(ctx, rel, a_id, a_mod, b_id, b_mod):
    """A crmentityrel row of the call history: the popup's own pair (duplicate of `callid`), or a contact/lead of the
    call (an attendee item)."""
    calls, carriers = ctx.telephony.get("calls", {}), ctx.telephony.get("carriers", {})
    if {a_mod, b_mod} == {"PBXManager", "SPCallPopup"}:
        pbx, popup = (a_id, b_id) if a_mod == "PBXManager" else (b_id, a_id)
        carrier, call = carriers.get(popup), calls.get(pbx)
        holder = carrier or call
        if holder is None:
            ctx.flags[f"deferred_rel:{rel}"] += 1
            return
        if holder.skip == EXCLUDED:
            holder.relation(rel, NOT_APPLICABLE)
        elif carrier is not None and carrier.name_override == f"Call:{pbx}":
            carrier.relation(rel, "duplicate", "vtigerId")
        else:
            holder.relation(rel, "conflict", holder.archive("popupCallAlternatives", [pbx, popup]))
        return
    if a_mod in CLIENT_TYPES:
        client, record, record_mod = a_id, b_id, b_mod
    else:
        client, record, record_mod = b_id, a_id, a_mod
    if record_mod == "PBXManager":
        call = calls.get(record)
    else:
        carrier = carriers.get(record)
        call = calls.get(int(carrier.name_override.split(":")[1])) if carrier and carrier.name_override else None
    if call is None:
        ctx.flags[f"deferred_rel:{rel}"] += 1
        return
    if call.skip == EXCLUDED:
        call.relation(rel, NOT_APPLICABLE)
        return
    status, target = ctx.target(client)
    link = {"Contact": "contacts", "Lead": "leads"}.get(target[0]) if status == "ok" else None
    if status == "ok" and link is None:
        call.relation(rel, "no_target")
    elif status == "ok":
        item = list(target) + [{"status": "None"}]
        if item in call.linkMultiple.get(link, {}).get("items", []):
            call.relation(rel, "duplicate", link)
        else:
            S.multi_item(call, ctx, rel, link, status, target, columns={"status": "None"})
    else:
        S.multi_item(call, ctx, rel, "contacts", status, target)


def consumed_columns():
    out = {("PBXManager", P + c) for c in ("direction", "callstatus", "starttime", "endtime", "totalduration",
                                           "billduration", "recordingurl", "sourceuuid", "incominglinename",
                                           "customernumber", "user", "customer")}
    out |= {("PBXManager", E + c) for c in ("smownerid", "smcreatorid", "modifiedby", "createdtime", "modifiedtime",
                                            "description")}
    out |= {("SPCallPopup", POP + c) for c in ("callid", "comment", *POPUP_ARCHIVE)}
    out |= {("SPCallPopup", E + c) for c in POPUP_SAME}
    return out
