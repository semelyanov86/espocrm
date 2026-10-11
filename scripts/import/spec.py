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
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import transforms as T

# --- scope ---------------------------------------------------------------------------------------

BASE_SCOPE = ("Users", "Accounts", "Contacts", "Leads", "Potentials", "Calendar", "Events", "HelpDesk", "ModComments",
              "Project", "ProjectTask")
# Stage 06.3 (D-139, owner's answers 2026-10-11): finance, catalogues, documents, knowledge base, e-mail, archives and
# every file; pseudo-modules: the legal entity (vtiger_organizationdetails) and the files of the records in scope.
FINANCE = ("Quotes", "SalesOrder", "Act", "Invoice", "SPPayments")
ARCHIVES = ("Consignment", "ServiceContracts", "Assets", "Jivosite", "JVmes")
CONTENT_SCOPE = ("Vendors", "Products", "Services", *FINANCE, *ARCHIVES, "Faq", "Emails", "Documents",
                 "OrganizationDetails", "Attachments")
SCOPE = BASE_SCOPE + CONTENT_SCOPE
# Target entity of a live source record of each setype (activities: by activitytype).
ENTITY_BY_SETYPE = {"Accounts": "Account", "Contacts": "Contact", "Leads": "Lead", "Potentials": "Opportunity",
                    "HelpDesk": "Case", "Project": "Project", "ProjectTask": "ProjectTask", "ModComments": "Note",
                    "Vendors": "Vendor", "Products": "Product", "Services": "Product", "Quotes": "Quote",
                    "SalesOrder": "SalesOrder", "Invoice": "Invoice", "Act": "Act", "SPPayments": "Payment",
                    "Documents": "Document", "Faq": "KnowledgeBaseArticle", "Emails": "Email",
                    **{m: "VtigerArchive" for m in ARCHIVES}}
ACTIVITY_ENTITY = {"Task": "Task", "Call": "Call", "Meeting": "Meeting", "Письмо": "Task"}
# Modules imported by later stages (owner's answer 2026-10-11): references to them wait for that stage.
PENDING = {"PBXManager": "07.2", "SPCallPopup": "07.2"}
# Target entity types each source module fills (inventory of the target: records gone from the source).
MODULE_ENTITIES = {"Users": ("User",), "Accounts": ("Account",), "Contacts": ("Contact", "ContactAccess"),
                   "Leads": ("Lead",), "Potentials": ("Opportunity",), "Project": ("Project",),
                   "ProjectTask": ("ProjectTask",), "HelpDesk": ("Case",), "Calendar": ("Task",),
                   "Events": ("Call", "Meeting", "Task"), "ModComments": ("Note",), "Vendors": ("Vendor",),
                   "Products": ("Product",), "Services": ("Product",), "Quotes": ("Quote", "QuoteItem"),
                   "SalesOrder": ("SalesOrder", "SalesOrderItem"), "Invoice": ("Invoice", "InvoiceItem"),
                   "Act": ("Act", "ActItem"), "SPPayments": ("Payment", "PaymentAllocation"),
                   **{m: ("VtigerArchive",) for m in ARCHIVES}, "Faq": ("KnowledgeBaseArticle",),
                   "Emails": ("Email",), "Documents": ("Document", "DocumentFolder"), "Attachments": ("Attachment",)}
# Import order: a reference always points to an entity type imported earlier in the run.
ORDER = ("User", "Vendor", "Product", "LegalEntity", "Account", "Contact", "ContactAccess", "Lead", "Opportunity",
         "Project", "ProjectTask", "Case", "Quote", "QuoteItem", "SalesOrder", "SalesOrderItem", "Act", "ActItem",
         "Invoice", "InvoiceItem", "Payment", "PaymentAllocation", "VtigerArchive", "KnowledgeBaseCategory",
         "KnowledgeBaseArticle", "Task", "Call", "Meeting", "Email", "DocumentFolder", "Document", "Note", "Attachment")
# Entity types identified by a natural key instead of vtigerId (KeyResolver::NATURAL_KEYS).
NATURAL_KEY_TYPES = ("LegalEntity", "KnowledgeBaseCategory")
ROLES = {"H2": "Директор", "H3": "Заместитель директора", "H4": "Менеджер по продажам", "H10": "Менеджер клиентов"}
GROUP_TEAMS = ("Отдел Поддержки", "Отдел Маркетинга", "Отдел Продаж")  # app.itvolgaAcl.groupTeams
EFFECTIVE_ADMIN = 1          # D-39: only user#1 is an administrator in Vtiger
SYNTHETIC_KEY_MIN = 900_000_000  # vtigerId block of the stand tests; the real import refuses such source keys
TRANSFER_FATES = ("перенос", "архив", "переносится как связь")
# Filled source columns the generated map has no row for, consumed by a rule anyway (reason in import.md):
# ModComments does not declare `modifiedby` in vtiger_field, so the audit has no module row for it; the name of an
# attachment has a map row only under Emails (uitype 61), the file of every attachment needs it (D-149).
MAP_GAPS = {("ModComments", "vtiger_crmentity.modifiedby"): "Note.modifiedBy",
            ("Attachments", "vtiger_attachments.name"): "Attachment.name",
            # Emails and Faq do not declare the author / the owner in vtiger_field either (stage 06.3, D-149)
            ("Emails", "vtiger_crmentity.smcreatorid"): "Email.createdBy",
            ("Faq", "vtiger_crmentity.smownerid"): "KnowledgeBaseArticle.assignedUser"}

# Filled source columns without a map row and without a working field: an explicit fate with its reason (stage 06.3,
# D-149). Archived e-mails share vtiger_activity with the calendar; the event-only service columns hold the defaults.
EXTRA_FATES = {("Emails", "vtiger_activity." + c): f"исключено: служебное поле события Vtiger, у писем — значение по "
               f"умолчанию ({c})" for c in ("notime", "sendnotification", "visibility")}
MAP_GAPS.update({(m, "vtiger_crmentity." + c): f"VtigerArchive.data.{k}" for m in ("Jivosite", "JVmes")
                 for c, k in (("smcreatorid", "created_user_id"), ("modifiedby", "modifiedby"))})


def is_key_row(r):
    """A map row of a record key: the key of the record or a join (→ vtigerId), the entity type."""
    target = r["target_field"]
    return target in ("(ключ записи)", "vtigerId", "(тип сущности)") or target.endswith(".vtigerId")
NO_VTIGER_DATA = {"ContactAccess", "VtigerArchive", "LegalEntity", "KnowledgeBaseCategory"}  # no vtigerData field
ACCESS_COLUMNS = ("cf_1322", "cf_1324", "cf_1326", "cf_1328")  # D-06/D-42: values never leave the pipe
# Source columns never read into the import process (secrets of users and staff data excluded by the owner).
FORBIDDEN = {"vtiger_users": {"user_password", "confirm_password", "user_hash", "accesskey", "crypt_type",
                              "phone_home", "address_street", "address_city", "address_state", "address_country",
                              "address_postalcode", "user_preferences"}}


