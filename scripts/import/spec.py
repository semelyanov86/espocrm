"""Mapping of the Vtiger import, stage 06.2 (docs/migration/import.md): which source rows become which EspoCRM records,
how every consumed column is transformed, and what happened to every non-empty value (outcomes for the private
reconciliation). Pure: no I/O, no stand, no values in messages.

The specification is bound to the generated maps (docs/migration/field-map.csv, relations.csv) by `check_coverage`:
every in-scope column with a transfer fate must be consumed by a rule, every rule must consume a mapped column, every
in-scope relation must be handled, pending for a later stage or excluded by its fate.

An operation is the desired state of one target record (owner's rules 2026-10-11): attributes owned by the import are
always sent (null when empty: no EspoCRM defaults, D-38); a single link to a record of a later stage is not sent (left
as it is), to a deleted or missing source record it is sent as null; link-multiple items are added (manual links stay),
except the domains `teams` (Vtiger groups) and `roles` (the four Vtiger roles), which follow the source.
"""
import csv
import datetime as dt
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import transforms as T

# --- scope ---------------------------------------------------------------------------------------

SCOPE = ("Users", "Accounts", "Contacts", "Leads", "Potentials", "Calendar", "Events", "HelpDesk", "ModComments",
         "Project", "ProjectTask")
# Target entity of a live source record of each setype (activities: by activitytype).
ENTITY_BY_SETYPE = {"Accounts": "Account", "Contacts": "Contact", "Leads": "Lead", "Potentials": "Opportunity",
                    "HelpDesk": "Case", "Project": "Project", "ProjectTask": "ProjectTask", "ModComments": "Note"}
ACTIVITY_ENTITY = {"Task": "Task", "Call": "Call", "Meeting": "Meeting", "Письмо": "Task"}
# Modules imported by later stages (owner's answer 2026-10-11): references to them wait for that stage.
PENDING = {**{m: "06.3" for m in ("Faq", "Documents", "Emails", "Invoice", "Quotes", "SalesOrder", "Act", "SPPayments",
                                  "Products", "Services", "Vendors", "Consignment", "ServiceContracts", "Assets",
                                  "Jivosite", "JVmes", "PurchaseOrder")},
           "PBXManager": "07.2", "SPCallPopup": "07.2"}
# Target entity types each source module fills (inventory of the target: records gone from the source).
MODULE_ENTITIES = {"Users": ("User",), "Accounts": ("Account",), "Contacts": ("Contact", "ContactAccess"),
                   "Leads": ("Lead",), "Potentials": ("Opportunity",), "Project": ("Project",),
                   "ProjectTask": ("ProjectTask",), "HelpDesk": ("Case",), "Calendar": ("Task",),
                   "Events": ("Call", "Meeting", "Task"), "ModComments": ("Note",)}
# Import order: a reference always points to an entity type imported earlier in the run.
ORDER = ("User", "Account", "Contact", "ContactAccess", "Lead", "Opportunity", "Project", "ProjectTask", "Case",
         "Task", "Call", "Meeting", "Note")
ROLES = {"H2": "Директор", "H3": "Заместитель директора", "H4": "Менеджер по продажам", "H10": "Менеджер клиентов"}
GROUP_TEAMS = ("Отдел Поддержки", "Отдел Маркетинга", "Отдел Продаж")  # app.itvolgaAcl.groupTeams
EFFECTIVE_ADMIN = 1          # D-39: only user#1 is an administrator in Vtiger
SYNTHETIC_KEY_MIN = 900_000_000  # vtigerId block of the stand tests; the real import refuses such source keys
TRANSFER_FATES = ("перенос", "архив", "переносится как связь")
# Filled source columns the generated map has no row for, consumed by a rule anyway (reason in import.md):
# ModComments does not declare `modifiedby` in vtiger_field, so the audit has no module row for it.
MAP_GAPS = {("ModComments", "vtiger_crmentity.modifiedby"): "Note.modifiedBy"}
NO_VTIGER_DATA = {"ContactAccess"}  # model.md: the access record keeps no source archive (D-42)
ACCESS_COLUMNS = ("cf_1322", "cf_1324", "cf_1326", "cf_1328")  # D-06/D-42: values never leave the pipe
# Source columns never read into the import process (secrets of users and staff data excluded by the owner).
FORBIDDEN = {"vtiger_users": {"user_password", "confirm_password", "user_hash", "accesskey", "crypt_type",
                              "phone_home", "address_street", "address_city", "address_state", "address_country",
                              "address_postalcode", "user_preferences"}}


@dataclass(frozen=True)
class Source:
    """Live rows of a module: vtiger_crmentity (deleted=0, setype) + the base table + one-to-one tables."""
    module: str
    base: tuple
    joins: tuple = ()
    setype: str = None
    where: str = ""

    def tables(self):
        return ("vtiger_crmentity", self.base[0], *(t for t, _ in self.joins))

    def from_sql(self):
        t, k = self.base
        sql = f"FROM vtiger_crmentity JOIN `{t}` ON `{t}`.`{k}` = vtiger_crmentity.crmid"
        for jt, jk in self.joins:
            sql += f" LEFT JOIN `{jt}` ON `{jt}`.`{jk}` = vtiger_crmentity.crmid"
        return sql + f" WHERE vtiger_crmentity.deleted = 0 AND vtiger_crmentity.setype = '{self.setype or self.module}'" \
            + self.where


SOURCES = {
    "Accounts": Source("Accounts", ("vtiger_account", "accountid"),
                       (("vtiger_accountscf", "accountid"), ("vtiger_accountbillads", "accountaddressid"),
                        ("vtiger_accountshipads", "accountaddressid"))),
    "Contacts": Source("Contacts", ("vtiger_contactdetails", "contactid"),
                       (("vtiger_contactaddress", "contactaddressid"), ("vtiger_contactsubdetails", "contactsubscriptionid"),
                        ("vtiger_contactscf", "contactid"), ("vtiger_customerdetails", "customerid"))),
    "Leads": Source("Leads", ("vtiger_leaddetails", "leadid"),
                    (("vtiger_leadaddress", "leadaddressid"), ("vtiger_leadsubdetails", "leadsubscriptionid"),
                     ("vtiger_leadscf", "leadid"))),
    "Potentials": Source("Potentials", ("vtiger_potential", "potentialid")),
    "HelpDesk": Source("HelpDesk", ("vtiger_troubletickets", "ticketid"), (("vtiger_ticketcf", "ticketid"),)),
    "Project": Source("Project", ("vtiger_project", "projectid")),
    "ProjectTask": Source("ProjectTask", ("vtiger_projecttask", "projecttaskid"), (("vtiger_projecttaskcf", "projecttaskid"),)),
    "ModComments": Source("ModComments", ("vtiger_modcomments", "modcommentsid"), (("vtiger_modcommentscf", "modcommentsid"),)),
    "Calendar": Source("Calendar", ("vtiger_activity", "activityid"), setype="Calendar",
                       where=" AND `vtiger_activity`.activitytype = 'Task'"),
    "Events": Source("Events", ("vtiger_activity", "activityid"), setype="Calendar",
                     where=" AND `vtiger_activity`.activitytype NOT IN ('Task', 'Emails')"),
}
# Plain tables read whole (no crmentity): users and the link tables.
TABLES = ("vtiger_users", "vtiger_user2role", "vtiger_users2group", "vtiger_groups", "vtiger_crmentityrel",
          "vtiger_contpotentialrel", "vtiger_seactivityrel", "vtiger_cntactivityrel", "vtiger_salesmanactivityrel",
          "vtiger_freetagged_objects", "vtiger_freetags", "vtiger_senotesrel", "vtiger_seattachmentsrel")


# --- operation under construction ----------------------------------------------------------------

