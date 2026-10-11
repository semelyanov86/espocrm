"""Content part of the Vtiger import (stage 06.3, docs/migration/import.md): vendors, products and services, documents
and their folder, the knowledge base (FAQ), archived e-mails, the archive modules (VtigerArchive) and every file
(Attachment operations: document files, the contact photo, the user avatar, comment and e-mail attachments, the logo
of the legal entity). Pure: no I/O, no values in messages.
"""
import csv
import json
import mimetypes
import re
from urllib.parse import urlsplit

import spec as S
import transforms as T

# owner setype of vtiger_senotesrel → link of Document to it
DOCUMENT_LINKS = {"Accounts": "accounts", "Contacts": "contacts", "Leads": "leads", "Potentials": "opportunities",
                  "HelpDesk": "cCases", "Project": "cProjects", "ProjectTask": "cProjectTasks",
                  "Faq": "cKnowledgeBaseArticles", "Invoice": "cInvoices", "Act": "cActs", "SPPayments": "cPayments",
                  "Quotes": "cQuotes", "SalesOrder": "cSalesOrders", **{m: "cVtigerArchives" for m in S.ARCHIVES}}
# attachment setype → (owner setype, owner entity, owner field) — vtiger_seattachmentsrel / salesmanattachmentsrel
ATTACHMENT_OWNERS = {"Documents Attachment": ("Documents", "Document", "file"),
                     "Contacts Image": ("Contacts", "Contact", "cPhoto"),
                     "ModComments Attachment": ("ModComments", "Note", "attachments"),
                     "Emails Attachment": ("Emails", "Email", "attachments"),
                     "Users Image": ("Users", "User", "avatar")}
KB_CATEGORY = {"General": "Общее"}  # field-map: the single FAQ category → KnowledgeBaseCategory «Общее»
URL_RE = re.compile(r"^(https?|ftp)://\S+$", re.IGNORECASE)


def is_url(value):
    """A link the field can hold and a browser can open: http/https/ftp with a host, no whitespace, ≤ 255."""
    try:
        return len(value) <= 255 and bool(URL_RE.match(value.strip())) and bool(urlsplit(value.strip()).hostname)
    except ValueError:
        return False
ARCHIVE_LINKS = {  # archive module → column → (link, accepted entity types)
    "Consignment": {"vtiger_sp_consignment.accountid": ("account", ("Account",)),
                    "vtiger_sp_consignment.invoiceid": ("invoice", ("Invoice",)),
                    "vtiger_sp_consignment.contactid": ("contact", ("Contact",))},
    "ServiceContracts": {"vtiger_servicecontracts.sc_related_to": ("account", ("Account",))},
    "Assets": {"vtiger_assets.account": ("account", ("Account",)), "vtiger_assets.product": ("product", ("Product",)),
               "vtiger_assets.contact": ("contact", ("Contact",))},
    "Jivosite": {"vtiger_jivosite.relatedleads": ("lead", ("Lead",)),
                 "vtiger_jivosite.relatedcontact": ("contact", ("Contact",))},
    "JVmes": {"vtiger_jvmes.relatedjivo": ("parentArchive", ("VtigerArchive",))},
}
ARCHIVE_TITLE = {"Consignment": ("vtiger_sp_consignment.subject", "vtiger_sp_consignment.consignment_no"),
                 "ServiceContracts": ("vtiger_servicecontracts.subject", "vtiger_servicecontracts.contract_no"),
                 "Assets": ("vtiger_assets.assetname", "vtiger_assets.asset_no"),
                 "Jivosite": (None, None), "JVmes": (None, None)}


# --- catalogues -----------------------------------------------------------------------------------------