# Columns of the link tables (read whole for the rows in scope): "pair" — the columns a link is made of (each row gets
# one relation outcome, counted against the SQL row census); "pending:<stage>" — links of a later stage; anything else is
# an explicit reason why the value is not carried (D-144). A non-empty column missing here fails the reconciliation.
LINK_COLUMNS = {
    "vtiger_user2role": {"userid": "pair", "roleid": "pair"},
    "vtiger_users2group": {"groupid": "pair", "userid": "pair"},
    "vtiger_groups": {"groupid": "pair", "groupname": "pair",
                      "description": "excluded: группы воспроизводятся командами (D-39), описание не переносится"},
    "vtiger_crmentityrel": {"crmid": "pair", "module": "pair", "relcrmid": "pair", "relmodule": "pair"},
    "vtiger_contpotentialrel": {"contactid": "pair", "potentialid": "pair"},
    "vtiger_seactivityrel": {"crmid": "pair", "activityid": "pair"},
    "vtiger_cntactivityrel": {"contactid": "pair", "activityid": "pair"},
    "vtiger_salesmanactivityrel": {"smid": "pair", "activityid": "pair"},
    "vtiger_freetagged_objects": {"tag_id": "pair", "object_id": "pair", "module": "pair",
                                  "tagger_id": "excluded: автор постановки тега — у значения multiEnum его нет",
                                  "tagged_on": "excluded: время постановки тега — у значения multiEnum его нет"},
    "vtiger_freetags": {"id": "pair", "raw_tag": "pair",
                        "tag": "excluded: нормализованная форма raw_tag (значение тега — raw_tag)",
                        "visibility": "excluded: видимость тега Vtiger (теги EspoCRM — значения поля)",
                        "owner": "excluded: автор тега Vtiger"},
    "vtiger_senotesrel": {"crmid": "pair", "notesid": "pair"},
    "vtiger_seattachmentsrel": {"crmid": "pair", "attachmentsid": "pair"},
    "vtiger_salesmanattachmentsrel": {"smid": "pair", "attachmentsid": "pair"},
    "vtiger_email_track": {"crmid": "pair", "mailid": "pair", "access_count": "pair", "click_count": "pair"},
}
# Phone columns of each module (number type), in record order: they also fix the type of a shared number (first owner
# in import order over the whole source, whatever modules a run selects).
PHONE_COLUMNS = {
    "Users": (("vtiger_users.phone_work", "Office", "phone_work"), ("vtiger_users.phone_mobile", "Mobile", "phone_mobile")),
    "Accounts": (("vtiger_account.phone", "Office", "phone"), ("vtiger_account.otherphone", "Other", "otherphone"),
                 ("vtiger_account.fax", "Fax", "fax")),
    "Contacts": (("vtiger_contactdetails.phone", "Office", "phone"), ("vtiger_contactdetails.mobile", "Mobile", "mobile"),
                 ("vtiger_contactsubdetails.homephone", "Home", "homephone"),
                 ("vtiger_contactsubdetails.otherphone", "Other", "otherphone"),
                 ("vtiger_contactdetails.fax", "Fax", "fax")),
    "Leads": (("vtiger_leadaddress.phone", "Office", "phone"), ("vtiger_leadaddress.mobile", "Mobile", "mobile"),
              ("vtiger_leadaddress.fax", "Fax", "fax")),
    "Vendors": (("vtiger_vendor.phone", "Office", "phone"),),
}


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
                     where=" AND (`vtiger_activity`.activitytype IS NULL "
                           "OR `vtiger_activity`.activitytype NOT IN ('Task', 'Emails'))"),  # NULL: an error record
    # stage 06.3
    "Vendors": Source("Vendors", ("vtiger_vendor", "vendorid"), (("vtiger_vendorcf", "vendorid"),)),
    "Products": Source("Products", ("vtiger_products", "productid"), (("vtiger_productcf", "productid"),)),
    "Services": Source("Services", ("vtiger_service", "serviceid"), (("vtiger_servicecf", "serviceid"),)),
    "Quotes": Source("Quotes", ("vtiger_quotes", "quoteid"),
                     (("vtiger_quotescf", "quoteid"), ("vtiger_quotesbillads", "quotebilladdressid"),
                      ("vtiger_quotesshipads", "quoteshipaddressid"))),
    "SalesOrder": Source("SalesOrder", ("vtiger_salesorder", "salesorderid"),
                         (("vtiger_salesordercf", "salesorderid"), ("vtiger_sobillads", "sobilladdressid"),
                          ("vtiger_soshipads", "soshipaddressid"), ("vtiger_invoice_recurring_info", "salesorderid"))),
    "Invoice": Source("Invoice", ("vtiger_invoice", "invoiceid"),
                      (("vtiger_invoicecf", "invoiceid"), ("vtiger_invoicebillads", "invoicebilladdressid"),
                       ("vtiger_invoiceshipads", "invoiceshipaddressid"))),
    "Act": Source("Act", ("vtiger_sp_act", "actid"),
                  (("vtiger_sp_actcf", "actid"), ("vtiger_sp_actbillads", "actbilladdressid"),
                   ("vtiger_sp_actshipads", "actshipaddressid"))),
    "SPPayments": Source("SPPayments", ("sp_payments", "payid"), (("sp_paymentscf", "payid"),)),
    "Documents": Source("Documents", ("vtiger_notes", "notesid"), (("vtiger_notescf", "notesid"),)),
    "Faq": Source("Faq", ("vtiger_faq", "id"), (("vtiger_faqcf", "faqid"),)),
    "Emails": Source("Emails", ("vtiger_activity", "activityid"), (("vtiger_emaildetails", "emailid"),),
                     setype="Emails"),
    "Consignment": Source("Consignment", ("vtiger_sp_consignment", "consignmentid"),
                          (("vtiger_sp_consignmentcf", "consignmentid"),
                           ("vtiger_sp_consignmentbillads", "consignmentbilladdressid"),
                           ("vtiger_sp_consignmentshipads", "consignmentshipaddressid"))),
    "ServiceContracts": Source("ServiceContracts", ("vtiger_servicecontracts", "servicecontractsid"),
                               (("vtiger_servicecontractscf", "servicecontractsid"),)),
    "Assets": Source("Assets", ("vtiger_assets", "assetsid"), (("vtiger_assetscf", "assetsid"),)),
    "Jivosite": Source("Jivosite", ("vtiger_jivosite", "jivositeid"), (("vtiger_jivositecf", "jivositeid"),)),
    "JVmes": Source("JVmes", ("vtiger_jvmes", "jvmesid"), (("vtiger_jvmescf", "jvmesid"),)),
}
# Line items of the documents (one table for every module, D-09: VTEItems excluded): read per live parent module.
LINE_MODULES = ("Quotes", "SalesOrder", "Invoice", "Act", "Consignment")
# Plain tables read whole (no crmentity): users and the link tables.
TABLES = ("vtiger_users", "vtiger_user2role", "vtiger_users2group", "vtiger_groups", "vtiger_crmentityrel",
          "vtiger_contpotentialrel", "vtiger_seactivityrel", "vtiger_cntactivityrel", "vtiger_salesmanactivityrel",
          "vtiger_freetagged_objects", "vtiger_freetags", "vtiger_senotesrel", "vtiger_seattachmentsrel",
          "vtiger_salesmanattachmentsrel", "vtiger_email_track")