@dataclass
class Op:
    entityType: str
    vtigerId: int
    module: str
    attributes: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)
    linkMultiple: dict = field(default_factory=dict)
    emails: list = None
    phones: list = None
    secret: dict = None
    preferences: dict = None
    user: dict = None
    keyAlsoIn: list = None
    onlyIfExists: bool = False
    vtigerData: dict = field(default_factory=dict)
    outcomes: list = field(default_factory=list)   # (kind 'f'|'r', key, outcome, verify attrs)
    keep: set = field(default_factory=set)          # single links left untouched (target of a later stage, deferred)
    pending: str = None                             # the whole record waits for a stage (comment on a FAQ)
    skip: str = None                                # the record is not imported (reason code)

    @property
    def key(self):
        return f"{self.entityType}:{self.vtigerId}"

    def column(self, col, outcome, *attrs):
        self.outcomes.append(("f", col, outcome, attrs))

    def relation(self, rel, outcome, *attrs):
        self.outcomes.append(("r", rel, outcome, attrs))

    def archive(self, key, value):
        self.vtigerData[key] = value
        return f"vtigerData.{key}"

    def add_item(self, link, item, domain=None):
        lm = self.linkMultiple.setdefault(link, {"items": []})
        if item not in lm["items"]:
            lm["items"].append(item)
        if domain is not None:
            lm["domain"] = domain

    def payload(self):
        """The operation sent to the writer. vtigerData is owned as a whole: its keys are the source facts kept."""
        attributes = dict(self.attributes)
        if self.entityType not in NO_VTIGER_DATA:
            attributes["vtigerData"] = dict(sorted(self.vtigerData.items())) or None
        data = {"key": self.key, "entityType": self.entityType, "vtigerId": self.vtigerId, "attributes": attributes,
                "links": self.links, "linkMultiple": self.linkMultiple}
        for name in ("emails", "phones", "secret", "preferences", "user", "keyAlsoIn"):
            if getattr(self, name) is not None:
                data[name] = getattr(self, name)
        if self.onlyIfExists:
            data["onlyIfExists"] = True
        return data


class Context:
    """Everything a builder needs besides its own row: the reference resolver, users, groups, value maps, flags."""

    def __init__(self, data, selected=None, key_range=(1, SYNTHETIC_KEY_MIN - 1), effective_admin=EFFECTIVE_ADMIN):
        self.data = data
        self.effective_admin = effective_admin
        self.maps = T.ValueMaps()
        self.selected = set(selected or SCOPE)
        self.key_range = key_range
        self.flags = Counter()          # dst gaps/folds, phone classes, conflicts — counts only
        self.crm = data["crm"]          # crmid → (setype, deleted)
        self.activity_type = data["activity_type"]
        self.users = {int(r["vtiger_users.id"]): r for r in data["vtiger_users"]}  # live users only (source.load)
        self.groups = {int(r["vtiger_groups.groupid"]): r["vtiger_groups.groupname"] for r in data["vtiger_groups"]}
        self.phone_types = {}           # number → type of its first owner (EspoCRM keeps the type on the shared row)

    def dt(self, value):
        return T.vt_datetime(value, self.flags)

    def target(self, crmid):
        """→ (status, (entityType, vtigerId) | stage | None) for a crmid referenced by a source row."""
        if crmid is None or str(crmid).strip(" ") in ("", "0"):
            return "zero", None
        try:
            crmid = int(crmid)
        except ValueError:
            return "dangling:not_a_key", None
        if crmid not in self.crm:
            return "dangling:missing", None
        setype, deleted = self.crm[crmid]
        if deleted:
            return "dangling:deleted", None
        if setype == "Calendar":
            atype = self.activity_type.get(crmid)
            if atype == "Emails":
                return "pending", PENDING["Emails"]
            module = "Calendar" if atype == "Task" else "Events"
            entity = ACTIVITY_ENTITY.get(atype)
        else:
            module, entity = setype, ENTITY_BY_SETYPE.get(setype)
        if setype in PENDING:
            return "pending", PENDING[setype]
        if module not in SCOPE or entity is None:
            return "error:unexpected_target", None
        if module not in self.selected:
            return "deferred", None
        return "ok", (entity, crmid)


# --- rules ---------------------------------------------------------------------------------------

def _set(op, col, attr, value, outcome="carried"):
    op.attributes[attr] = value
    if value is not None:
        op.column(col, outcome, attr)


class Rule:
    """A column rule: `cols` consumed (table.column); `apply(op, row, ctx)` sets the desired state and outcomes."""
    cols = ()

    def __init__(self, col, attr=None, **kw):
        self.cols = (col,)
        self.attr = attr
        self.kw = kw

    def value(self, row):
        return row.get(self.cols[0])


class Str(Rule):
    def apply(self, op, row, ctx):
        _set(op, self.cols[0], self.attr, T.string(self.value(row)))


class Text(Rule):
    def apply(self, op, row, ctx):
        _set(op, self.cols[0], self.attr, T.text(self.value(row)))


class Int(Rule):
    def apply(self, op, row, ctx):
        raw = self.value(row)
        value = T.integer(raw, self.kw.get("zero_empty", False))
        _set(op, self.cols[0], self.attr, value)
        if value is None and not T.is_empty(raw):
            op.column(self.cols[0], "zero_empty")


class Dec(Rule):
    def apply(self, op, row, ctx):
        raw = self.value(row)
        value = T.decimal(raw, self.kw["scale"], self.kw.get("zero_empty", False))
        _set(op, self.cols[0], self.attr, value)
        op.attributes[self.attr + "Currency"] = "RUB" if value is not None else None
        if value is None and not T.is_empty(raw):
            op.column(self.cols[0], "zero_empty")


class Date(Rule):
    def apply(self, op, row, ctx):
        _set(op, self.cols[0], self.attr, T.date_only(self.value(row)))


class Bool(Rule):
    """Checkbox: '1'/'0' are both values (false is a fact); NULL → false (the field is not nullable)."""

    def apply(self, op, row, ctx):
        value = T.checkbox(self.value(row))
        op.attributes[self.attr] = bool(value)
        if not T.is_empty(self.value(row)):
            op.column(self.cols[0], "carried", self.attr)


class Enum(Rule):
    """Value dictionary D-38; a replaced source value is kept in vtigerData under `key` (D-19)."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        entity, fld, source_key = self.kw["vmap"]
        value = ctx.maps.lookup(entity, fld, source_key, raw) if not T.is_empty(raw) else None
        op.attributes[self.attr] = value
        if value is None:
            if not T.is_empty(raw):  # the dictionary maps it to an empty value: the source is kept
                op.column(self.cols[0], "mapped", self.attr, op.archive(self.kw["key"], raw))
            return
        if value != raw:
            op.column(self.cols[0], "mapped", self.attr, op.archive(self.kw["key"], raw))
        else:
            op.column(self.cols[0], "carried", self.attr)


class Archive(Rule):
    """Non-empty source value without a working field → vtigerData.<key> (D-08): text as is, checkbox as bool."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        if T.is_empty(raw):
            return
        kind = self.kw.get("kind", "text")
        if kind == "bool":
            value = T.checkbox(raw)
        elif kind in ("int", "dec"):
            if T.decimal(raw, 8, zero_is_empty=True) is None:
                op.column(self.cols[0], "zero_empty")
                return
            value = raw.strip()
        else:
            value = raw
        op.column(self.cols[0], "archived", op.archive(self.attr, value))


class Pending(Rule):
    def apply(self, op, row, ctx):
        if not T.is_empty(self.value(row)):
            op.column(self.cols[0], "pending:" + self.attr)


class NotApplicable(Rule):
    """A transfer-fate column whose value has no per-record target (e.g. the currency of a single-currency
    installation, D-37). Counted with its reason; nothing is written."""

    def apply(self, op, row, ctx):
        if not T.is_empty(self.value(row)):
            op.column(self.cols[0], "not_applicable:" + self.attr)


class Phones(Rule):
    """Phone columns of a record → phoneNumberData (owner's rule 2026-10-11): unambiguous numbers normalised to
    E.164, others kept; a changed value keeps its source string in vtigerData. The type lives on the shared
    PhoneNumber row: the first owner (import order) fixes it, a later owner with another type keeps its source
    column in vtigerData (counted as a type conflict)."""

    def __init__(self, *spec):
        self.spec = spec  # (col, type, vtigerData key)
        self.cols = tuple(c for c, _, _ in spec)

    def apply(self, op, row, ctx):
        phones = []
        for col, ptype, key in self.spec:
            raw = row.get(col)
            number, cls = T.phone(raw)
            if number is None:
                continue
            ctx.flags[f"phone_{cls}"] += 1
            attrs = ["phoneNumberData"]
            outcome = "carried" if number == raw else "normalized"
            if number != raw:
                attrs.append(op.archive(key, raw))
            if any(p["phoneNumber"] == number for p in phones):
                ctx.flags["phone_duplicate_in_record"] += 1
                op.column(col, "duplicate", op.archive(key, raw))
                continue
            shared = ctx.phone_types.setdefault(number, ptype)
            if shared != ptype:
                ctx.flags["phone_type_conflict"] += 1
                attrs.append(op.archive(key, raw))
                outcome = "type_conflict"
            phones.append({"phoneNumber": number, "type": shared, "primary": not phones})
            op.column(col, outcome, *attrs)
        op.phones = phones