def catalogue_rules(module):
    if module == "Vendors":
        v = "vtiger_vendor."
        return [S.Str(v + "vendorname", "name"), S.Str(v + "vendor_no", "vtigerNo"), S.Str(v + "website", "website"),
                S.Emails((v + "email", "email")), S.Phones(*S.PHONE_COLUMNS["Vendors"]),
                S.Str("vtiger_vendorcf.cf_1206", "inn")]
    if module == "Products":
        p = "vtiger_products."
        return [S.Str(p + "productname", "name"), S.Str(p + "product_no", "vtigerNo"), S.Str(p + "productcode", "code"),
                Active(p + "discontinued", "isActive"), S.Dec(p + "unit_price", "unitPrice", scale=8),
                S.Enum(p + "usageunit", "unit", vmap=("Product", "unit", "Products.usageunit"), key="usageunit"),
                S.Archive(p + "qtyinstock", "qtyinstock", kind="dec"),
                S.Archive(p + "commissionrate", "commissionrate", kind="dec"),
                S.Archive(p + "qty_per_unit", "qty_per_unit", kind="dec")]
    s = "vtiger_service."
    return [S.Str(s + "servicename", "name"), S.Str(s + "service_no", "vtigerNo"), Active(s + "discontinued", "isActive"),
            S.Dec(s + "unit_price", "unitPrice", scale=8), S.Num(s + "qty_per_unit", "qtyPerUnit", scale=2),
            S.Enum(s + "service_usageunit", "unit", vmap=("Product", "unit", "Services.service_usageunit"),
                   key="service_usageunit"),
            S.Enum(s + "servicecategory", "category", vmap=("Product", "category", "Services.servicecategory"),
                   key="servicecategory"),
            S.Archive(s + "website", "website"), S.Archive(s + "sales_start_date", "sales_start_date"),
            S.Archive(s + "sales_end_date", "sales_end_date"), S.Archive(s + "start_date", "start_date"),
            S.Archive(s + "commissionrate", "commissionrate", kind="dec"),
            S.Bool("vtiger_servicecf.cf_billable_time_tracker", "isBillableTime")]


class Active(S.Rule):
    """discontinued of Vtiger products and services: 1 means «active» (field-map)."""

    def apply(self, op, row, ctx):
        raw = self.value(row)
        op.attributes[self.attr] = not T.is_empty(raw) and raw.strip() == "1"
        if not T.is_empty(raw):
            op.column(self.cols[0], "mapped", self.attr)


def build_catalogue(module, row, ctx):
    entity = S.ENTITY_BY_SETYPE[module]
    op = S.Op(entity, int(row["vtiger_crmentity.crmid"]), module)
    S.crmentity(op, row, ctx)
    if module in ("Products", "Services"):
        op.attributes["type"] = ctx.maps.lookup("Product", "type", "(module)", module)
    for rule in catalogue_rules(module):
        rule.apply(op, row, ctx)
    return op


# --- documents -----------------------------------------------------------------------------------------

def build_folder(row, ctx):
    f = "vtiger_attachmentsfolder."
    op = S.Op("DocumentFolder", int(row[f + "folderid"]), "Documents")
    op.column(f + "folderid", "carried", "vtigerId")
    S._set(op, f + "foldername", "name", T.string(row.get(f + "foldername")))
    S._set(op, f + "description", "description", T.text(row.get(f + "description")))
    S.user_ref(op, ctx, f + "createdby", "createdBy", row.get(f + "createdby"))
    seq = row.get(f + "sequence")
    if not T.is_empty(seq):
        op.column(f + "sequence", "archived", op.archive("sequence", T.integer(seq)))
    return op