# Plain tables of pseudo-modules (06.3): rows in scope with their census under the pseudo-module.
PLAIN_MODULES = {"Attachments": ("vtiger_attachments",), "OrganizationDetails": ("vtiger_organizationdetails",),
                 "Documents": ("vtiger_attachmentsfolder",)}


# --- operation under construction ----------------------------------------------------------------

@dataclass
class Op:
    entityType: str
    vtigerId: object        # int; the natural key (str) of NATURAL_KEY_TYPES; None for the logo attachment
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
    kept_ids: dict = field(default_factory=dict)    # link → source crmid of the untouched target
    pending: str = None                             # the whole record waits for a stage (comment on a FAQ)
    skip: str = None                                # the record is not imported (reason code)
    relate: dict = field(default_factory=dict)      # link → [[type, key]]: add-only rows of links without a field
    owner: dict = None                              # Attachment: {entityType, key, field}
    file: dict = None                               # Attachment: {size, sha256} of the source file
    file_ref: bytes = None                          # Attachment: path of the file in the snapshot (never sent)
    name_override: str = None                       # key of an operation without a numeric source key

    @property
    def key(self):
        return self.name_override or f"{self.entityType}:{self.vtigerId}"

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

    def add_relate(self, link, target):
        items = self.relate.setdefault(link, [])
        if list(target) not in items:
            items.append(list(target))

    def payload(self):
        """The operation sent to the writer. vtigerData is owned as a whole: its keys are the source facts kept."""
        attributes = dict(self.attributes)
        if self.entityType not in NO_VTIGER_DATA:
            attributes["vtigerData"] = dict(sorted(self.vtigerData.items())) or None
        data = {"key": self.key, "entityType": self.entityType, "attributes": attributes,
                "links": self.links, "linkMultiple": self.linkMultiple}
        if self.entityType in NATURAL_KEY_TYPES:
            data["naturalKey"] = self.vtigerId
        elif self.vtigerId is not None:
            data["vtigerId"] = self.vtigerId
        for name in ("emails", "phones", "secret", "preferences", "user", "keyAlsoIn", "owner"):
            if getattr(self, name) is not None:
                data[name] = getattr(self, name)
        if self.relate:
            data["relate"] = {k: sorted(v) for k, v in sorted(self.relate.items())}
        if self.file is not None:
            data["file"] = dict(self.file)
        if self.onlyIfExists:
            data["onlyIfExists"] = True
        if self.keep:
            data["keep"] = sorted(self.keep)  # single links left as they are: the writer protects them from hooks
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
        self.phone_types = phone_registry(data)  # number → type of its first owner over the whole source
        # stage 06.3: product names (the name of a document line), files of their owners ((entity, key) → attachment ids)
        self.product_names = {int(r["vtiger_crmentity.crmid"]): r.get(c) for m, c in (
            ("Products", "vtiger_products.productname"), ("Services", "vtiger_service.servicename"))
            for r in data.get(m, [])}
        self.attachments_of = attachment_owners(data)
        self.attachment_names = {int(r["vtiger_attachments.attachmentsid"]): r.get("vtiger_attachments.name")
                                 for r in data.get("vtiger_attachments", [])}
        self.rows_of_email = {}

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
                module, entity = "Emails", "Email"
            else:
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


class Num(Rule):
    """A decimal without a currency (quantity, percent): the value as a decimal string of the column's scale."""

    def apply(self, op, row, ctx):
        _set(op, self.cols[0], self.attr, T.decimal(self.value(row), self.kw["scale"]))


class Currency(Rule):
    """currency_id of a finance record: the installation has one currency (D-37), 1 = RUB; the currency of every money
    attribute of the record carries it. Any other id is an error, never a guess."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        if T.is_empty(raw):
            return
        if raw.strip() != "1":
            raise T.TransformError("currency_unknown")  # the record is held: its money is never written as RUB
        op.column(self.cols[0], "mapped", *sorted(a for a in op.attributes if a.endswith("Currency")))


class RegionId(Rule):
    """region_id of a finance document: NULL (before the 2018-07 upgrade) and 0 are both meaningful for the source
    verification (SourceVerification reads vtigerData.region_id), so the key is always present."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        if T.is_empty(raw):
            op.vtigerData["region_id"] = None
            return
        op.column(self.cols[0], "archived", op.archive("region_id", T.integer(raw)))


class DocNo(Rule):
    """An integer number kept as a string field (the payment document number); 0 is «no number»."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        value = T.integer(raw, zero_is_empty=True)
        _set(op, self.cols[0], self.attr, None if value is None else str(value))
        if value is None and not T.is_empty(raw):
            op.column(self.cols[0], "zero_empty")


class Data(Rule):
    """A column of an archive module (VtigerArchive.data.<key>, D-08): the source value as is."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        if T.is_empty(raw):
            return
        op.attributes.setdefault("data", {})[self.attr] = raw
        op.column(self.cols[0], "archived", "data")


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