class Emails(Rule):
    """E-mail columns (first non-empty = primary) → emailAddressData; lower-cased, the source kept if it differed."""

    def __init__(self, *spec):
        self.spec = spec  # (col, vtigerData key)
        self.cols = tuple(c for c, _ in spec)

    def apply(self, op, row, ctx):
        emails = []
        for col, key in self.spec:
            raw = row.get(col)
            address = T.email(raw)
            if address is None:
                continue
            if any(e["emailAddress"] == address for e in emails):
                op.column(col, "duplicate", op.archive(key, raw))
                continue
            attrs = ["emailAddressData"]
            if address != raw:
                attrs.append(op.archive(key, raw))
            emails.append({"emailAddress": address, "primary": not emails})
            op.column(col, "carried" if address == raw else "normalized", *attrs)
        op.emails = emails


class Address(Rule):
    def __init__(self, prefix, **parts):
        self.prefix, self.parts = prefix, parts   # part (Street, City, ...) → column
        self.cols = tuple(parts.values())

    def apply(self, op, row, ctx):
        for part, col in self.parts.items():
            _set(op, col, f"{self.prefix}{part}", T.text(row.get(col)) if part == "Street" else T.string(row.get(col)))


class Ref(Rule):
    """A belongsTo link by source crmid (`attr` = link name)."""

    def apply(self, op, row, ctx):
        link_ref(op, ctx, self.cols[0], self.attr, row.get(self.cols[0]), kind="f",
                 accept=self.kw.get("accept"), also=self.kw.get("also"))


def link_ref(op, ctx, key, link, crmid, kind="f", accept=None, also=None):
    """Set link `link` from a source crmid and record the outcome under `key`. `accept` limits target entity types
    (another type → the source id goes to vtigerData); `also` adds the target to a link-multiple too."""
    status, target = ctx.target(crmid)
    record = op.column if kind == "f" else op.relation
    if status == "zero":
        if key and kind == "f" and crmid is not None and str(crmid).strip(" ") != "":
            record(key, "zero_empty")
        op.links.setdefault(link, None)
        return None
    if status == "ok" and accept and target[0] not in accept:
        record(key, "no_target", op.archive(f"{link}SourceId", int(crmid)))
        op.links.setdefault(link, None)
        return None
    if status == "ok":
        op.links[link] = list(target)
        attrs = [f"{link}Id"]
        if also:
            op.add_item(also, list(target))
            attrs.append(also)
        record(key, "linked", *attrs)
        return target
    if status == "pending":
        record(key, f"pending:{target}")
        op.keep.add(link)
        return None
    if status == "deferred":
        record(key, "deferred")
        op.keep.add(link)
        return None
    record(key, status)
    if status.startswith("dangling"):
        op.links[link] = None
    return None


# --- common vtiger_crmentity rules ------------------------------------------------------------------

def crmentity(op, row, ctx, owner=True, description=True):
    e = "vtiger_crmentity."
    if owner:
        owner_ref(op, ctx, row.get(e + "smownerid"))
    user_ref(op, ctx, e + "smcreatorid", "createdBy", row.get(e + "smcreatorid"))
    user_ref(op, ctx, e + "modifiedby", "modifiedBy", row.get(e + "modifiedby"))
    _set(op, e + "createdtime", "createdAt", ctx.dt(row.get(e + "createdtime")))
    _set(op, e + "modifiedtime", "modifiedAt", ctx.dt(row.get(e + "modifiedtime")))
    if description:
        _set(op, e + "description", "description", T.text(row.get(e + "description")))


def user_ref(op, ctx, col, link, value):
    if T.is_empty(value) or int(value) == 0:
        op.links[link] = None
        if not T.is_empty(value):
            op.column(col, "zero_empty")
        return
    uid = int(value)
    if uid in ctx.users:
        op.links[link] = ["User", uid]
        op.column(col, "linked", f"{link}Id")
    else:
        op.links[link] = None
        op.column(col, "dangling:not_a_user")


def owner_ref(op, ctx, value):
    """smownerid: a user → assignedUser; a Vtiger group → its team, no assigned user (D-08, module-decisions)."""
    col = "vtiger_crmentity.smownerid"
    oid = int(value) if not T.is_empty(value) else 0
    op.linkMultiple["teams"] = {"items": [], "domain": [["Team", t] for t in GROUP_TEAMS]}
    if oid in ctx.users:
        op.links["assignedUser"] = ["User", oid]
        op.column(col, "linked", "assignedUserId")
    elif oid in ctx.groups and ctx.groups[oid] in GROUP_TEAMS:
        op.links["assignedUser"] = None
        op.linkMultiple["teams"]["items"].append(["Team", ctx.groups[oid]])
        op.column(col, "linked", "teams", "assignedUserId")
    else:
        op.links["assignedUser"] = None
        op.column(col, "error:owner_unknown")


# --- entity builders -----------------------------------------------------------------------------