def build_document(row, ctx, files):
    """vtiger_notes → Document: an internal file (I) is the Attachment operation of its vtiger_seattachmentsrel row,
    an external one (E) the URL in cExternalUrl (never fetched); file name, size and type of the source record are
    compared with the attachment (equal → derived, otherwise kept in vtigerData)."""
    n = "vtiger_notes."
    op = S.Op("Document", int(row["vtiger_crmentity.crmid"]), "Documents")
    S.crmentity(op, row, ctx, description=False)
    S.Str(n + "title", "name").apply(op, row, ctx)
    S.Str(n + "note_no", "vtigerNo").apply(op, row, ctx)
    S.Enum(n + "filestatus", "status", vmap=("Document", "status", "Documents.filestatus"), key="filestatus") \
        .apply(op, row, ctx)
    S.Text(n + "notecontent", "description").apply(op, row, ctx)
    S.Archive(n + "fileversion", "fileversion").apply(op, row, ctx)
    S.Archive(n + "filedownloadcount", "filedownloadcount", kind="int").apply(op, row, ctx)
    S.Archive("vtiger_notescf.cf_for_field", "cf_for_field").apply(op, row, ctx)
    folder = row.get(n + "folderid")
    op.links["folder"] = None
    if not T.is_empty(folder) and folder.strip() != "0":
        op.links["folder"] = ["DocumentFolder", int(folder)]
        op.column(n + "folderid", "linked", "folderId")
    elif not T.is_empty(folder):
        op.column(n + "folderid", "zero_empty")
    location = (row.get(n + "filelocationtype") or "").strip()
    name, size, mime = row.get(n + "filename"), row.get(n + "filesize"), row.get(n + "filetype")
    attachment = files.get(op.vtigerId)  # the Documents Attachment of this document, resolved (or None)
    op.attributes["cExternalUrl"] = None
    if location == "E":
        op.column(n + "filelocationtype", "mapped", "cExternalUrl")
        if not T.is_empty(name) and is_url(name):
            op.attributes["cExternalUrl"] = name
            op.column(n + "filename", "carried", "cExternalUrl")
        elif not T.is_empty(name):
            ctx.flags["external_url_invalid"] += 1
            op.column(n + "filename", "archived", op.archive("filename", name))
        for col, raw, key in ((n + "filesize", size, "filesize"), (n + "filetype", mime, "filetype")):
            if not T.is_empty(raw) and not (key == "filesize" and raw.strip() == "0"):
                op.column(col, "archived", op.archive(key, raw))
            elif not T.is_empty(raw):
                op.column(col, "zero_empty")
        return op
    if location == "I" and attachment:
        op.column(n + "filelocationtype", "mapped", "fileId")
    elif not T.is_empty(location):
        # D-23: an internal document without a file in the source (accepted loss), or an unknown location type
        op.column(n + "filelocationtype", "not_applicable:D-23" if location == "I" else "error:location_unknown")
    for col, raw, key, have in ((n + "filename", name, "filename", attachment and attachment["name"]),
                                (n + "filesize", size, "filesize", attachment and str(attachment["size"])),
                                (n + "filetype", mime, "filetype", attachment and attachment["type"])):
        if T.is_empty(raw):
            continue
        if have is not None and raw == have:
            op.column(col, "derived_equal", "fileId")
        elif key == "filesize" and raw.strip() == "0":
            op.column(col, "zero_empty")
        else:
            op.column(col, "archived", op.archive(key, raw))
    return op


# --- knowledge base ----------------------------------------------------------------------------------------

def build_category(name):
    op = S.Op("KnowledgeBaseCategory", name, "Faq", name_override=f"KnowledgeBaseCategory:{name}")
    op.attributes["name"] = name
    return op


def build_faq(row, ctx):
    f = "vtiger_faq."
    op = S.Op("KnowledgeBaseArticle", int(row["vtiger_crmentity.crmid"]), "Faq")
    S.crmentity(op, row, ctx, description=False)
    S.Str(f + "question", "name").apply(op, row, ctx)
    S.Text(f + "answer", "body").apply(op, row, ctx)
    S.Str(f + "faq_no", "vtigerNo").apply(op, row, ctx)
    S.Enum(f + "status", "status", vmap=("KnowledgeBaseArticle", "status", "Faq.faqstatus"), key="faqstatus") \
        .apply(op, row, ctx)
    S.Archive(f + "product_id", "product_id", kind="int").apply(op, row, ctx)
    op.attributes.update(type="Article", language=None)
    category = row.get(f + "category")
    op.linkMultiple["categories"] = {"items": [], "domain": [["KnowledgeBaseCategory", n] for n in KB_CATEGORY.values()]}
    if not T.is_empty(category):
        name = KB_CATEGORY.get(category)
        if name is None:
            op.column(f + "category", "error:category_unknown")
        else:
            op.add_item("categories", ["KnowledgeBaseCategory", name])
            op.column(f + "category", "mapped", "categories")
    return op


# --- e-mail ------------------------------------------------------------------------------------------------

def address_list(raw):
    """vtiger_emaildetails to/cc/bcc: a JSON array of addresses (or a plain string) → (';'-joined lower-case addresses,
    representation changed, content changed). Never guesses: an unparsable value is kept as is."""
    if T.is_empty(raw):
        return None, False, False
    try:
        items = json.loads(raw)
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            raise ValueError
    except ValueError:
        items = [raw]
    addresses = [T.email(i) for i in items if not T.is_empty(i)]
    joined = ";".join(a for a in addresses if a) or None
    lossless = all(T.email(i) == i.strip().lower() and "@" in i and ";" not in i for i in items if not T.is_empty(i))
    return joined, True, not lossless