class FileName(Rule):
    """The file name column of a record whose file is an attachment of its own (Contact photo, User avatar): with the
    attachment of the same name in the source the file arrives by its Attachment operation (`linked`); another name
    is kept in vtigerData and counted (`file_name_differs`, a finding); a name without a file is an accepted loss
    (D-23), the name kept in vtigerData. A file field is never cleared by the import (stage 06.3)."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        if T.is_empty(raw):
            return
        attached = ctx.attachments_of.get((op.entityType, op.vtigerId))
        if not attached:
            op.column(self.cols[0], "not_applicable:D-23", op.archive(self.cols[0].split(".")[1], raw))
        elif raw in {ctx.attachment_names.get(a) for a in attached}:
            op.column(self.cols[0], "linked", self.attr)
        else:
            ctx.flags["file_name_differs"] += 1
            op.column(self.cols[0], "archived", op.archive(self.cols[0].split(".")[1], raw))


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
            shared = ctx.phone_types.get(number, ptype)
            if shared != ptype:
                ctx.flags["phone_type_conflict"] += 1
                attrs.append(op.archive(key, raw))
                outcome = "type_conflict"
            phones.append({"phoneNumber": number, "type": shared, "primary": not phones})
            op.column(col, outcome, *attrs)
        op.phones = phones


def phone_registry(data):
    """EspoCRM keeps a number's type on the shared PhoneNumber row: the first owner in import order over the WHOLE
    source fixes it, so a run limited by --only never flips the type of a number another module uses."""
    registry = {}
    batches = [("Users", sorted(data.get("vtiger_users", []), key=lambda r: int(r["vtiger_users.id"])))]
    batches += [(m, sorted(data.get(m, []), key=lambda r: int(r["vtiger_crmentity.crmid"])))
                for m in ("Accounts", "Contacts", "Leads", "Vendors")]  # vendors (06.3) last: 06.2 types stay
    for module, rows in batches:
        for row in rows:
            for col, ptype, _ in PHONE_COLUMNS[module]:
                number, _cls = T.phone(row.get(col))
                if number is not None:
                    registry.setdefault(number, ptype)
    return registry


def attachment_owners(data):
    """(owner entity, owner key) → ids of its live attachments in scope (vtiger_seattachmentsrel by crmid, user images
    by vtiger_salesmanattachmentsrel)."""
    import spec_content as C  # noqa: PLC0415 (the content part imports this module)
    live = {r["vtiger_attachments.attachmentsid"] for r in data.get("vtiger_attachments", [])}
    out = defaultdict(list)
    for table, owner_col in (("vtiger_seattachmentsrel", "crmid"), ("vtiger_salesmanattachmentsrel", "smid")):
        for r in data.get(table, []):
            att = r[f"{table}.attachmentsid"]
            setype = data["crm"].get(int(att), (None,))[0]
            if att not in live or setype not in C.ATTACHMENT_OWNERS:
                continue
            out[(C.ATTACHMENT_OWNERS[setype][1], int(r[f"{table}.{owner_col}"]))].append(int(att))
    return dict(out)


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
    if status in ("pending", "deferred"):
        record(key, f"pending:{target}" if status == "pending" else "deferred")
        op.keep.add(link)
        op.kept_ids.setdefault(link, int(crmid))
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


def users_deferred(op, ctx, col, link):
    """Users are not part of this run (--only): a link to a user is left as it is (and protected from hooks)."""
    if "Users" in ctx.selected:
        return False
    op.keep.add(link)
    op.column(col, "deferred")
    return True


def user_ref(op, ctx, col, link, value):
    if not (T.is_empty(value) or int(value) == 0) and users_deferred(op, ctx, col, link):
        return
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
    if oid in ctx.users and users_deferred(op, ctx, col, "assignedUser"):
        return
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
            Phones(*PHONE_COLUMNS["Accounts"]),
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
            Phones(*PHONE_COLUMNS["Contacts"]),
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
            FileName(c + "imagename", "cPhotoId"),
        ]
    if module == "Leads":
        a2, s2, cf = "vtiger_leadaddress.", "vtiger_leadsubdetails.", "vtiger_leadscf."
        return [
            Salutation(l + "salutation", "salutationName", entity="Lead"),
            Str(l + "firstname", "firstName"), Str(l + "lead_no", "vtigerNo"), Str(l + "lastname", "lastName"),
            Phones(*PHONE_COLUMNS["Leads"]),
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
        if "account" in op.keep:  # the account is not imported in this run: the title (its link role) is left as is
            if raw is not None:
                op.column(self.cols[0], "deferred")
            return
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
    entity = ACTIVITY_ENTITY.get(atype or "")
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
    start_utc = pair_datetime(op, row, ctx, a + "date_start", a + "time_start", "dateStart")
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
    if entity == "Task":
        op.attributes.update(dateStart=start_utc, dateStartDate=None, dateCompleted=None)
        if module == "Calendar":
            op.attributes["cTaskType"] = None  # a plain task: the kind «Письмо» is owned by the source too
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
            end = pair_datetime(op, row, ctx, a + "due_date", a + "time_end", "dateEnd")
            op.attributes.update(dateEnd=end, dateEndDate=None, priority=None, cTaskType="Письмо")
            op.column(a + "activitytype", "mapped", "cTaskType")
            duration(op, row, start_utc, end)
    else:
        end = pair_datetime(op, row, ctx, a + "due_date", a + "time_end", "dateEnd")
        if entity == "Call" and end is None:
            end = start_utc   # D-43: Call.dateEnd is required; the source had no complete end
            if start_utc:
                op.archive("dateEndMissing", True)
        op.attributes.update(dateStart=start_utc, dateEnd=end)
        if entity == "Meeting":
            op.attributes.update(dateStartDate=None, dateEndDate=None, isAllDay=False)
        op.column(a + "activitytype", "carried", "entityType")
        duration(op, row, start_utc, end)
    if module == "Events":
        prio = row.get(a + "priority")
        if not T.is_empty(prio):
            op.column(a + "priority", "archived", op.archive("taskpriority", prio))
    if module == "Calendar":
        op.column(a + "activitytype", "carried", "entityType")
    return op


def pair_datetime(op, row, ctx, date_col, time_col, attr):
    """Vtiger keeps an activity's start/end as a date column plus a time column → one UTC datetime (D-30). Both parts
    are carried only when the datetime is made of them; a part that has no place (the other one is empty) stays in
    vtigerData under its column name — never a substituted value."""
    value = T.to_utc(T.combine(row.get(date_col), row.get(time_col)), ctx.flags)
    for col in (date_col, time_col):
        if T.is_empty(row.get(col)):
            continue
        if value:
            op.column(col, "carried", attr)
        else:
            op.column(col, "archived", op.archive(col.split(".")[1], row[col]))
    return value


def duration(op, row, start_utc, end_utc):
    """Call/Meeting duration is computed by EspoCRM from the dates; Vtiger hours+minutes are kept only when they
    disagree with the dates."""
    a = "vtiger_activity."
    hours, minutes = row.get(a + "duration_hours"), row.get(a + "duration_minutes")
    if T.is_empty(hours) and T.is_empty(minutes):
        return
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
    Phones(*PHONE_COLUMNS["Users"]).apply(op, row, ctx)
    if not T.is_empty(row.get(u + "department")):
        op.column(u + "department", "archived", op.archive("department", row[u + "department"]))
    prefs = dict.fromkeys(("language", "dateFormat", "timeFormat", "weekStart", "timeZone", "signature"))  # owned
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
        if col == "date_format" and table[raw] != raw:
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
    FileName(u + "imagename", "avatarId").apply(op, row, ctx)
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
    if not T.is_empty(author) and int(author) in ctx.users and "Users" not in ctx.selected:
        op.column(m + "userid", "deferred")
    elif not T.is_empty(author) and int(author) in ctx.users:
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
    filename = row.get(m + "filename")
    if not T.is_empty(filename) and filename.strip() == "0":
        op.column(m + "filename", "zero_empty")
    elif not T.is_empty(filename):  # the id of the comment's ModComments Attachment
        attached = ctx.attachments_of.get(("Note", op.vtigerId), ())
        op.column(m + "filename", "linked" if filename.strip() in {str(a) for a in attached} else "error:attachment_unknown",
                  "attachments")
    return op


# --- relations ---------------------------------------------------------------------------------------

# Relations of relations.csv touching the scope and owned by a later stage (the other end is imported there).
REL_PENDING_PAIRS = {
    ("Contacts", "PBXManager"): "07.2", ("Leads", "PBXManager"): "07.2", ("Contacts", "SPCallPopup"): "07.2",
    ("Leads", "SPCallPopup"): "07.2", ("SPCallPopup", "Contacts"): "07.2", ("SPCallPopup", "Leads"): "07.2",
}


# crmentityrel pairs handled in this stage: a single link (duplicate of a field) or a link-multiple item;
# pairs with Calendar set the activity's parent (contacts of calls/meetings, the contact of a task).
REL_SINGLE = {("Accounts", "Potentials"): ("Opportunity", "account"), ("Accounts", "HelpDesk"): ("Case", "account"),
              ("Accounts", "Project"): ("Project", "account"), ("Project", "ProjectTask"): ("ProjectTask", "project"),
              # stage 06.3
              ("Accounts", "Invoice"): ("Invoice", "account"), ("Contacts", "Invoice"): ("Invoice", "contact"),
              ("Potentials", "Invoice"): ("Invoice", "opportunity"), ("Potentials", "Quotes"): ("Quote", "opportunity"),
              ("Accounts", "SPPayments"): ("Payment", "payer"), ("Contacts", "SPPayments"): ("Payment", "payer"),
              ("Vendors", "SPPayments"): ("Payment", "payer"), ("Invoice", "Consignment"): ("VtigerArchive", "invoice"),
              ("Leads", "Jivosite"): ("VtigerArchive", "lead"), ("Contacts", "Jivosite"): ("VtigerArchive", "contact"),
              ("Potentials", "Emails"): ("Email", "parent"), ("Contacts", "Emails"): ("Email", "parent"),
              ("Leads", "Emails"): ("Email", "parent")}
REL_MULTI = {("Accounts", "Contacts"): ("Contact", "accounts"), ("Contacts", "HelpDesk"): ("Case", "contacts")}
# a link-multiple item on the record of the first module (06.3: services of an opportunity)
REL_MULTI_FIRST = {("Potentials", "Services"): ("Opportunity", "cProducts")}
# allocation sources of payments: consumed by spec_finance.build_allocation
REL_ALLOCATION = {("Invoice", "SPPayments"), ("SPPayments", "Invoice")}
REL_CALENDAR = {"Accounts", "Contacts", "Leads", "Potentials", "Invoice"}


def attach_relations(ops, ctx):
    """Link tables → operations of the side imported later. Several sources of one single link (field, crmentityrel,
    seactivityrel) are merged: the same pair is a duplicate, another pair a conflict (kept in vtigerData, never
    last-writer-wins)."""
    by_key = {(o.entityType, o.vtigerId): o for o in ops}
    acts = {o.vtigerId: o for o in ops if o.entityType in ("Task", "Call", "Meeting")}
    emails = {o.vtigerId: o for o in ops if o.entityType == "Email"}
    d = ctx.data

    def live(crmid):
        info = ctx.crm.get(int(crmid))
        return info and not info[1]

    # seactivityrel: the activity's (and the archived e-mail's) parent
    for r in d["vtiger_seactivityrel"]:
        act, crmid = int(r["vtiger_seactivityrel.activityid"]), r["vtiger_seactivityrel.crmid"]
        op = acts.get(act) or emails.get(act)
        if op is None:
            continue
        rel = f"seactivityrel:{ctx.crm.get(int(crmid), ('?',))[0]}->{op.entityType}"
        parent_conflict(op, ctx, rel, crmid)
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
        if uid in ctx.users and "Users" not in ctx.selected:
            op.relation(rel, "deferred")
        elif uid in ctx.users:
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
        if ctx.crm[a_id][0] != a_mod or ctx.crm[b_id][0] != b_mod:
            ctx.flags[f"mismatch_rel:{rel}"] += 1  # the row names other modules than its records: never linked
            continue
        if (a_mod, b_mod) in REL_PENDING_PAIRS:
            ctx.flags[f"pending_rel:{rel}:{REL_PENDING_PAIRS[(a_mod, b_mod)]}"] += 1
            continue
        if (a_mod, b_mod) in REL_ALLOCATION:
            continue  # the source of the payment's allocation: outcomes in spec_finance.build_allocation
        crmentityrel_pair(by_key, acts, ctx, rel, a_id, a_mod, b_id, b_mod)
    # tags (freetags) of cases and project tasks
    tags = {int(r["vtiger_freetags.id"]): r["vtiger_freetags.raw_tag"] if not T.is_empty(r.get("vtiger_freetags.raw_tag"))
            else r["vtiger_freetags.tag"] for r in d["vtiger_freetags"]}
    for r in d["vtiger_freetagged_objects"]:
        module = r["vtiger_freetagged_objects.module"]
        entity, attr = {"HelpDesk": ("Case", "cTags"), "ProjectTask": ("ProjectTask", "tags"),
                        "Faq": ("KnowledgeBaseArticle", "cTags")}.get(module, (None, None))
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
        if op.entityType in ("Case", "ProjectTask", "KnowledgeBaseArticle"):
            op.attributes.setdefault("tags" if op.entityType == "ProjectTask" else "cTags", [])
    # stage 06.3: documents of records, the e-mails' parents and recipients, opens of tracked e-mails
    documents = {o.vtigerId: o for o in ops if o.entityType == "Document"}
    for r in d["vtiger_senotesrel"]:
        crmid, note = int(r["vtiger_senotesrel.crmid"]), int(r["vtiger_senotesrel.notesid"])
        setype = ctx.crm.get(crmid, ("?",))[0]
        rel = f"senotesrel:{setype}->Documents"
        op = documents.get(note)
        if op is None:
            _not_in_run(ctx, rel, "Documents")
            continue
        link = C.DOCUMENT_LINKS.get(setype)
        status, target = ctx.target(crmid)
        if link is None:
            op.relation(rel, "error:document_owner_unknown")
        elif status == "ok":
            op.add_relate(link, target)
            op.relation(rel, "linked", f"relate.{link}")
        else:
            op.relation(rel, status if status != "pending" else f"pending:{target}")
    for op in emails.values():
        if "parent" not in op.links and "parent" not in op.keep:
            op.links["parent"] = None
        C.recipients(op, ctx.rows_of_email.get(op.vtigerId, {}), ctx)
    track = defaultdict(list)
    for r in d["vtiger_email_track"]:
        mail = int(r["vtiger_email_track.mailid"])
        op = emails.get(mail)
        if op is None:
            _not_in_run(ctx, "email_track:Emails", "Emails")
            continue
        entry = {k: r[f"vtiger_email_track.{k}"] for k in ("crmid", "access_count", "click_count")
                 if not T.is_empty(r.get(f"vtiger_email_track.{k}")) and r[f"vtiger_email_track.{k}"].strip() != "0"}
        track[mail].append(dict(sorted(entry.items())))
        op.relation("email_track:Emails", "archived", "vtigerData.track")
    for mail, entries in track.items():
        emails[mail].archive("track", sorted(entries, key=lambda e: json.dumps(e, sort_keys=True)))


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


# Entity types a single link of the in-scope entities accepts (a crmentityrel row may name a module the record is not).
LINK_TYPES = {"account": ("Account",), "contact": ("Contact",), "project": ("Project",), "opportunity": ("Opportunity",),
              "parent": ("Account", "Contact", "Lead", "Opportunity", "Case", "Project", "ProjectTask", "Invoice"),
              "payer": ("Account", "Contact", "Vendor"), "invoice": ("Invoice",), "lead": ("Lead",)}


def single_or_conflict(op, ctx, rel, link, crmid, status, target):
    """A second source of a single link: unset → it sets the link; the same target → duplicate; another target →
    conflict, the alternative source id kept in vtigerData.<link>Alternatives (never last-writer-wins)."""
    current = op.links.get(link)
    if not current and link in op.keep:  # the first source points to a record of a later stage: it stays the link
        if op.kept_ids.get(link) == int(crmid):
            op.relation(rel, "duplicate")
            return
        current = "kept"
    if not current:
        link_ref(op, ctx, rel, link, crmid, kind="r", accept=LINK_TYPES.get(link))
    elif status == "ok" and current == list(target):
        op.relation(rel, "duplicate", f"{link}Id")
    else:
        key = f"{link}Alternatives"
        op.relation(rel, "conflict", op.archive(key, sorted(set(op.vtigerData.get(key, [])) | {int(crmid)})))


def _not_in_run(ctx, rel, module):
    """A link row whose record belongs to a module outside this run (--only): counted, left for that module's run."""
    if module in ctx.selected or (module == "Calendar" and ctx.selected & {"Calendar", "Events"}):
        return False
    ctx.flags[f"deferred_rel:{rel}"] += 1
    return True