def rules_of(module):
    """Column rules of a module (besides vtiger_crmentity). Kept as data to be checked against field-map.csv."""
    a, c, l, p = "vtiger_account.", "vtiger_contactdetails.", "vtiger_leaddetails.", "vtiger_potential."
    if module == "Accounts":
        return [
            Str(a + "accountname", "name"), Str(a + "account_no", "vtigerNo"), Str(a + "website", "website"),
            Phones((a + "phone", "Office", "phone"), (a + "otherphone", "Other", "otherphone"), (a + "fax", "Fax", "fax")),
            Str(a + "tickersymbol", "cShortName"), Int(a + "employees", "cEmployees", zero_empty=True),
            Emails((a + "email1", "email1"), (a + "email2", "email2")),
            Archive(a + "ownership", "ownership"),
            Enum(a + "industry", "industry", vmap=("Account", "industry", "Accounts.industry"), key="industry"),
            Enum(a + "rating", "cRating", vmap=("Account", "cRating", "Accounts.rating"), key="rating"),
            Enum(a + "account_type", "type", vmap=("Account", "type", "Accounts.accounttype"), key="accounttype"),
            Str(a + "siccode", "sicCode"), Str(a + "inn", "cInn"), Str(a + "kpp", "cKpp"),
            Str("vtiger_accountscf.vk_url", "cVkUrl"), Archive(a + "isconvertedfromlead", "isconvertedfromlead", kind="bool"),
            Address("billingAddress", Street="vtiger_accountbillads.bill_street", City="vtiger_accountbillads.bill_city",
                    State="vtiger_accountbillads.bill_state", PostalCode="vtiger_accountbillads.bill_code",
                    Country="vtiger_accountbillads.bill_country"),
            Address("shippingAddress", Street="vtiger_accountshipads.ship_street", City="vtiger_accountshipads.ship_city",
                    State="vtiger_accountshipads.ship_state", PostalCode="vtiger_accountshipads.ship_code",
                    Country="vtiger_accountshipads.ship_country"),
            Archive("vtiger_accountshipads.ship_pobox", "ship_pobox"),
            Str("vtiger_accountscf.cf_1109", "cBankAccount"), Str("vtiger_accountscf.cf_1111", "cBankName"),
            Str("vtiger_accountscf.cf_1113", "cCorrAccount"), Str("vtiger_accountscf.cf_1115", "cBic"),
        ]
    if module == "Contacts":
        s, cf, ad = "vtiger_contactsubdetails.", "vtiger_contactscf.", "vtiger_contactaddress."
        return [
            Salutation(c + "salutation", "salutationName", entity="Contact"),
            Str(c + "firstname", "firstName"), Str(c + "contact_no", "vtigerNo"), Str(c + "lastname", "lastName"),
            Phones((c + "phone", "Office", "phone"), (c + "mobile", "Mobile", "mobile"), (s + "homephone", "Home", "homephone"),
                   (s + "otherphone", "Other", "otherphone"), (c + "fax", "Fax", "fax")),
            Enum(s + "leadsource", "cLeadSource", vmap=("Lead", "source", "Contacts.leadsource"), key="leadsource"),
            ContactTitle(c + "title", "title"),
            Str(c + "department", "cDepartment"),
            Emails((c + "email", "email"), (c + "secondaryemail", "secondaryemail")),
            Date(s + "birthday", "cBirthday"), Str(cf + "vk_url", "cVkUrl"),
            Archive(c + "isconvertedfromlead", "isconvertedfromlead", kind="bool"),
            Archive("vtiger_customerdetails.portal", "portal", kind="bool"),
            Date("vtiger_customerdetails.support_start_date", "cSupportStartDate"),
            Date("vtiger_customerdetails.support_end_date", "cSupportEndDate"),
            Bool(cf + "cf_1372", "cNeedOriginalDocs"), Bool(cf + "cf_1374", "cSendNews"),
            Bool(cf + "cf_1376", "cPartnerAds"), Bool(cf + "cf_1378", "cSendAlerts"),
            Address("address", Street=ad + "mailingstreet", City=ad + "mailingcity", State=ad + "mailingstate",
                    PostalCode=ad + "mailingzip", Country=ad + "mailingcountry"),
            Address("cOtherAddress", Street=ad + "otherstreet", City=ad + "othercity", State=ad + "otherstate",
                    PostalCode=ad + "otherzip", Country=ad + "othercountry"),
            Pending(c + "imagename", "06.3"),
        ]
    if module == "Leads":
        a2, s2, cf = "vtiger_leadaddress.", "vtiger_leadsubdetails.", "vtiger_leadscf."
        return [
            Salutation(l + "salutation", "salutationName", entity="Lead"),
            Str(l + "firstname", "firstName"), Str(l + "lead_no", "vtigerNo"), Str(l + "lastname", "lastName"),
            Phones((a2 + "phone", "Office", "phone"), (a2 + "mobile", "Mobile", "mobile"), (a2 + "fax", "Fax", "fax")),
            Str(l + "company", "accountName"), Str(l + "designation", "title"),
            Enum(l + "leadsource", "source", vmap=("Lead", "source", "Leads.leadsource"), key="leadsource"),
            Emails((l + "email", "email"), (l + "secondaryemail", "secondaryemail")),
            Enum(l + "industry", "industry", vmap=("Account", "industry", "Leads.industry"), key="industry"),
            Str(s2 + "website", "website"),
            Archive(l + "annualrevenue", "annualrevenue", kind="dec"), Archive(l + "noofemployees", "noofemployees", kind="int"),
            LeadStatus(l + "leadstatus", "status"),
            Enum(l + "rating", "cRating", vmap=("Account", "cRating", "Leads.rating"), key="rating"),
            Str(cf + "vk_url", "cVkUrl"),
            Enum(cf + "cf_1107", "cPriority", vmap=("Lead", "cPriority", "Leads.cf_1107"), key="cf_1107"),
            Int(cf + "cf_1165", "cJivositeId"),
            Address("address", Street=a2 + "lane", City=a2 + "city", State=a2 + "state", PostalCode=a2 + "code",
                    Country=a2 + "country"),
        ]
    if module == "Potentials":
        return [
            Str(p + "potentialname", "name"), Str(p + "potential_no", "vtigerNo"),
            Ref(p + "related_to", "account", accept=("Account",)),
            Ref(p + "contact_id", "contact", accept=("Contact",), also="contacts"),
            Dec(p + "amount", "amount", scale=8),
            Enum(p + "potentialtype", "cOpportunityType", vmap=("Opportunity", "cOpportunityType", "Potentials.opportunity_type"),
                 key="opportunity_type"),
            Date(p + "closingdate", "closeDate"),
            Enum(p + "leadsource", "leadSource", vmap=("Lead", "source", "Potentials.leadsource"), key="leadsource"),
            Archive(p + "nextstep", "nextstep"),
            Enum(p + "sales_stage", "stage", vmap=("Opportunity", "stage", "Potentials.sales_stage"), key="sales_stage"),
            Probability(p + "probability", "probability"),
            Archive(p + "isconvertedfromlead", "isconvertedfromlead", kind="bool"),
            Archive(p + "spcompany", "spcompany"), Archive(p + "converted", "converted", kind="bool"),
        ]
    if module == "HelpDesk":
        t = "vtiger_troubletickets."
        return [
            Str(t + "title", "name"), Ref(t + "parent_id", "account", accept=("Account",)),
            Ref(t + "contact_id", "contact", accept=("Contact",), also="contacts"),
            Archive(t + "product_id", "product_id"),
            Enum(t + "priority", "priority", vmap=("Case", "priority", "HelpDesk.ticketpriorities"), key="ticketpriorities"),
            Enum(t + "status", "status", vmap=("Case", "status", "HelpDesk.ticketstatus"), key="ticketstatus"),
            Enum(t + "severity", "cSeverity", vmap=("Case", "cSeverity", "HelpDesk.ticketseverities"), key="ticketseverities"),
            Archive(t + "hours", "hours", kind="dec"),
            Enum(t + "category", "type", vmap=("Case", "type", "HelpDesk.ticketcategories"), key="ticketcategories"),
            Archive(t + "days", "days", kind="dec"), Str(t + "ticket_no", "vtigerNo"), Text(t + "solution", "cSolution"),
        ]
    if module == "Project":
        j = "vtiger_project."
        return [
            Str(j + "projectname", "name"), Str(j + "project_no", "vtigerNo"), Date(j + "startdate", "dateStart"),
            Date(j + "targetenddate", "dateEndPlanned"), Date(j + "actualenddate", "dateEnd"),
            Enum(j + "projectstatus", "status", vmap=("Project", "status", "Project.projectstatus"), key="projectstatus"),
            Enum(j + "projecttype", "type", vmap=("Project", "type", "Project.projecttype"), key="projecttype"),
            Ref(j + "linktoaccountscontacts", "account", accept=("Account",)),
            Archive(j + "isconvertedfrompotential", "isconvertedfrompotential", kind="bool"),
            Ref(j + "potentialid", "opportunity", accept=("Opportunity",)),
            Budget(j + "targetbudget", "budget"), Str(j + "projecturl", "url"),
            Enum(j + "projectpriority", "priority", vmap=("Project", "priority", "Project.projectpriority"),
                 key="projectpriority"),
            Enum(j + "progress", "progress", vmap=("Project", "progress", "Project.progress"), key="progress"),
        ]
    if module == "ProjectTask":
        j = "vtiger_projecttask."
        return [
            Str(j + "projecttaskname", "name"), Str(j + "projecttask_no", "vtigerNo"),
            Enum(j + "projecttaskpriority", "priority", vmap=("ProjectTask", "priority", "ProjectTask.projecttaskpriority"),
                 key="projecttaskpriority"),
            Enum(j + "projecttasktype", "type", vmap=("ProjectTask", "type", "ProjectTask.projecttasktype"),
                 key="projecttasktype"),
            Int(j + "projecttasknumber", "orderNumber"), Ref(j + "projectid", "project", accept=("Project",)),
            Enum(j + "projecttaskstatus", "status", vmap=("ProjectTask", "status", "ProjectTask.projecttaskstatus"),
                 key="projecttaskstatus"),
            Bool("vtiger_projecttaskcf.cf_1354", "showInStat"),
            Enum(j + "projecttaskprogress", "progress", vmap=("ProjectTask", "progress", "ProjectTask.projecttaskprogress"),
                 key="projecttaskprogress"),
            Int(j + "projecttaskhours", "hours"), Date(j + "startdate", "dateStart"), Date(j + "enddate", "dateEnd"),
            Str("vtiger_projecttaskcf.cf_1320", "gitCommit"),
        ]
    return []


class Salutation(Rule):
    """Only the standard salutations are an enum value; other text stays in vtigerData.salutationtype."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        op.attributes[self.attr] = None
        if T.is_empty(raw):
            return
        try:
            value = ctx.maps.lookup(self.kw["entity"], "salutationName", "(picklist)", raw)
        except T.TransformError:
            value = None
        if value:
            op.attributes[self.attr] = value
            op.column(self.cols[0], "carried", self.attr)
        else:
            op.column(self.cols[0], "archived", op.archive("salutationtype", raw))


class LeadStatus(Rule):
    """leadstatus by the dictionary; converted=1 → Converted (D-38), the replaced status kept in vtigerData."""

    def __init__(self, col, attr):
        super().__init__(col, attr)
        self.cols = (col, "vtiger_leaddetails.converted")

    def apply(self, op, row, ctx):
        raw, converted = row.get(self.cols[0]), row.get(self.cols[1])
        value = ctx.maps.lookup("Lead", "status", "Leads.leadstatus", raw) if not T.is_empty(raw) else None
        if converted is not None and converted.strip() == "1":
            op.column(self.cols[1], "mapped", "status")
            if not T.is_empty(raw):
                op.column(self.cols[0], "archived", op.archive("leadstatus", raw))
            value = ctx.maps.lookup("Lead", "status", "Leads.converted", "1")
        elif not T.is_empty(raw):
            if value != raw:
                op.column(self.cols[0], "mapped", "status", op.archive("leadstatus", raw))
            else:
                op.column(self.cols[0], "carried", "status")
        if converted is not None and converted.strip() == "0":
            op.column(self.cols[1], "zero_empty")
        op.attributes["status"] = value
        op.attributes["convertedAt"] = None  # unknown in Vtiger: never the import time (Lead\ConvertedAt hook)


class Probability(Rule):
    """decimal(7,3) percent → int; a fractional value would be a loss and is refused."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        value = T.decimal(raw, 0) if not T.is_empty(raw) else None
        _set(op, self.cols[0], self.attr, int(value) if value is not None else None)