def build_email(row, ctx):
    a, d = "vtiger_activity.", "vtiger_emaildetails."
    op = S.Op("Email", int(row["vtiger_crmentity.crmid"]), "Emails")
    S.crmentity(op, row, ctx, description=False)
    S.Str(a + "subject", "name").apply(op, row, ctx)
    S.Text("vtiger_crmentity.description", "body").apply(op, row, ctx)
    op.attributes["isHtml"] = True
    op.attributes["dateSent"] = S.pair_datetime(op, row, ctx, a + "date_start", a + "time_start", "dateSent")
    S.Enum(d + "email_flag", "status", vmap=("Email", "status", "Emails.email_flag"), key="email_flag") \
        .apply(op, row, ctx)
    S.Archive(a + "semodule", "parent_type").apply(op, row, ctx)
    sender = row.get(d + "from_email")
    op.attributes["fromString"] = T.string(sender)
    op.attributes["from"] = T.email(sender)
    if not T.is_empty(sender):
        op.column(d + "from_email", "carried" if T.email(sender) == sender else "normalized", "from", "fromString")
    for field in ("to", "cc", "bcc"):
        raw = row.get(d + f"{field}_email")
        joined, _changed, lossy = address_list(raw)
        op.attributes[field] = joined
        if T.is_empty(raw):
            continue
        if joined is None:
            op.column(d + f"{field}_email", "zero_empty")  # an empty JSON list
        elif lossy:
            op.column(d + f"{field}_email", "normalized", field, op.archive(f"{field}_email", raw))
        else:
            op.column(d + f"{field}_email", "normalized", field)
    op.attributes["hasAttachment"] = bool(ctx.attachments_of.get(("Email", op.vtigerId)))  # its Attachment operations
    return op


def recipients(op, row, ctx):
    """idlists: the recipient records of the mail (crmid@fieldid|…; Vtiger tracks opens per recipient). EspoCRM keeps
    one parent: a list of only the parent is a duplicate of it, anything else is kept in vtigerData.idlists."""
    col = "vtiger_emaildetails.idlists"
    raw = row.get(col)
    if T.is_empty(raw):
        return
    ids = sorted({int(p.split("@")[0]) for p in raw.split("|") if p.split("@")[0].strip().isdigit()})
    parent = op.links.get("parent")
    if parent and ids == [parent[1]]:
        op.column(col, "duplicate", "parentId")
    else:
        op.column(col, "archived", op.archive("idlists", raw))


# --- archives ------------------------------------------------------------------------------------------

_ARCHIVE_RULES = {}