def crmentityrel_pair(by_key, acts, ctx, rel, a_id, a_mod, b_id, b_mod):
    """Vtiger's generic M:N → the link of the record imported later."""
    if b_mod == "Calendar":
        op = acts.get(b_id)
        if op is None:
            _not_in_run(ctx, rel, "Calendar")
            return
        status, target = ctx.target(a_id)
        if op.entityType == "Task" and a_mod == "Contacts":
            single_or_conflict(op, ctx, rel, "contact", a_id, status, target)
            return
        if op.entityType in ("Call", "Meeting") and a_mod in ("Contacts", "Leads"):
            if a_mod == "Leads" and not (op.links.get("parent") or "parent" in op.keep):
                single_or_conflict(op, ctx, rel, "parent", a_id, status, target)
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
        else:
            _not_in_run(ctx, rel, b_mod)
        return
    if (a_mod, b_mod) in REL_MULTI:
        entity, link = REL_MULTI[(a_mod, b_mod)]
        op = by_key.get((entity, b_id))
        if op is None:
            _not_in_run(ctx, rel, b_mod)
            return
        status, target = ctx.target(a_id)
        multi_item(op, ctx, rel, link, status, target)
        return
    if (a_mod, b_mod) in REL_MULTI_FIRST:
        entity, link = REL_MULTI_FIRST[(a_mod, b_mod)]
        op = by_key.get((entity, a_id))
        if op is None:
            _not_in_run(ctx, rel, a_mod)
            return
        status, target = ctx.target(b_id)
        multi_item(op, ctx, rel, link, status, target)
        return
    ctx.flags[f"unhandled_rel:{rel}"] += 1