class Budget(Rule):
    """varchar target budget → decimal(25,2); a non-numeric value stays in vtigerData.targetbudget."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        op.attributes["budget"] = op.attributes["budgetCurrency"] = None
        if T.is_empty(raw):
            return
        try:
            value = T.decimal(raw.replace(" ", "").replace(",", "."), 2)
        except T.TransformError:
            op.column(self.cols[0], "archived", op.archive("targetbudget", raw))
            return
        op.attributes.update(budget=value, budgetCurrency="RUB")
        op.column(self.cols[0], "carried" if value == raw else "normalized", "budget",
                  *([] if value == raw else [op.archive("targetbudget", raw)]))


class ContactTitle(Rule):
    """Contact.title is the role of the primary account link in EspoCRM: without an account it has no place and
    stays in vtigerData.title."""

    def apply(self, op, row, ctx):
        raw = T.string(self.value(row))
        if raw is None:
            op.attributes["title"] = None
            return
        if op.links.get("account"):
            op.attributes["title"] = raw
            op.column(self.cols[0], "carried", "title")
        else:
            op.attributes["title"] = None
            op.column(self.cols[0], "no_target", op.archive("title", raw))


# --- builders --------------------------------------------------------------------------------------

def build_record(module, row, ctx):
    entity = ENTITY_BY_SETYPE[module]
    op = Op(entity, int(row["vtiger_crmentity.crmid"]), module)
    crmentity(op, row, ctx)
    if module == "Contacts":  # the account first: the title rule depends on it
        link_ref(op, ctx, "vtiger_contactdetails.accountid", "account", row.get("vtiger_contactdetails.accountid"),
                 accept=("Account",), also="accounts")
    for rule in rules_of(module):
        rule.apply(op, row, ctx)
    return op


def build_contact_access(row, ctx):
    """ContactAccess (D-06/D-42): vtigerId = the contact's crmid; created only when an access field is non-empty;
    values only in the operation (never in outcomes, vtigerData or messages)."""
    cf = "vtiger_contactscf."
    values = {c: row.get(cf + c) for c in ACCESS_COLUMNS}
    op = Op("ContactAccess", int(row["vtiger_crmentity.crmid"]), "Contacts")
    op.links["contact"] = ["Contact", op.vtigerId]
    owner_ref(op, ctx, row.get("vtiger_crmentity.smownerid"))
    user_ref(op, ctx, "vtiger_crmentity.smcreatorid", "createdBy", row.get("vtiger_crmentity.smcreatorid"))
    op.outcomes = []  # owner and author are the contact's; accounted on the contact
    op.attributes["createdAt"] = ctx.dt(row.get("vtiger_crmentity.createdtime"))
    op.attributes.update(
        anydeskId=T.string(values["cf_1322"]), hostname=T.string(values["cf_1326"]), ipAddress=T.string(values["cf_1328"]))
    op.secret = {"anydeskPassword": None if T.is_empty(values["cf_1324"]) else values["cf_1324"]}
    for c, attr in (("cf_1322", "anydeskId"), ("cf_1324", "secret.anydeskPassword"), ("cf_1326", "hostname"),
                    ("cf_1328", "ipAddress")):
        if not T.is_empty(values[c]):
            op.column(cf + c, "protected", attr)
    if not any(not T.is_empty(v) for v in values.values()):
        op.onlyIfExists = True  # source wins: clears an access record that exists, never creates an empty one
    return op


def build_activity(module, row, ctx):
    a = "vtiger_activity."
    atype = row[a + "activitytype"]
    entity = ACTIVITY_ENTITY.get(atype)
    if entity is None:
        op = Op("Task", int(row["vtiger_crmentity.crmid"]), module)
        op.skip = "error:unknown_activitytype"
        return op
    op = Op(entity, int(row["vtiger_crmentity.crmid"]), module)
    op.keyAlsoIn = [e for e in ("Task", "Call", "Meeting") if e != entity]
    crmentity(op, row, ctx)
    op.attributes["name"] = T.string(row.get(a + "subject"))
    if op.attributes["name"] is not None:
        op.column(a + "subject", "carried", "name")
    start = T.combine(row.get(a + "date_start"), row.get(a + "time_start"))
    start_utc = T.to_utc(start, ctx.flags)
    status_key = "Calendar.taskstatus" if module == "Calendar" else "Events.eventstatus"
    raw_status = row.get(a + ("status" if module == "Calendar" else "eventstatus"))
    status = ctx.maps.lookup(entity, "status", status_key, raw_status) if not T.is_empty(raw_status) else None
    status_col = a + ("status" if module == "Calendar" else "eventstatus")
    op.attributes["status"] = status
    if status is not None:
        if status != raw_status:
            op.column(status_col, "mapped", "status", op.archive("eventstatus" if module == "Events" else "taskstatus",
                                                                 raw_status))
        else:
            op.column(status_col, "carried", "status")
    date_cols = (a + "date_start", a + "time_start")
    if entity == "Task":
        op.attributes.update(dateStart=start_utc, dateStartDate=None, dateCompleted=None)
        if module == "Calendar":
            due = T.date_only(row.get(a + "due_date"))
            op.attributes.update(dateEnd=T.all_day_end(due), dateEndDate=due)  # the deadline is a date (all-day end)
            if due:
                op.column(a + "due_date", "carried", "dateEndDate")
            prio = row.get(a + "priority")
            op.attributes["priority"] = ctx.maps.lookup("Task", "priority", "Calendar.taskpriority", prio) \
                if not T.is_empty(prio) else None
            if not T.is_empty(prio):
                pv = op.attributes["priority"]
                op.column(a + "priority", "mapped" if pv != prio else "carried", "priority",
                          *([op.archive("taskpriority", prio)] if pv != prio else []))
        else:
            end = T.to_utc(T.combine(row.get(a + "due_date"), row.get(a + "time_end")), ctx.flags)
            op.attributes.update(dateEnd=end, dateEndDate=None, priority=None, cTaskType="Письмо")
            for col in (a + "due_date", a + "time_end"):
                if not T.is_empty(row.get(col)) and end:
                    op.column(col, "carried", "dateEnd")
            op.column(a + "activitytype", "mapped", "cTaskType")
            duration(op, row, ctx, start, end)
    else:
        end = T.to_utc(T.combine(row.get(a + "due_date"), row.get(a + "time_end")), ctx.flags)
        if entity == "Call" and end is None:
            end = start_utc   # D-43: Call.dateEnd is required
            if start_utc:
                op.archive("dateEndMissing", True)
        op.attributes.update(dateStart=start_utc, dateEnd=end)
        if entity == "Meeting":
            op.attributes.update(dateStartDate=None, dateEndDate=None, isAllDay=False)
        for col in (a + "due_date", a + "time_end"):
            if not T.is_empty(row.get(col)) and end:
                op.column(col, "carried", "dateEnd")
        op.column(a + "activitytype", "carried", "entityType")
        duration(op, row, ctx, start, end)
    if module == "Events":
        prio = row.get(a + "priority")
        if not T.is_empty(prio):
            op.column(a + "priority", "archived", op.archive("taskpriority", prio))
    for col in date_cols:
        if not T.is_empty(row.get(col)) and start_utc:
            op.column(col, "carried", "dateStart")
    for date_col, time_col in ((a + "date_start", a + "time_start"), (a + "due_date", a + "time_end")):
        # a time without its date (or the reverse) has no place in a datetime: kept as a source fact
        if T.is_empty(row.get(date_col)) != T.is_empty(row.get(time_col)) and time_col in row:
            lone = time_col if T.is_empty(row.get(date_col)) else date_col
            if not any(k == lone for _, k, _, _ in op.outcomes):
                op.column(lone, "archived", op.archive(lone.split(".")[1], row[lone]))
    if module == "Calendar":
        op.column(a + "activitytype", "carried", "entityType")
    return op


def duration(op, row, ctx, start_local, end_utc):
    """Call/Meeting duration is computed by EspoCRM from the dates; Vtiger hours+minutes are kept only when they
    disagree with the dates."""
    a = "vtiger_activity."
    hours, minutes = row.get(a + "duration_hours"), row.get(a + "duration_minutes")
    if T.is_empty(hours) and T.is_empty(minutes):
        return
    start_utc = T.to_utc(start_local)
    try:
        source = int(hours or 0) * 3600 + int(minutes or 0) * 60
    except ValueError:
        source = None
    computed = None
    if start_utc and end_utc:
        computed = (dt.datetime.fromisoformat(end_utc) - dt.datetime.fromisoformat(start_utc)).total_seconds()
    for col, raw in ((a + "duration_hours", hours), (a + "duration_minutes", minutes)):
        if T.is_empty(raw):
            continue
        if computed is not None and source == computed:
            op.column(col, "derived_equal", "dateEnd")
        else:
            op.column(col, "archived", op.archive(col.split(".")[1], raw))


def build_user(row, ctx):
    u = "vtiger_users."
    uid = int(row[u + "id"])
    op = Op("User", uid, "Users")
    is_admin = uid == ctx.effective_admin and row.get(u + "is_admin") == "on"
    op.user = {"adopt": uid == ctx.effective_admin}
    _set(op, u + "user_name", "userName", T.string(row.get(u + "user_name")))
    op.attributes["type"] = "admin" if is_admin else "regular"
    op.column(u + "is_admin", "mapped", "type")
    for col, attr in (("first_name", "firstName"), ("last_name", "lastName"), ("title", "title"),
                      ("phone_crm_extension", "cPhoneExtension")):
        _set(op, u + col, attr, T.string(row.get(u + col)))
    status = row.get(u + "status")
    op.attributes["isActive"] = status == "Active"
    op.column(u + "status", "mapped", "isActive")
    _set(op, u + "date_entered", "createdAt", T.utc_timestamp(row.get(u + "date_entered")))
    Emails((u + "email1", "email1")).apply(op, row, ctx)
    Phones((u + "phone_work", "Office", "phone_work"), (u + "phone_mobile", "Mobile", "phone_mobile")).apply(op, row, ctx)
    if not T.is_empty(row.get(u + "department")):
        op.column(u + "department", "archived", op.archive("department", row[u + "department"]))
    prefs = {}
    lang = row.get(u + "language")
    if not T.is_empty(lang):
        prefs["language"] = lang[:2].lower() + "_" + lang[3:].upper() if len(lang) == 5 else lang
        op.column(u + "language", "mapped", "preferences.language")
    for col, key, table in (("date_format", "dateFormat", {"dd-mm-yyyy": "DD.MM.YYYY", "mm-dd-yyyy": "MM/DD/YYYY",
                                                           "yyyy-mm-dd": "YYYY-MM-DD", "dd.mm.yyyy": "DD.MM.YYYY",
                                                           "dd/mm/yyyy": "DD/MM/YYYY"}),
                            ("hour_format", "timeFormat", {"24": "HH:mm", "12": "hh:mm a"}),
                            ("dayoftheweek", "weekStart", {d: i for i, d in enumerate(
                                ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"))})):
        raw = row.get(u + col)
        if T.is_empty(raw):
            continue
        if raw not in table:
            raise T.TransformError(f"unmapped_{col}")
        prefs[key] = table[raw]
        attrs = [f"preferences.{key}"]
        if col == "date_format" and table[raw].lower().replace(".", "-") != raw:
            attrs.append(op.archive("date_format", raw))
        op.column(u + col, "mapped", *attrs)
    if not T.is_empty(row.get(u + "time_zone")):
        prefs["timeZone"] = row[u + "time_zone"]
        op.column(u + "time_zone", "carried", "preferences.timeZone")
    if not T.is_empty(row.get(u + "signature")):
        prefs["signature"] = row[u + "signature"]
        op.column(u + "signature", "carried", "preferences.signature")
    op.preferences = prefs
    NotApplicable(u + "currency_id", "D-37").apply(op, row, ctx)
    Pending(u + "imagename", "06.3").apply(op, row, ctx)
    roles = [ROLES[r["vtiger_user2role.roleid"]] for r in ctx.data["vtiger_user2role"]
             if int(r["vtiger_user2role.userid"]) == uid and r["vtiger_user2role.roleid"] in ROLES]
    for r in ctx.data["vtiger_user2role"]:
        if int(r["vtiger_user2role.userid"]) == uid:
            ok = r["vtiger_user2role.roleid"] in ROLES
            op.column("vtiger_user2role.roleid", "mapped" if ok else "error:role_unknown", "roles")
            op.relation("user2role", "linked" if ok else "error:role_unknown", "roles")
    op.linkMultiple["roles"] = {"items": [["Role", n] for n in roles], "domain": [["Role", n] for n in ROLES.values()]}
    teams = []
    for r in ctx.data["vtiger_users2group"]:
        if int(r["vtiger_users2group.userid"]) == uid:
            name = ctx.groups.get(int(r["vtiger_users2group.groupid"]))
            if name in GROUP_TEAMS:
                teams.append(["Team", name])
                op.relation("users2group", "linked", "teams")
            else:
                op.relation("users2group", "error:group_unknown")
    op.linkMultiple["teams"] = {"items": teams, "domain": [["Team", t] for t in GROUP_TEAMS]}
    return op


def build_note(row, ctx):
    m = "vtiger_modcomments."
    op = Op("Note", int(row["vtiger_crmentity.crmid"]), "ModComments")
    crmentity(op, row, ctx, owner=False, description=False)
    op.attributes.update(type="Post", isInternal=False, post=T.text(row.get(m + "commentcontent")))
    if op.attributes["post"] is not None:
        op.column(m + "commentcontent", "carried", "post")
    author = row.get(m + "userid")
    creator = op.links.get("createdBy")
    if not T.is_empty(author) and int(author) in ctx.users:
        op.links["createdBy"] = ["User", int(author)]
        op.column(m + "userid", "linked", "createdById")
        if creator and creator[1] != int(author):
            op.archive("smcreatorid", creator[1])
    elif not T.is_empty(author):
        op.column(m + "userid", "dangling:not_a_user")
    owner = row.get("vtiger_crmentity.smownerid")
    if not T.is_empty(owner):
        op.column("vtiger_crmentity.smownerid", "archived", op.archive("assigned_user_id", int(owner)))
    customer = row.get(m + "customer")
    if not T.is_empty(customer) and customer.strip() != "0":
        op.column(m + "customer", "archived", op.archive("customer", int(customer)))
    elif customer is not None and customer.strip() == "0":
        op.column(m + "customer", "zero_empty")
    status, target = ctx.target(row.get(m + "related_to"))
    if status == "ok":
        op.links["parent"] = list(target)
        op.column(m + "related_to", "linked", "parentId")
    elif status == "pending":
        op.pending = target       # the comment waits for its parent (stage `target`), not created as an orphan
        op.column(m + "related_to", f"pending:{target}")
    elif status == "deferred":
        op.pending = "deferred"
        op.column(m + "related_to", "deferred")
    else:
        op.skip = f"parent_{status}"
        op.column(m + "related_to", status)
    Pending(m + "filename", "06.3").apply(op, row, ctx)
    return op


# --- relations ---------------------------------------------------------------------------------------

# Relations of relations.csv touching the scope and owned by a later stage (the other end is imported there).
REL_PENDING_PAIRS = {
    ("Accounts", "Invoice"): "06.3", ("Contacts", "Invoice"): "06.3", ("Potentials", "Invoice"): "06.3",
    ("Potentials", "Quotes"): "06.3", ("Accounts", "SPPayments"): "06.3", ("Contacts", "SPPayments"): "06.3",
    ("Potentials", "Services"): "06.3", ("Contacts", "Emails"): "06.3", ("Leads", "Emails"): "06.3",
    ("Potentials", "Emails"): "06.3", ("Contacts", "Jivosite"): "06.3", ("Leads", "Jivosite"): "06.3",
    ("Contacts", "PBXManager"): "07.2", ("Leads", "PBXManager"): "07.2", ("Contacts", "SPCallPopup"): "07.2",
    ("Leads", "SPCallPopup"): "07.2", ("SPCallPopup", "Contacts"): "07.2", ("SPCallPopup", "Leads"): "07.2",
}


# crmentityrel pairs handled in this stage: a single link (duplicate of a field) or a link-multiple item;
# pairs with Calendar set the activity's parent (contacts of calls/meetings, the contact of a task).
REL_SINGLE = {("Accounts", "Potentials"): ("Opportunity", "account"), ("Accounts", "HelpDesk"): ("Case", "account"),
              ("Accounts", "Project"): ("Project", "account"), ("Project", "ProjectTask"): ("ProjectTask", "project")}
REL_MULTI = {("Accounts", "Contacts"): ("Contact", "accounts"), ("Contacts", "HelpDesk"): ("Case", "contacts")}
REL_CALENDAR = {"Accounts", "Contacts", "Leads", "Potentials", "Invoice"}


def attach_relations(ops, ctx):
    """Link tables → operations of the side imported later. Several sources of one single link (field, crmentityrel,
    seactivityrel) are merged: the same pair is a duplicate, another pair a conflict (kept in vtigerData, never
    last-writer-wins)."""
    by_key = {(o.entityType, o.vtigerId): o for o in ops}
    acts = {o.vtigerId: o for o in ops if o.entityType in ("Task", "Call", "Meeting")}
    d = ctx.data

    def live(crmid):
        info = ctx.crm.get(int(crmid))
        return info and not info[1]

    # seactivityrel: the activity's parent
    for r in d["vtiger_seactivityrel"]:
        act, crmid = int(r["vtiger_seactivityrel.activityid"]), r["vtiger_seactivityrel.crmid"]
        op = acts.get(act)
        if op is None:
            continue
        rel = f"seactivityrel:{ctx.crm.get(int(crmid), ('?',))[0]}->{op.entityType}"
        if op.links.get("parent"):
            parent_conflict(op, ctx, rel, crmid)
            continue
        link_ref(op, ctx, rel, "parent", crmid, kind="r")
    # cntactivityrel: contacts of calls/meetings, the contact of a task
    task_contacts = defaultdict(list)
    for r in d["vtiger_cntactivityrel"]:
        act, cid = int(r["vtiger_cntactivityrel.activityid"]), r["vtiger_cntactivityrel.contactid"]
        op = acts.get(act)
        if op is None:
            continue
        rel = f"cntactivityrel:Contacts->{op.entityType}"
        if op.entityType == "Task":
            task_contacts[act].append(int(cid))
            continue
        status, target = ctx.target(cid)
        multi_item(op, ctx, rel, "contacts", status, target, columns={"status": "None"})
    for act, cids in task_contacts.items():
        op = acts[act]
        cids.sort()
        link_ref(op, ctx, f"cntactivityrel:Contacts->Task", "contact", cids[0], kind="r", accept=("Contact",))
        for extra in cids[1:]:
            op.relation("cntactivityrel:Contacts->Task", "no_target")
        if cids[1:]:
            op.archive("contactids", cids)
    # salesmanactivityrel: invited users (Call/Meeting users, Task collaborators)
    for r in d["vtiger_salesmanactivityrel"]:
        act, uid = int(r["vtiger_salesmanactivityrel.activityid"]), int(r["vtiger_salesmanactivityrel.smid"])
        op = acts.get(act)
        if op is None:
            continue
        rel = f"salesmanactivityrel:Users->{op.entityType}"
        link = "collaborators" if op.entityType == "Task" else "users"
        if uid in ctx.users:
            op.add_item(link, ["User", uid] + ([{"status": "None"}] if link == "users" else []))
            op.relation(rel, "linked", link)
        else:
            op.relation(rel, "dangling:not_a_user")
    # contpotentialrel: more contacts of an opportunity
    for r in d["vtiger_contpotentialrel"]:
        op = by_key.get(("Opportunity", int(r["vtiger_contpotentialrel.potentialid"])))
        if op is None:
            continue
        status, target = ctx.target(r["vtiger_contpotentialrel.contactid"])
        multi_item(op, ctx, "contpotentialrel:Contacts->Potentials", "contacts", status, target)
    # crmentityrel: generic M:N of Vtiger
    for r in d["vtiger_crmentityrel"]:
        a_id, a_mod = int(r["vtiger_crmentityrel.crmid"]), r["vtiger_crmentityrel.module"]
        b_id, b_mod = int(r["vtiger_crmentityrel.relcrmid"]), r["vtiger_crmentityrel.relmodule"]
        if not (live(a_id) and live(b_id)):
            continue  # a pair with a deleted end is not a live relation (relations.csv counts live pairs)
        rel = f"crmentityrel:{a_mod}->{b_mod}"
        if a_mod not in SCOPE and b_mod not in SCOPE + ("Calendar",):
            continue  # neither end is imported in this stage
        if (a_mod, b_mod) in REL_PENDING_PAIRS:
            ctx.flags[f"pending_rel:{rel}:{REL_PENDING_PAIRS[(a_mod, b_mod)]}"] += 1
            continue
        crmentityrel_pair(by_key, acts, ctx, rel, a_id, a_mod, b_id, b_mod)
    # tags (freetags) of cases and project tasks
    tags = {int(r["vtiger_freetags.id"]): r["vtiger_freetags.tag"] for r in d["vtiger_freetags"]}
    for r in d["vtiger_freetagged_objects"]:
        module = r["vtiger_freetagged_objects.module"]
        entity, attr = {"HelpDesk": ("Case", "cTags"), "ProjectTask": ("ProjectTask", "tags")}.get(module, (None, None))
        oid = int(r["vtiger_freetagged_objects.object_id"])
        if entity is None or not live(oid):
            continue
        op = by_key.get((entity, oid))
        if op is None:
            continue
        tag = tags.get(int(r["vtiger_freetagged_objects.tag_id"]))
        if tag is None:
            op.relation(f"tags:{module}", "dangling:missing")
            continue
        op.attributes.setdefault(attr, [])
        if tag not in op.attributes[attr]:
            op.attributes[attr].append(tag)
        op.relation(f"tags:{module}", "linked", attr)
    for op in acts.values():
        # source wins: an activity without a (live) source parent has none in EspoCRM either
        if "parent" not in op.links and "parent" not in op.keep:
            op.links["parent"] = None
        if op.entityType == "Task" and "contact" not in op.links and "contact" not in op.keep:
            derived = derived_task_contact(op, by_key)
            if derived is DEFERRED:
                op.keep.add("contact")  # the parent or its contact is not imported in this run: left as it is
            else:
                op.links["contact"] = derived
    for op in ops:
        for attr in ("cTags", "tags"):
            if attr in op.attributes:
                op.attributes[attr].sort()
        if op.entityType in ("Case", "ProjectTask"):
            op.attributes.setdefault("cTags" if op.entityType == "Case" else "tags", [])
    # documents and attachments of in-scope records: stage 06.3
    for table, col, ref in (("vtiger_senotesrel", "crmid", "Documents"), ("vtiger_seattachmentsrel", "crmid", "attachment")):
        for r in d[table]:
            info = ctx.crm.get(int(r[f"{table}.{col}"]))
            if info and not info[1] and info[0] in SCOPE[1:] + ("Calendar",):
                ctx.flags[f"pending_rel:{table}:{info[0]}->{ref}:06.3"] += 1


def derived_task_contact(op, by_key):
    """A task without a contact of its own gets the one EspoCRM derives from the parent (Task ParentLink hook): the
    parent contact, or the primary contact of the parent opportunity — owned explicitly, so a re-run neither fights
    the hook nor keeps a contact the source no longer has."""
    if "parent" in op.keep:
        return DEFERRED
    parent = op.links.get("parent")
    if not parent:
        return None
    if parent[0] == "Contact":
        return parent
    if parent[0] == "Opportunity":
        opportunity = by_key.get(tuple(parent))
        if opportunity is None or "contact" in opportunity.keep:
            return DEFERRED
        return opportunity.links.get("contact")
    return None


DEFERRED = object()  # marker of derived_task_contact: its inputs are not part of this run


def multi_item(op, ctx, rel, link, status, target, columns=None):
    if status == "ok":
        op.add_item(link, list(target) + ([columns] if columns else []))
        op.relation(rel, "linked", link)
    elif status == "pending":
        op.relation(rel, f"pending:{target}")
    else:
        op.relation(rel, status)


def parent_conflict(op, ctx, rel, crmid):
    status, target = ctx.target(crmid)
    single_or_conflict(op, ctx, rel, "parent", crmid, status, target)


def single_or_conflict(op, ctx, rel, link, crmid, status, target):
    """A second source of a single link: unset → it sets the link; the same target → duplicate; another target →
    conflict, the alternative source id kept in vtigerData.<link>Alternatives (never last-writer-wins)."""
    current = op.links.get(link)
    if not current:
        link_ref(op, ctx, rel, link, crmid, kind="r")
    elif status == "ok" and current == list(target):
        op.relation(rel, "duplicate", f"{link}Id")
    else:
        key = f"{link}Alternatives"
        op.relation(rel, "conflict", op.archive(key, sorted(set(op.vtigerData.get(key, [])) | {int(crmid)})))


def crmentityrel_pair(by_key, acts, ctx, rel, a_id, a_mod, b_id, b_mod):
    """Vtiger's generic M:N → the link of the record imported later."""
    if b_mod == "Calendar":
        op = acts.get(b_id)
        if op is None:
            return
        status, target = ctx.target(a_id)
        if op.entityType == "Task" and a_mod == "Contacts":
            single_or_conflict(op, ctx, rel, "contact", a_id, status, target)
            return
        if op.entityType in ("Call", "Meeting") and a_mod in ("Contacts", "Leads"):
            if a_mod == "Leads" and not op.links.get("parent"):
                link_ref(op, ctx, rel, "parent", a_id, kind="r")
            elif a_mod == "Leads" and status == "ok" and op.links.get("parent") == list(target):
                op.relation(rel, "duplicate", "parentId")
            else:  # attendees: contacts and leads of a call or meeting
                multi_item(op, ctx, rel, a_mod.lower(), status, target, columns={"status": "None"})
            return
        single_or_conflict(op, ctx, rel, "parent", a_id, status, target)
        return
    if (a_mod, b_mod) in REL_SINGLE:
        entity, link = REL_SINGLE[(a_mod, b_mod)]
        op = by_key.get((entity, b_id))
        if op is not None:
            status, target = ctx.target(a_id)
            single_or_conflict(op, ctx, rel, link, a_id, status, target)
        return
    if (a_mod, b_mod) in REL_MULTI:
        entity, link = REL_MULTI[(a_mod, b_mod)]
        op = by_key.get((entity, b_id))
        if op is None:
            return
        status, target = ctx.target(a_id)
        multi_item(op, ctx, rel, link, status, target)
        return
    ctx.flags[f"unhandled_rel:{rel}"] += 1