def archive_rules(module):
    """VtigerArchive.data.<key> from the generated map (D-08: every non-empty source column of the record, under the
    key the map names); links of the archive record on top."""
    if module not in _ARCHIVE_RULES:
        rules = []
        with open(S.T.REPO / "docs/migration/field-map.csv", newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["source_module"] != module or not r["target_field"].startswith("VtigerArchive.data."):
                    continue
                col = f"{r['source_table']}.{r['source_column']}"
                if r["source_table"] in ("vtiger_crmentity_user_field", "vtiger_inventoryproductrel"):
                    continue  # stars are not read; lines are archived as a list
                if any(rule.cols[0] == col for rule in rules):
                    continue  # a duplicated map row (smcreatorid)
                rules.append(S.Data(col, r["target_field"][len("VtigerArchive.data."):]))
        if module == "Consignment":  # a physical map row (VtigerArchive.data), not a declared field
            rules.append(S.Data("vtiger_sp_consignment.compound_taxes_info", "compound_taxes_info"))
        for (gap_module, col), target in S.MAP_GAPS.items():  # author and modifier of the chats (no map row)
            if gap_module == module and target.startswith("VtigerArchive.data."):
                rules.append(S.Data(col, target[len("VtigerArchive.data."):]))
        _ARCHIVE_RULES[module] = rules
    return _ARCHIVE_RULES[module]


def build_archive(module, row, ctx, lines=()):
    op = S.Op("VtigerArchive", int(row["vtiger_crmentity.crmid"]), module)
    op.attributes.update(vtigerModule=module, data={})
    for rule in archive_rules(module):
        rule.apply(op, row, ctx)
    for col, (link, accept) in ARCHIVE_LINKS[module].items():
        raw = row.get(col)
        op.links[link] = None
        if T.is_empty(raw) or raw.strip() == "0":
            continue
        try:
            int(raw)
        except ValueError:
            continue  # stays in data only (archived)
        target = S.link_ref(op, ctx, None, link, raw, accept=accept)
        ctx.flags[f"archive_link:{module}.{link}:{'linked' if target else 'kept'}"] += 1
    title, number = ARCHIVE_TITLE[module]
    op.attributes["name"] = T.string(row.get(title)) if title else None
    op.attributes["vtigerNo"] = T.string(row.get(number)) if number else None
    op.attributes["recordDate"] = ctx.dt(row.get("vtiger_crmentity.createdtime"))
    archive_lines(op, lines)
    op.attributes["data"] = dict(sorted(op.attributes["data"].items())) or None
    return op


LINE = "vtiger_inventoryproductrel."
LINE_EXCLUDED = (LINE + "image", LINE + "description", LINE + "incrementondel")  # empty / Vtiger stock flag (map)


def archive_lines(op, rows):
    """Lines of an archived document (the single consignment) → data.lines: every non-empty column but the ones the
    map excludes, in line order."""
    out = []
    for row in sorted(rows, key=lambda r: int(r[LINE + "sequence_no"] or 0)):
        line = {}
        for col, value in row.items():
            if T.is_empty(value) or col in LINE_EXCLUDED:
                continue
            line[col.split(".", 1)[1]] = value
            op.column(col, "archived", "data")
        out.append(dict(sorted(line.items())))
    if out:
        op.attributes.setdefault("data", {})["lines"] = out


# --- files ---------------------------------------------------------------------------------------------

def build_attachment(row, owner, files, ctx):
    """An Attachment operation: the record (name, MIME type, role, description in vtigerData), its owner and the
    resolved file of the snapshot (size, sha256)."""
    a = "vtiger_attachments."
    aid = int(row[a + "attachmentsid"])
    op = S.Op("Attachment", aid, "Attachments")
    op.column(a + "attachmentsid", "carried", "vtigerId")
    S._set(op, a + "name", "name", T.string(row.get(a + "name")))
    S._set(op, a + "type", "type", T.string(row.get(a + "type")))
    S.Archive(a + "description", "description").apply(op, row, ctx)
    op.attributes["role"] = "Attachment"
    owner_setype, owner_entity, field, owner_id = owner
    op.owner = {"entityType": owner_entity, "key": owner_id, "field": field}
    ref = files.get(aid)
    if not ref or ref["status"] != "found":
        op.skip = f"file_{ref['status'] if ref else 'unresolved'}"
        op.column(a + "path", f"not_applicable:file_{ref['status'] if ref else 'unresolved'}")
        return op
    op.file = {"size": ref["size"], "sha256": ref["sha256"]}
    op.file_ref = ref["rel"]
    op.column(a + "path", "carried", "file")
    return op


def build_logo(row, inventory, ctx):
    """The logo of the legal entity: test/logo/<logoname> of the snapshot (no Vtiger attachment id)."""
    o = "vtiger_organizationdetails."
    name = row.get(o + "logoname")
    if T.is_empty(name):
        return None
    op = S.Op("Attachment", None, "OrganizationDetails", name_override="Attachment:LegalEntity.logo")
    rel = b"test/logo/" + name.encode("utf-8")
    entry = inventory.get(rel) if b"/" not in name.encode("utf-8") else None
    op.owner = {"entityType": "LegalEntity", "key": "Default", "field": "logo"}
    op.attributes.update(name=name, type=mimetypes.guess_type(name)[0] or "application/octet-stream",
                         role="Attachment")
    op.vtigerData["source"] = "vtiger_organizationdetails.logoname"  # the identity of the logo (AttachmentWriter)
    if entry is None:
        op.skip = "file_missing"
        return op
    op.file = {"size": entry[0], "sha256": entry[2]}
    op.file_ref = rel
    return op