# --- plan ------------------------------------------------------------------------------------------

@dataclass
class Plan:
    ops: list            # operations to send, in ORDER
    held: list           # records not sent: pending (later stage), skipped (reason)
    flags: Counter
    counters: dict = field(default_factory=dict)   # entity type → next number (vtiger_modentity_num.cur_id)
    problems: list = field(default_factory=list)   # plan-level problems (identifiers only)


def _crm_sorted(rows):
    return sorted(rows, key=lambda r: int(r["vtiger_crmentity.crmid"]))


def build(data, selected=None, key_range=(1, SYNTHETIC_KEY_MIN - 1), effective_admin=EFFECTIVE_ADMIN, files=None):
    """All operations of the run from the rows read (spec order, deterministic). `files`: attachment id → resolved
    snapshot file ({status, rel, size, sha256}) and the snapshot inventory under the key `inventory`."""
    files = files or {}
    ctx = Context(data, selected, key_range, effective_admin)
    ops = []
    if "Users" in ctx.selected:
        ops += [build_user(r, ctx) for r in sorted(data["vtiger_users"], key=lambda r: int(r["vtiger_users.id"]))]
    for module in ("Vendors", "Products", "Services"):
        if module in ctx.selected:
            ops += [record_or_error(module, r, ctx, C.build_catalogue) for r in _crm_sorted(data[module])]
    if "OrganizationDetails" in ctx.selected:
        for row in data.get("vtiger_organizationdetails", []):
            ops.append(F.build_legal_entity(row, ctx))
            logo = C.build_logo(row, files.get("inventory", {}), ctx)
            if logo:
                ops.append(logo)
                logo_col = "vtiger_organizationdetails.logoname"
                ops[-2].column(logo_col, "linked" if not logo.skip else f"not_applicable:{logo.skip}", "logoId")
    for module in ("Accounts", "Contacts", "Leads", "Potentials", "Project", "ProjectTask", "HelpDesk"):
        if module not in ctx.selected:
            continue
        rows = _crm_sorted(data[module])
        ops += [record_or_error(module, r, ctx, build_record) for r in rows]
        if module == "Contacts":
            ops += [record_or_error(module, r, ctx, lambda m, row, c: build_contact_access(row, c)) for r in rows]
    lines = defaultdict(list)
    for row in data.get("lines", []):
        lines[int(row["vtiger_inventoryproductrel.id"])].append(row)
    for module in F.DOCUMENTS:
        if module not in ctx.selected:
            continue
        for row in _crm_sorted(data[module]):
            doc = record_or_error(module, row, ctx, F.build_document)
            ops.append(doc)
            for line in sorted(lines.get(doc.vtigerId, []), key=lambda r: int(r["vtiger_inventoryproductrel.lineitem_id"])):
                item = record_or_error(module, line, ctx, F.build_item, key_col="vtiger_inventoryproductrel.lineitem_id",
                                       entity=F.DOCUMENTS[module][1])
                if doc.skip or doc.pending:
                    item.pending, item.skip = doc.pending, doc.skip and "owner_skipped"
                ops.append(item)
    if "SPPayments" in ctx.selected:
        invoice_links = defaultdict(list)
        for r in data["vtiger_crmentityrel"]:
            a, b = int(r["vtiger_crmentityrel.crmid"]), int(r["vtiger_crmentityrel.relcrmid"])
            pair = (r["vtiger_crmentityrel.module"], r["vtiger_crmentityrel.relmodule"])
            if pair not in REL_ALLOCATION or not (_live(ctx, a) and _live(ctx, b)) \
                    or (ctx.crm[a][0], ctx.crm[b][0]) != pair:
                continue
            payment, invoice = (b, a) if pair[0] == "Invoice" else (a, b)
            invoice_links[payment].append(invoice)
        for row in _crm_sorted(data["SPPayments"]):
            payment = record_or_error("SPPayments", row, ctx, F.build_payment)
            ops.append(payment)
            if payment.skip:
                continue
            allocation = F.build_allocation(payment, row, invoice_links.get(payment.vtigerId, []), ctx)
            if allocation:
                ops.append(allocation)
    for module in ARCHIVES:
        if module in ctx.selected:
            ops += [record_or_error(module, r, ctx, lambda m, row, c: C.build_archive(
                m, row, c, lines.get(int(row["vtiger_crmentity.crmid"]), []))) for r in _crm_sorted(data[module])]
    if "Faq" in ctx.selected:
        faqs = [record_or_error("Faq", r, ctx, lambda m, row, c: C.build_faq(row, c)) for r in _crm_sorted(data["Faq"])]
        names = sorted({i[1] for o in faqs for i in o.linkMultiple.get("categories", {}).get("items", [])})
        ops += [C.build_category(n) for n in names] + faqs
    for module in ("Calendar", "Events"):
        if module in ctx.selected:
            ops += [record_or_error(module, r, ctx, build_activity) for r in _crm_sorted(data[module])]
    if "Emails" in ctx.selected:
        ctx.rows_of_email = {int(r["vtiger_crmentity.crmid"]): r for r in data["Emails"]}
        ops += [record_or_error("Emails", r, ctx, lambda m, row, c: C.build_email(row, c))
                for r in _crm_sorted(data["Emails"])]
    if "Documents" in ctx.selected:
        ops += [C.build_folder(r, ctx) for r in data.get("vtiger_attachmentsfolder", [])]
        documents_files = document_files(data, files)
        ops += [record_or_error("Documents", r, ctx, lambda m, row, c: C.build_document(row, c, documents_files))
                for r in _crm_sorted(data["Documents"])]
    if "ModComments" in ctx.selected:
        rows = sorted(data["ModComments"], key=lambda r: (r["vtiger_crmentity.createdtime"] or "",
                                                          int(r["vtiger_crmentity.crmid"])))
        ops += [record_or_error("ModComments", r, ctx, lambda m, row, c: build_note(row, c)) for r in rows]
    if "Attachments" in ctx.selected:
        ops += build_attachments(data, files, ctx)
    attach_relations([o for o in ops if not o.skip], ctx)
    held = {(o.entityType, o.vtigerId) for o in ops if o.skip or o.pending}
    for op in ops:  # a file waits with its owner (a comment held, an owner not created)
        if op.entityType == "Attachment" and not (op.skip or op.pending) and \
                (op.owner["entityType"], op.owner["key"]) in held:
            op.pending = "owner_held"
    for op in ops:
        if isinstance(op.vtigerId, int) and not (key_range[0] <= op.vtigerId <= key_range[1]):
            raise T.TransformError("key_out_of_range")
    order = {e: i for i, e in enumerate(ORDER)}
    send = [o for o in ops if not (o.skip or o.pending)]
    send.sort(key=lambda o: order[o.entityType])   # stable: comments keep their chronological order
    counters, problems = F.counters(data) if FINANCE_COUNTERS & ctx.selected else ({}, [])
    return Plan(send, [o for o in ops if o.skip or o.pending], ctx.flags, counters, problems)