# --- plan ------------------------------------------------------------------------------------------

@dataclass
class Plan:
    ops: list            # operations to send, in ORDER
    held: list           # records not sent: pending (later stage), skipped (reason)
    flags: Counter


def build(data, selected=None, key_range=(1, SYNTHETIC_KEY_MIN - 1), effective_admin=EFFECTIVE_ADMIN):
    """All operations of the run from the rows read (spec order, deterministic)."""
    ctx = Context(data, selected, key_range, effective_admin)
    ops = []
    if "Users" in ctx.selected:
        ops += [build_user(r, ctx) for r in sorted(data["vtiger_users"], key=lambda r: int(r["vtiger_users.id"]))]
    for module in ("Accounts", "Contacts", "Leads", "Potentials", "Project", "ProjectTask", "HelpDesk"):
        if module not in ctx.selected:
            continue
        rows = sorted(data[module], key=lambda r: int(r["vtiger_crmentity.crmid"]))
        ops += [record_or_error(module, r, ctx, build_record) for r in rows]
        if module == "Contacts":
            ops += [record_or_error(module, r, ctx, lambda m, row, c: build_contact_access(row, c)) for r in rows]
    for module in ("Calendar", "Events"):
        if module in ctx.selected:
            ops += [record_or_error(module, r, ctx, build_activity)
                    for r in sorted(data[module], key=lambda r: int(r["vtiger_crmentity.crmid"]))]
    if "ModComments" in ctx.selected:
        rows = sorted(data["ModComments"], key=lambda r: (r["vtiger_crmentity.createdtime"] or "",
                                                          int(r["vtiger_crmentity.crmid"])))
        ops += [record_or_error("ModComments", r, ctx, lambda m, row, c: build_note(row, c)) for r in rows]
    attach_relations([o for o in ops if not o.skip], ctx)
    for op in ops:
        if not (key_range[0] <= op.vtigerId <= key_range[1]):
            raise T.TransformError("key_out_of_range")
    order = {e: i for i, e in enumerate(ORDER)}
    send = [o for o in ops if not (o.skip or o.pending)]
    send.sort(key=lambda o: order[o.entityType])   # stable: comments keep their chronological order
    return Plan(send, [o for o in ops if o.skip or o.pending], ctx.flags)