FINANCE_COUNTERS = {"Quotes", "SalesOrder", "Invoice", "Act", "SPPayments"}


def _live(ctx, crmid):
    info = ctx.crm.get(int(crmid))
    return bool(info) and not info[1]


def document_files(data, files):
    """Document crmid → the resolved file of its Documents Attachment (name, size, type), for the comparison of the
    source document's file name, size and type."""
    atts = {int(r["vtiger_attachments.attachmentsid"]): r for r in data.get("vtiger_attachments", [])}
    out = {}
    for r in data.get("vtiger_seattachmentsrel", []):
        att = int(r["vtiger_seattachmentsrel.attachmentsid"])
        ref = files.get(att)
        if att in atts and data["crm"].get(att, (None,))[0] == "Documents Attachment" and ref and ref["status"] == "found":
            out[int(r["vtiger_seattachmentsrel.crmid"])] = {"name": atts[att].get("vtiger_attachments.name"),
                                                             "size": ref["size"],
                                                             "type": atts[att].get("vtiger_attachments.type")}
    return out


def build_attachments(data, files, ctx):
    """One Attachment operation per live attachment of a record in scope (vtiger_seattachmentsrel by its owner,
    vtiger_salesmanattachmentsrel for user images); an attachment of an owner outside this run waits (deferred)."""
    rows = {int(r["vtiger_attachments.attachmentsid"]): r for r in data.get("vtiger_attachments", [])}
    ops = []
    for table, owner_col in (("vtiger_seattachmentsrel", "crmid"), ("vtiger_salesmanattachmentsrel", "smid")):
        for r in sorted(data.get(table, []), key=lambda r: int(r[f"{table}.attachmentsid"])):
            att = int(r[f"{table}.attachmentsid"])
            setype = ctx.crm.get(att, ("?",))[0]
            rel = f"{table.replace('vtiger_', '')}:{setype}"
            if att not in rows or setype not in C.ATTACHMENT_OWNERS:
                continue  # outside the scope of the reader (LINK_ROWS): not counted there either
            owner_setype, owner_entity, field_name = C.ATTACHMENT_OWNERS[setype]
            owner_key = int(r[f"{table}.{owner_col}"])
            module_of_owner = "Users" if owner_setype == "Users" else owner_setype
            op = C.build_attachment(rows[att], (owner_setype, owner_entity, field_name, owner_key), files, ctx)
            if module_of_owner not in ctx.selected:
                op.pending = "deferred"
                op.relation(rel, "deferred")
            else:
                op.relation(rel, "linked", f"owner.{field_name}")
            ops.append(op)
    return ops


def record_or_error(module, row, ctx, builder, key_col=None, entity=None):
    try:
        return builder(module, row, ctx)
    except T.TransformError as e:
        entity = entity or ENTITY_BY_SETYPE.get(module, "Task" if module in ("Calendar", "Events") else "User")
        key = row.get(key_col) if key_col else (row.get("vtiger_crmentity.crmid") or row.get("vtiger_users.id"))
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
    return out | consumed_columns_063()


def consumed_columns_063():
    """Columns consumed by the stage-06.3 rules (spec_finance, spec_content)."""
    out = set()
    common = ("smownerid", "smcreatorid", "modifiedby", "createdtime", "modifiedtime", "description")
    for module in ("Vendors", "Products", "Services"):
        out |= {(module, c) for rule in C.catalogue_rules(module) for c in rule.cols}
        out |= {(module, "vtiger_crmentity." + c) for c in common}
    line = F.LINE
    for module in F.DOCUMENTS:
        out |= {(module, c) for rule in F.document_rules(module) for c in rule.cols}
        out |= {(module, "vtiger_crmentity." + c) for c in common}
        out |= {(module, c) for rule in F.line_rules() for c in rule.cols}
        out |= {(module, line + c) for c in ("id", "lineitem_id", "sequence_no", "productid")}
    out |= {("SPPayments", c) for rule in F.payment_rules() for c in rule.cols}
    out |= {("SPPayments", "vtiger_crmentity." + c) for c in common} | {("SPPayments", "sp_payments.related_to")}
    for module in ARCHIVES:
        out |= {(module, c) for rule in C.archive_rules(module) for c in rule.cols}
    out |= {("Consignment", line + c) for c in ("id", "lineitem_id", "sequence_no", "productid", "quantity", "listprice",
                                                 "comment", "discount_amount", "discount_percent", "tax1", "tax2",
                                                 "tax3", "purchase_cost", "margin")}
    f = "vtiger_faq."
    out |= {("Faq", f + c) for c in ("question", "answer", "faq_no", "status", "product_id", "category")}
    out |= {("Faq", "vtiger_crmentity." + c) for c in common if c != "description"}
    a, d = "vtiger_activity.", "vtiger_emaildetails."
    out |= {("Emails", a + c) for c in ("subject", "date_start", "time_start", "semodule")}
    out |= {("Emails", d + c) for c in ("from_email", "to_email", "cc_email", "bcc_email", "idlists", "email_flag")}
    out |= {("Emails", "vtiger_crmentity." + c) for c in common}
    n = "vtiger_notes."
    out |= {("Documents", n + c) for c in ("title", "note_no", "folderid", "filelocationtype", "filestatus",
                                            "filename", "filesize", "filetype", "fileversion", "filedownloadcount",
                                            "notecontent")}
    out |= {("Documents", "vtiger_notescf.cf_for_field")}
    out |= {("Documents", "vtiger_crmentity." + c) for c in common if c != "description"}
    out |= {("Documents", "vtiger_attachmentsfolder." + c) for c in ("folderid", "foldername", "description",
                                                                     "createdby", "sequence")}
    out |= {("Attachments", "vtiger_attachments." + c) for c in ("attachmentsid", "name", "type", "description", "path")}
    out |= {("Emails", "vtiger_attachments.name")}  # the file of an e-mail: its Attachment operation (Attachments)
    o = "vtiger_organizationdetails."
    out |= {("OrganizationDetails", c) for rule in F.legal_entity_rules() for c in rule.cols}
    out |= {("OrganizationDetails", o + c) for c in ("company", "logoname")}
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
    modules = modules_of_physical(table)
    return modules[0] if modules else None


def modules_of_physical(table):
    """Modules whose records read rows of `table` (vtiger_crmentity excluded: its columns are per module)."""
    if table == "vtiger_inventoryproductrel":
        return list(LINE_MODULES)
    out = [module for module, src in SOURCES.items() if table in src.tables()[1:]]
    out += [module for module, tables in PLAIN_MODULES.items() if table in tables and module not in out]
    if table in ("vtiger_users", "vtiger_user2role"):
        out.append("Users")
    return out


def check_coverage(fields, relations):
    """Problems (identifiers only) that refuse the run before any read of the source."""
    problems = []
    consumed = consumed_columns()
    rows = defaultdict(list)
    for r in fields:
        for module in [r["source_module"]] if r["source_module"] else modules_of_physical(r["source_table"]):
            if module in SCOPE:
                rows[(module, f"{r['source_table']}.{r['source_column']}")].append(r)
    for key, rs in sorted(rows.items()):
        transfer = [r for r in rs if r["fate"].startswith(TRANSFER_FATES)]
        is_key = any(is_key_row(r) for r in rs)
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
    for r in fields:  # columns of the link tables: every mapped column has an explicit fate
        table = r["source_table"]
        if table in LINK_COLUMNS and not r["source_module"] and r["source_column"] not in LINK_COLUMNS[table]:
            problems.append(f"link column without a fate: {table}.{r['source_column']}")
    for r in relations:
        ends = {r["from_module"], *r["to_module"].split("|")}
        if not ends & set(SCOPE) or r["kind"] in ("owner", "history"):
            continue
        if r["fate"].startswith(("пусто", "исключено")) or not r["fate"].startswith(TRANSFER_FATES + ("слияние",)):
            continue
        rid = r["relation_id"]
        if rid.startswith("crmentityrel:"):
            pair = tuple(rid.split(":", 1)[1].split("->"))
            if not (pair in REL_PENDING_PAIRS or pair in REL_SINGLE or pair in REL_MULTI or pair in REL_MULTI_FIRST
                    or pair in REL_ALLOCATION or (pair[1] == "Calendar" and pair[0] in REL_CALENDAR)):
                problems.append(f"relation not handled: {rid}")
            continue
        if rid.startswith(HANDLED_RELATIONS_PREFIXES) or rid in FIELD_RELATIONS:
            continue
        if rid.startswith(("senotesrel:", "seattachmentsrel:", "lines:", "allocation:", "invoice_act:", "tags:")):
            continue  # documents, files, line items, allocations: 06.3 builders (spec_content, spec_finance)
        if r["from_module"] not in SCOPE:
            continue  # a field of a later module pointing into the scope: imported with that module
        problems.append(f"relation not handled: {rid}")
    return problems


# Field relations of in-scope modules handled by the column rules above.
FIELD_RELATIONS = {"Calendar.crmid", "Events.crmid", "Events.contactid", "Contacts.accountid", "HelpDesk.contact_id",
                   # stage 06.3: links of the finance documents, payments and archives (spec_finance, spec_content)
                   *(f"{m}.{c}" for m in ("Quotes", "SalesOrder", "Invoice", "Act")
                     for c in ("productid", "accountid", "contactid", "potentialid", "potential_id", "salesorderid",
                               "sp_act_id")),
                   "SPPayments.payer", "SPPayments.related_to", "Assets.account", "Assets.product",
                   "Consignment.productid", "Consignment.accountid", "Consignment.invoiceid", "JVmes.relatedjivo",
                   "Jivosite.relatedleads", "ServiceContracts.sc_related_to",
                   "HelpDesk.parent_id", "ModComments.customer", "ModComments.related_to", "ModComments.userid",
                   "Potentials.contact_id", "Potentials.related_to", "Project.linktoaccountscontacts",
                   "Project.potentialid", "ProjectTask.projectid"}


# The stage-06.3 parts of the specification (they use the definitions above).
import spec_content as C  # noqa: E402
import spec_finance as F  # noqa: E402