def record_or_error(module, row, ctx, builder):
    try:
        return builder(module, row, ctx)
    except T.TransformError as e:
        entity = ENTITY_BY_SETYPE.get(module, "Task" if module in ("Calendar", "Events") else "User")
        key = row.get("vtiger_crmentity.crmid") or row.get("vtiger_users.id")
        op = Op(entity, int(key), module)
        op.skip = f"error:{e.code}"
        return op


# --- coverage against the maps --------------------------------------------------------------------

def consumed_columns():
    """(module, table.column) consumed by the rules — the static side of check_coverage."""
    out = set()
    for module in ("Accounts", "Contacts", "Leads", "Potentials", "HelpDesk", "Project", "ProjectTask"):
        for rule in rules_of(module):
            out |= {(module, c) for c in rule.cols}
    common = ("smownerid", "smcreatorid", "modifiedby", "createdtime", "modifiedtime", "description")
    for module in ("Accounts", "Contacts", "Leads", "Potentials", "HelpDesk", "Project", "ProjectTask", "Calendar", "Events"):
        out |= {(module, "vtiger_crmentity." + c) for c in common}
    out |= {("ModComments", "vtiger_crmentity." + c) for c in common if c != "description"}
    out |= {(m, "vtiger_seactivityrel.crmid") for m in ("Calendar", "Events")}  # attach_relations: parent
    out |= {("Events", "vtiger_cntactivityrel.contactid")}                    # attach_relations: contacts
    out |= {("Contacts", "vtiger_contactdetails.accountid")}
    out |= {("Contacts", "vtiger_contactscf." + c) for c in ACCESS_COLUMNS}
    a = "vtiger_activity."
    for module in ("Calendar", "Events"):
        out |= {(module, a + c) for c in ("subject", "date_start", "time_start", "due_date", "priority", "activitytype")}
    out |= {("Calendar", a + "status")}
    out |= {("Events", a + c) for c in ("time_end", "eventstatus", "duration_hours", "duration_minutes")}
    m = "vtiger_modcomments."
    out |= {("ModComments", m + c) for c in ("commentcontent", "userid", "customer", "related_to", "filename")}
    u = "vtiger_users."
    out |= {("Users", u + c) for c in ("user_name", "is_admin", "first_name", "last_name", "title", "phone_crm_extension",
                                       "status", "date_entered", "email1", "phone_work", "phone_mobile", "department",
                                       "language", "date_format", "hour_format", "dayoftheweek", "time_zone",
                                       "signature", "currency_id", "imagename")}
    out |= {("Users", "vtiger_user2role.roleid")}
    return out


HANDLED_RELATIONS_PREFIXES = ("seactivityrel:", "cntactivityrel:", "salesmanactivityrel:", "contpotentialrel:",
                              "tags:", "users2group", "user2role")


def load_maps(repo):
    with open(repo / "docs/migration/field-map.csv", newline="", encoding="utf-8") as fh:
        fields = list(csv.DictReader(fh))
    with open(repo / "docs/migration/relations.csv", newline="", encoding="utf-8") as fh:
        relations = list(csv.DictReader(fh))
    return fields, relations


def module_of_physical(table):
    for module, src in SOURCES.items():
        if table in src.tables()[1:]:
            return module
    return "Users" if table in ("vtiger_users", "vtiger_user2role") else None


def check_coverage(fields, relations):
    """Problems (identifiers only) that refuse the run before any read of the source."""
    problems = []
    consumed = consumed_columns()
    rows = defaultdict(list)
    for r in fields:
        module = r["source_module"] or module_of_physical(r["source_table"])
        if module in SCOPE:
            rows[(module, f"{r['source_table']}.{r['source_column']}")].append(r)
    for key, rs in sorted(rows.items()):
        transfer = [r for r in rs if r["fate"].startswith(TRANSFER_FATES)]
        is_key = any(r["target_field"] in ("(ключ записи)", "vtigerId", "(тип сущности)") for r in rs)
        if transfer and key not in consumed and not is_key:
            problems.append(f"no rule for {key[0]} {key[1]}")
    for key in sorted(consumed):
        if key in MAP_GAPS:
            continue
        if key not in rows:
            problems.append(f"rule without a field-map row: {key[0]} {key[1]}")
        elif all(r["fate"].startswith("исключено") for r in rows[key]) and key[1].split(".")[1] not in (
                "activitytype", "description"):
            problems.append(f"rule for an excluded column: {key[0]} {key[1]}")
    for r in relations:
        ends = {r["from_module"], *r["to_module"].split("|")}
        if not ends & set(SCOPE) or r["kind"] in ("owner", "history"):
            continue
        if r["fate"].startswith(("пусто", "исключено")) or not r["fate"].startswith(TRANSFER_FATES + ("слияние",)):
            continue
        rid = r["relation_id"]
        if rid.startswith("crmentityrel:"):
            pair = tuple(rid.split(":", 1)[1].split("->"))
            if not (pair in REL_PENDING_PAIRS or pair in REL_SINGLE or pair in REL_MULTI
                    or (pair[1] == "Calendar" and pair[0] in REL_CALENDAR)):
                problems.append(f"relation not handled: {rid}")
            continue
        if rid.startswith(HANDLED_RELATIONS_PREFIXES) or rid in FIELD_RELATIONS:
            continue
        if rid.startswith(("senotesrel:", "seattachmentsrel:")):
            continue  # documents and files: stage 06.3 (counted as pending)
        if r["from_module"] not in SCOPE:
            continue  # a field of a later module pointing into the scope: imported with that module
        problems.append(f"relation not handled: {rid}")
    return problems


# Field relations of in-scope modules handled by the column rules above.
FIELD_RELATIONS = {"Calendar.crmid", "Events.crmid", "Events.contactid", "Contacts.accountid", "HelpDesk.contact_id",
                   "HelpDesk.parent_id", "ModComments.customer", "ModComments.related_to", "ModComments.userid",
                   "Potentials.contact_id", "Potentials.related_to", "Project.linktoaccountscontacts",
                   "Project.potentialid", "ProjectTask.projectid"}
